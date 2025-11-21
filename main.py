import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List

from database import db, create_document, get_documents
from schemas import GSTCategory, GSTCalculation

app = FastAPI(title="GST Calculator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "GST Calculator API Running"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# AI-like matching using keyword similarity (simple heuristic)

def detect_category(description: str) -> Optional[GSTCategory]:
    description = (description or "").lower()
    try:
        categories = get_documents("gstcategory", {})
    except Exception:
        categories = []
    best = None
    best_score = 0
    for cat in categories:
        kws = [k.lower() for k in cat.get("keywords", [])] + [cat.get("name", "").lower()]
        score = sum(1 for k in kws if k and k in description)
        if score > best_score:
            best_score = score
            best = cat
    if best:
        return GSTCategory(
            name=best.get("name"),
            rate=float(best.get("rate", 0)),
            keywords=best.get("keywords", []),
            active=best.get("active", True)
        )
    return None

class CalculateRequest(BaseModel):
    amount: float = Field(..., ge=0)
    description: Optional[str] = Field(None, description="Goods/services description for AI detection")
    rate: Optional[float] = Field(None, ge=0, le=100, description="Override rate if provided")
    mode: str = Field("exclusive", description="exclusive or inclusive")

class CalculateResponse(BaseModel):
    net_amount: float
    gst_amount: float
    gross_amount: float
    applied_rate: float
    detected_category: Optional[str]
    source: str

@app.post("/api/calculate", response_model=CalculateResponse)
async def calculate_tax(payload: CalculateRequest):
    amount = payload.amount
    mode = payload.mode.lower()
    if mode not in ("exclusive", "inclusive"):
        raise HTTPException(status_code=400, detail="mode must be 'exclusive' or 'inclusive'")

    detected = None
    source = "default"
    applied_rate = 18.0  # default rate if nothing provided or detected

    if payload.rate is not None:
        applied_rate = payload.rate
        source = "provided"
    else:
        detected = detect_category(payload.description or "")
        if detected and detected.active:
            applied_rate = detected.rate
            source = "detected"

    r = applied_rate / 100.0

    if mode == "exclusive":
        net = amount
        gst = round(net * r, 2)
        gross = round(net + gst, 2)
    else:  # inclusive
        gross = amount
        net = round(gross / (1 + r), 2)
        gst = round(gross - net, 2)

    # Log calculation
    try:
        calc = GSTCalculation(
            amount=amount,
            mode=mode,
            applied_rate=applied_rate,
            computed_tax=gst,
            net_amount=net,
            gross_amount=gross,
            detected_category=detected.name if detected else None,
            source=source,
        )
        create_document("gstcalculation", calc)
    except Exception:
        pass

    return CalculateResponse(
        net_amount=net,
        gst_amount=gst,
        gross_amount=gross,
        applied_rate=applied_rate,
        detected_category=detected.name if detected else None,
        source=source,
    )

class CategoryIn(BaseModel):
    name: str
    rate: float = Field(..., ge=0, le=100)
    keywords: List[str] = []
    active: bool = True

@app.get("/api/categories")
async def list_categories():
    try:
        cats = get_documents("gstcategory", {})
        # sanitize
        return [
            {
                "name": c.get("name"),
                "rate": float(c.get("rate", 0)),
                "keywords": c.get("keywords", []),
                "active": bool(c.get("active", True)),
            } for c in cats
        ]
    except Exception:
        return []

@app.post("/api/categories")
async def add_category(cat: CategoryIn):
    try:
        create_document("gstcategory", cat.model_dump())
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
