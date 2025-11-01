from fastapi import APIRouter
router = APIRouter()

@router.get("/healthz")
def healthz():
    return {"status": "ok"}

@router.get("/readyz")
def readyz():
    return {"ready": True}
