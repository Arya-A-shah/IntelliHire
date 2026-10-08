from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Dict
from pydantic import Field

GEMINI_SAFETY_SETTINGS: List[Dict[str, str]] = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE"
                }
            ]
        

class Settings(BaseSettings):
    MONGODB_URI: str = Field(default="mongodb://localhost:6017")
    MONGO_DB_NAME: str = Field(default="interview_db")
    JWT_SECRET: str = Field(default="your_jwt_secret_key_here")
    JWT_ALGORITHM: str = Field(default="HS256")
    GEMINI_API_KEY: str = Field(default="")
    GEMINI_API_KEY_EVALUATOR: str = Field(default="")
    GEMINI_API_KEY_REPORTER: str = Field(default="")
    GEMINI_SAFETY_SETTINGS: List[Dict[str, str]] = GEMINI_SAFETY_SETTINGS
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24)  # 1 day
    CARTESIA_API_KEY: str = Field(default="")
    CARTESIA_API_KEY_OLD: str = Field(default="")
    LIVEKIT_URL: str = Field(default="")
    LIVEKIT_API_KEY: str = Field(default="")
    LIVEKIT_API_SECRET: str = Field(default="")
    ANALYSIS_FRAME_RATE: int = Field(default=0)
    FACE_DETECTION_CONFIDENCE: float = Field(default=0)
    EYE_CONTACT_THRESHOLD: float = Field(default=0)
    IMAGEKIT_PRIVATE_KEY: str = Field(default="")
    IMAGEKIT_PUBLIC_KEY: str = Field(default="")
    IMAGEKIT_URL_ENDPOINT: str = Field(default="")
    SMTP_HOST: str = Field(default="smtp.gmail.com")
    SMTP_PORT: int = Field(default=587)
    SMTP_USER: str = Field(default="from@gmail.com")
    SMTP_PASS: str = Field(default="examplePass")
    FROM_EMAIL: str = Field(default="to@gmail.com")
    # Where the React app runs: used for interview links in emails and for CORS.
    FRONTEND_URL: str = Field(default="http://localhost:5173")
    GEMINI_MODEL: str = Field(default="gemini-3.6-flash")
    GEMINI_FALLBACK_MODEL: str = Field(default="gemini-3.5-flash-lite")
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()
