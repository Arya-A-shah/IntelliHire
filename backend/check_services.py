"""
Checks every outside service the app needs, using the keys in .env.
Run it from the backend folder with your venv active:

    python check_services.py

It never prints your keys. Each line ends in OK or FAIL plus the reason.
"""
import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()
from config import settings  # noqa: E402  (reads .env too)

results = []


def report(name, ok, detail=""):
    results.append(ok)
    mark = "OK  " if ok else "FAIL"
    print(f"[{mark}] {name:<22} {detail}")


async def check_mongodb():
    from pymongo import AsyncMongoClient
    client = AsyncMongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=8000)
    try:
        await client.admin.command("ping")
        db = client[settings.MONGO_DB_NAME]
        names = await db.list_collection_names()
        report("MongoDB", True, f"connected, db '{settings.MONGO_DB_NAME}' has {len(names)} collections")
    except Exception as e:
        report("MongoDB", False, f"{type(e).__name__}: {str(e)[:150]}  (check URI, password, Atlas IP allow-list)")
    finally:
        await client.close()


EXTRA_MODELS = [
    "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
]


async def check_gemini():
    """
    Tries a tiny prompt on your main model, your fallbacks, and a few other
    Flash models, so you can see which ones are answering right now.
    """
    from google import genai
    from core.config import GEMINI_MODEL, GEMINI_FALLBACK_MODELS  # also silences the thought_signature warning

    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        report("Gemini", False, "GEMINI_API_KEY is not set in .env")
        return

    client = genai.Client()
    try:
        available = {m.name.replace("models/", "") async for m in await client.aio.models.list()}
        configured = [GEMINI_MODEL] + [m for m in GEMINI_FALLBACK_MODELS if m != GEMINI_MODEL]
        to_try = configured + [m for m in EXTRA_MODELS if m not in configured]

        working = []
        print("  Gemini models (main and fallbacks marked *):")
        for model in to_try:
            mark = "*" if model in configured else " "
            if model not in available:
                print(f"   {mark} {model:<24} not available to this key")
                continue
            try:
                r = await asyncio.wait_for(
                    client.aio.models.generate_content(model=model, contents="Reply with one word: ready"),
                    timeout=30)
                print(f"   {mark} {model:<24} OK ({(r.text or '').strip()[:20]!r})")
                working.append(model)
            except asyncio.TimeoutError:
                print(f"   {mark} {model:<24} timed out")
            except Exception as e:
                msg = str(e)
                reason = ("503 overloaded" if "503" in msg else
                          "429 quota / rate limit" if "429" in msg else msg[:80])
                print(f"   {mark} {model:<24} FAIL: {reason}")

        usable = [m for m in configured if m in working]
        if usable:
            report("Gemini", True, f"the app will use '{usable[0]}' right now")
        elif working:
            report("Gemini", False,
                   "none of your configured models answer. Put these in .env:  "
                   f"GEMINI_MODEL={working[0]}  GEMINI_FALLBACK_MODEL={','.join(working[1:3])}")
        else:
            report("Gemini", False, "no Flash model answered (all overloaded or quota). Try again later.")
    except Exception as e:
        report("Gemini", False, f"{type(e).__name__}: {str(e)[:200]}")
    finally:
        await client.aio.aclose()  # avoids the "Unclosed client session" warning


def check_cartesia():
    try:
        from services.tts_service import _synthesize, SAMPLE_RATE
        audio = _synthesize("Hello, this is a test.")
        seconds = len(audio) / 4 / SAMPLE_RATE  # 4 bytes per float32 sample
        ok = len(audio) > 0
        report("Cartesia TTS", ok, f"got {len(audio)} bytes (~{seconds:.1f}s of audio)" if ok else "no audio returned")
    except Exception as e:
        report("Cartesia TTS", False, f"{type(e).__name__}: {str(e)[:200]}")


async def check_livekit():
    from livekit import api
    url = settings.LIVEKIT_URL.replace("wss://", "https://").replace("ws://", "http://")
    lk = api.LiveKitAPI(url, settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
    try:
        rooms = await lk.room.list_rooms(api.ListRoomsRequest())
        report("LiveKit", True, f"key accepted, {len(rooms.rooms)} active rooms")
    except Exception as e:
        report("LiveKit", False, f"{type(e).__name__}: {str(e)[:200]}")
    finally:
        await lk.aclose()


def check_imagekit():
    try:
        from imagekitio.models.ListAndSearchFileRequestOptions import ListAndSearchFileRequestOptions
        from services.imagekit_service import imagekit
        res = imagekit.list_files(ListAndSearchFileRequestOptions(limit=1))
        report("ImageKit", True, f"key accepted ({len(res.list or [])} file listed)")
    except Exception as e:
        report("ImageKit", False, f"{type(e).__name__}: {str(e)[:200]}")


async def check_smtp():
    import aiosmtplib
    try:
        smtp = aiosmtplib.SMTP(hostname=settings.SMTP_HOST, port=settings.SMTP_PORT, start_tls=True, timeout=15)
        await smtp.connect()
        await smtp.login(settings.SMTP_USER, settings.SMTP_PASS)
        await smtp.quit()
        report("Gmail SMTP", True, f"logged in as {settings.SMTP_USER} (no email sent)")
    except Exception as e:
        report("Gmail SMTP", False, f"{type(e).__name__}: {str(e)[:200]}  (Gmail needs an App Password)")


def check_embeddings():
    try:
        from sentence_transformers import SentenceTransformer, util
        m = SentenceTransformer("all-MiniLM-L6-v2")
        a, b = m.encode(["Python FastAPI developer", "Backend engineer using FastAPI"])
        report("Embedding model", True, f"loaded, sample similarity {float(util.cos_sim(a, b)):.2f}")
    except Exception as e:
        report("Embedding model", False, f"{type(e).__name__}: {str(e)[:200]}")


def check_mediapipe():
    try:
        import numpy as np
        from services.video_processor import analyze_frame
        events = analyze_frame(np.zeros((480, 640, 3), dtype=np.uint8))
        report("MediaPipe", events == ["no_face_detected"], f"blank frame -> {events}")
    except Exception as e:
        report("MediaPipe", False, f"{type(e).__name__}: {str(e)[:200]}")


async def main():
    print("Checking services...\n")
    await check_mongodb()
    await check_gemini()
    check_cartesia()
    await check_livekit()
    check_imagekit()
    await check_smtp()
    check_embeddings()
    check_mediapipe()
    failed = results.count(False)
    print(f"\n{len(results) - failed} OK, {failed} FAIL")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main())
