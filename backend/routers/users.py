from fastapi import APIRouter, Depends, HTTPException, status
from models import User, UserUpdate
from dependencies import get_current_user
from datetime import datetime

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=User )
async def get_profile(user: User = Depends(get_current_user)):
    return user

@router.put("/me", response_model=User )
async def update_profile(update: UserUpdate, user: User = Depends(get_current_user)):
    updated = False
    if update.name is not None:
        user.name = update.name
        updated = True
    if updated:
        user.updated_at = datetime.utcnow()
        await user.save()
    return user