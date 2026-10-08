import re
import asyncio
import uuid
from typing import List, Dict, Optional
from enum import Enum

from pydantic import BaseModel
from google import genai
from google.genai import types

from core.config import gemini_config, nolimit_gemini_config, GEMINI_MODEL, GEMINI_FALLBACK_MODELS
from core.prompts import QUESTION_GENERATION_PROMPT
from services.tts_service import tts_callback


# ---------- Schemas Gemini must follow (structured output) ----------

class eval_schema(BaseModel):
    score: int
    reasoning: str
    follow_up_question: str


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


# ---------- One shared client ----------
# FIX: the old code built a new genai.Client() on every call. One client is
# enough, and its `.aio` side gives async methods that don't freeze the server.
_client: Optional[genai.Client] = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client()
    return _client


SENTENCE_SPLIT = re.compile(r'([.!?]+)\s+')


# ---------- Fallback when Gemini is overloaded ----------
# FIX: a 503 "model is experiencing high demand" from Google used to fail the
# whole step (no questions -> interview could not start). Now every call tries
# the main model, and only if it is overloaded / rate-limited, the fallback.

def _models() -> List[str]:
    models = [GEMINI_MODEL]
    for m in GEMINI_FALLBACK_MODELS:
        if m not in models:
            models.append(m)
    return models


def _is_overloaded(error: Exception) -> bool:
    text = str(error)
    return any(s in text for s in ("503", "UNAVAILABLE", "high demand", "overloaded",
                                    "429", "RESOURCE_EXHAUSTED"))


async def _generate(contents, config):
    """generate_content with the fallback model on overload errors."""
    last_error = None
    for model in _models():
        try:
            return await get_client().aio.models.generate_content(
                model=model, contents=contents, config=config)
        except Exception as e:
            last_error = e
            if not _is_overloaded(e):
                raise
            print(f"[AI] {model} is overloaded, trying the next model...")
    raise last_error


async def _open_stream(contents, config):
    """
    Start a streamed reply, falling back on overload. The 503 usually arrives
    with the first chunk, so we read that chunk here before committing.
    Returns (first_chunk, rest_of_stream).
    """
    last_error = None
    for model in _models():
        try:
            stream = await get_client().aio.models.generate_content_stream(
                model=model, contents=contents, config=config)
            first = await stream.__anext__()
            return first, stream
        except StopAsyncIteration:
            return None, None
        except Exception as e:
            last_error = e
            if not _is_overloaded(e):
                raise
            print(f"[AI] {model} is overloaded, trying the next model...")
    raise last_error


async def _chunks(first, stream):
    if first is not None:
        yield first
    if stream is not None:
        async for chunk in stream:
            yield chunk


async def _emit_sentence(text, message_id, sio, sid, namespace):
    """Send one sentence as text, then queue its speech (audio keeps order)."""
    await sio.emit("ai_partial", {"text": text, "message_id": message_id},
                   to=sid, namespace=namespace)
    asyncio.create_task(tts_callback(text, sio, sid, namespace))


async def stream_text_with_tts(text, sio, sid, namespace=None):
    """Stream an already-known text (e.g. a follow-up question) sentence by sentence."""
    if not text or not text.strip():
        return

    message_id = str(uuid.uuid4())
    parts = re.split(r'([.!?]+)\s*', text)

    i = 0
    while i < len(parts):
        sentence = parts[i].strip()
        punctuation = parts[i + 1] if i + 1 < len(parts) else ""
        complete = f"{sentence}{punctuation}".strip()
        if sentence and len(complete) > 3:
            await _emit_sentence(complete, message_id, sio, sid, namespace)
            await asyncio.sleep(0.05)
        i += 2

    await sio.emit("ai_streaming_complete", {"message_id": message_id},
                   to=sid, namespace=namespace)


