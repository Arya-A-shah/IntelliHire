import os
import logging
from dotenv import load_dotenv

# Newer Gemini models attach a hidden "thought_signature" part to replies. The
# SDK prints a warning every time we read response.text; it is harmless noise.
logging.getLogger("google_genai.types").setLevel(logging.ERROR)

# load_dotenv() copies .env into os.environ. The google-genai client reads
# GEMINI_API_KEY (or GOOGLE_API_KEY) from there, so this must run first.
load_dotenv()

# One place to change the model for every Gemini call (set GEMINI_MODEL in .env).
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

# Tried in order when the main model is overloaded (503) or rate-limited (429).
# Comma-separated list in .env, e.g.
#   GEMINI_FALLBACK_MODEL=gemini-3.6-flash,gemini-3.5-flash-lite
# Leave empty to disable.
GEMINI_FALLBACK_MODELS = [
    m.strip() for m in os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite").split(",")
    if m.strip()
]

# Used by the interviewer (spoken questions): a bit of creativity.
gemini_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
}

# Used by the evaluator and the report writer: more consistent output.
nolimit_gemini_config = {
    "temperature": 0.5,
    "top_p": 0.9,
    "top_k": 30,
}
