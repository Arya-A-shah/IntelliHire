from fastapi import HTTPException, status
from models import User, UserRole
from utils import hash_password, verify_password, create_access_token
from beanie import PydanticObjectId

class AuthService:
    @staticmethod
    async def signup(email: str, password: str, name: str, role: UserRole) -> str:
        existing = await User.find_one(User.email == email)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        hashed_pw = hash_password(password)
        user = User(email=email, hashed_password=hashed_pw, name=name, role=role)
        await user.insert()
        access_token = create_access_token({"user_id": str(user.id), "role": user.role.value})
        return access_token

    @staticmethod
    async def login(email: str, password: str) -> str:
        user = await User.find_one(User.email == email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        access_token = create_access_token({"user_id": str(user.id), "role": user.role.value})
        return access_token