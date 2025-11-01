from datetime import datetime, timedelta
from jose import jwt
from .settings import settings

def create_jwt(sub: str, ttl_minutes: int = 60) -> str:
    payload = {
        "sub": sub,
        "exp": datetime.utcnow() + timedelta(minutes=ttl_minutes),
        "iat": datetime.utcnow(),
        "iss": "health-app",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
