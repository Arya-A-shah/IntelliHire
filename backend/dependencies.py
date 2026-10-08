from fastapi import Depends, HTTPException, status, UploadFile
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from models import User, UserRole
from utils import decode_access_token
from beanie import PydanticObjectId
from docx import Document as DocxDocument
import pdfplumber
import io


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid authentication credentials")
    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid authentication credentials")
    user = await User.get(PydanticObjectId(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User  not found")
    return user


def require_role(*roles: UserRole):
    async def role_checker(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Operation not permitted")
        return user
    return role_checker


async def extract_text_from_bytes(file_bytes: bytes, filename: str, content_type: str) -> str:
    """
    Extract text from bytes of a file (.pdf, .docx, .txt).

    Args:
        file_bytes: Raw file content
        filename: Name of the file (used for extension detection)
        content_type: MIME type of the file

    Returns:
        Extracted text content

    Raises:
        ValueError: If file type is unsupported or extraction fails
    """
    file_ext = filename.rsplit('.', 1)[-1].lower() if filename else ""

    text = ""

    try:
        if file_ext == "pdf":
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

        elif file_ext == "docx":
            doc = DocxDocument(io.BytesIO(file_bytes))
            for para in doc.paragraphs:
                text += para.text + "\n"

        elif file_ext == "txt":
            text = file_bytes.decode('utf-8', errors='ignore')

        else:
            raise ValueError(f"Unsupported file type: .{file_ext}")

    except Exception as e:
        raise ValueError(f"Failed to extract text from {filename}: {str(e)}")

    return text.strip()
