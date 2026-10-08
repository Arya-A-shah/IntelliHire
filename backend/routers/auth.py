from fastapi import APIRouter, HTTPException, status
from models import User, UserRole
from utils import hash_password, verify_password, create_access_token
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    role: UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/signup", response_model=TokenResponse)
async def signup(data: SignupRequest):
    existing = await User.find_one(User.email == data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_pw = hash_password(data.password)
    user = User(
        email=data.email,
        hashed_password=hashed_pw,
        name=data.name,
        role=data.role
    )
    await user.insert()

    access_token = create_access_token({
        "user_id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role.value
    })

    return TokenResponse(
        access_token=access_token,
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    user = await User.find_one(User.email == data.email, User.role == data.role)
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    access_token = create_access_token({
        "user_id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role.value
    })

    return TokenResponse(
        access_token=access_token,
    )