async def stream_ai_response(prompt, sio, sid, namespace=None):
    """
    Stream Gemini's reply sentence by sentence: each finished sentence is sent
    to the browser and to text-to-speech while the rest is still generating.
    """
    message_id = str(uuid.uuid4())
    full_response = ""
    buffer = ""

    try:
        # FIX: async streaming. The old sync stream blocked the event loop, so
        # every other candidate's socket froze while one answer was generated.
        first, stream = await _open_stream(prompt, gemini_config)

        async for chunk in _chunks(first, stream):
            candidate = chunk.candidates[0] if chunk.candidates else None
            if candidate and candidate.finish_reason == types.FinishReason.SAFETY:
                await sio.emit("ai_error", {
                    "error": "Response blocked by safety filters. Please rephrase your message.",
                    "message_id": message_id,
                }, to=sid, namespace=namespace)
                return ""

            chunk_text = chunk.text  # None when the chunk has no text parts
            if not chunk_text:
                continue

            full_response += chunk_text
            buffer += chunk_text

            parts = SENTENCE_SPLIT.split(buffer)
            # parts = [sentence, punct, sentence, punct, ..., leftover]
            while len(parts) >= 3:
                sentence = f"{parts[0].strip()}{parts[1]}"
                if len(sentence) > 3:
                    await _emit_sentence(sentence, message_id, sio, sid, namespace)
                parts = parts[2:]
            buffer = "".join(parts)

        leftover = buffer.strip()
        if len(leftover) > 3:
            await _emit_sentence(leftover, message_id, sio, sid, namespace)

        if not full_response.strip():
            fallback = "I apologize, could you please continue?"
            await _emit_sentence(fallback, message_id, sio, sid, namespace)
            full_response = fallback

        await sio.emit("ai_streaming_complete", {"message_id": message_id},
                       to=sid, namespace=namespace)
        return full_response.strip()

    except Exception as e:
        print(f"[AI] Error in stream_ai_response: {e}")
        await sio.emit("ai_error", {
            "error": "I'm having trouble generating a response. Please try again.",
            "message_id": message_id,
        }, to=sid, namespace=namespace)
        return ""


async def evaluator_ai_response(prompt, sio, sid, namespace=None) -> Optional[Dict]:
    """
    Score one answer. Returns a dict {score, reasoning, follow_up_question}
    or None if Gemini failed.

    FIX: the old code read candidate.content.parts[0].text and then ran
    json.loads on it. Newer Gemini models can put a "thinking" part first,
    so parts[0] was not the JSON and parsing failed (every answer scored 5).
    `response.parsed` is the SDK's already-validated object.
    """
    try:
        response = await _generate(prompt, {
            **nolimit_gemini_config,
            "response_mime_type": "application/json",
            "response_schema": eval_schema,
        })
        parsed = response.parsed
        if isinstance(parsed, eval_schema):
            return parsed.model_dump()
        print(f"[AI] Evaluator returned no parsable JSON: {response.text!r}")
        return None

    except Exception as e:
        print(f"[AI] Error in evaluator_ai_response: {e}")
        await sio.emit("ai_error", {
            "error": "I'm having trouble evaluating your answer. Let's continue.",
            "message_id": str(uuid.uuid4()),
        }, to=sid, namespace=namespace)
        return None


async def reporter_ai_response(prompt) -> Optional[str]:
    """
    Write the recruiter report. Returns the text, or None on failure.

    FIX: on failure the old code returned the string "Trouble generating
    report. Please answer again." and that string was saved AS the report.
    Now failure is None, and the caller records it as a failed report.
    """
    try:
        response = await _generate(prompt, nolimit_gemini_config)
        text = (response.text or "").strip()
        if not text:
            raise ValueError("Empty response (possibly safety-filtered)")
        return text
    except Exception as e:
        print(f"Error in report generation: {e}")
        return None


async def generate_interview_questions(job_description: str, resume_text: str) -> List[Dict]:
    """
    Ask Gemini for 7 tailored questions as structured JSON.

    FIX: returns plain dicts. The old code returned Pydantic objects whose
    category/difficulty were Python Enums, which don't store cleanly in
    MongoDB and broke `question["question"]` style access later.
    """
    prompt = QUESTION_GENERATION_PROMPT(job_description, resume_text or "")
    try:
        response = await _generate(prompt, {
            "response_mime_type": "application/json",
            "response_schema": QuestionResponse,
        })
        parsed = response.parsed
        if not isinstance(parsed, QuestionResponse) or not parsed.response:
            raise ValueError(f"Unparsable question list: {response.text!r}")
        return [q.model_dump(mode="json") for q in parsed.response]
    except Exception as e:
        raise ValueError(f"Failed to generate questions with Gemini: {e}")
