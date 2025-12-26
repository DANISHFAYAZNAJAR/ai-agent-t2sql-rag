"""
JWT Authentication endpoints
"""
from ninja import Router
from ninja.security import HttpBearer
from django.conf import settings
import jwt
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel

router = Router()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET_KEY, 
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


# For demo purposes, simple authentication
# In production, use proper user authentication
DEMO_USERS = {
    "admin": "admin123",
    "user": "user123"
}


@router.post("/login", response=TokenResponse)
def login(request, credentials: LoginRequest):
    """
    Authenticate user and return JWT token
    """
    # Simple demo authentication
    if credentials.username in DEMO_USERS and DEMO_USERS[credentials.username] == credentials.password:
        # Generate JWT token
        payload = {
            'username': credentials.username,
            'exp': datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            'iat': datetime.utcnow()
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return TokenResponse(access_token=token)
    
    from ninja.responses import Response
    return Response({"error": "Invalid credentials"}, status=401)


@router.get("/verify")
def verify_token(request):
    """
    Verify JWT token
    """
    return {"message": "Token is valid", "user": request.auth.get('username')}

