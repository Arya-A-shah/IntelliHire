import json
from typing import List, Dict
from core.config import gemini_config
from core.prompts import QUESTION_GENERATION_PROMPT
from pydantic import BaseModel
from enum import Enum
from config import settings
from google import genai

class Category(Enum):
    technical = "technical"
    behavioral = "behavioral"


class Difficulty(Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class QuestionModel(BaseModel):
    category: Category
    difficulty: Difficulty
    weight: float
    question: str


class QuestionResponse(BaseModel):
    response: List[QuestionModel]

async def generate_interview_questions(job_description: str, resume_text: str) -> List[Dict[str, str]]:
    job_text = job_description
    resume_text = resume_text or ""
    client = genai.Client()
    
    try:
        prompt = QUESTION_GENERATION_PROMPT(job_text, resume_text)
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": QuestionResponse,
            },
        )
        
        return response.parsed.response

    except Exception as e:
        # Use getattr to safely get partial response text (if available)
        response_text = getattr(e, "message", str(e))
        raise ValueError(f"Failed to generate or parse Gemini response. Error: {response_text}")
