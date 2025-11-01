from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from ..security import create_jwt
from ..db import SessionLocal
from ..models import AuditLog
from ..utils.redis_cache import get_redis_client

router = APIRouter()
r = get_redis_client()

class SessionRequest(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None
    code: str

class SessionResponse(BaseModel):
    token: str

@router.post("/v1/sessions", response_model=SessionResponse)
def create_session(body: SessionRequest):
    sub = body.email or body.phone
    if not sub:
        raise HTTPException(status_code=422, detail="Provide email or phone")
    k = f"otp:{sub}"
    val = r.get(k)
    if not val or val != body.code:
        raise HTTPException(status_code=401, detail="Invalid OTP")
    r.delete(k)
    token = create_jwt(sub)
    # audit
    with SessionLocal() as db:
        db.add(AuditLog(actor=sub, action="SESSION_CREATED", target=sub, details={"method":"otp"}))
        db.commit()
    return SessionResponse(token=token)
