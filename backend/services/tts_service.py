import asyncio
import base64
import uuid
from typing import Dict

from cartesia import Cartesia
from config import settings

MODEL_ID = "sonic-3"
VOICE_ID = "791d5162-d5eb-40f0-8189-f19db44611d8"
SAMPLE_RATE = 44100  # what we ask Cartesia for AND what we tell the browser

_client = None

# FIX (audio order): one lock per socket. Sentences for the same candidate are
# synthesized one after another, in the order they were queued. asyncio.Lock
# hands itself out first-come-first-served, so sentence 2 can never be spoken
# before sentence 1, even though the work now runs in a background thread.
_locks: Dict[str, asyncio.Lock] = {}


def _get_client() -> Cartesia:
    global _client
    if _client is None:
        _client = Cartesia(api_key=settings.CARTESIA_API_KEY)
    return _client


def _synthesize(text: str) -> bytes:
    """Blocking Cartesia call: returns raw 32-bit float PCM for one sentence."""
    ws = _get_client().tts.websocket()
    try:
        chunks = []
        for output in ws.send(
            model_id=MODEL_ID,
            transcript=text,
            voice_id=VOICE_ID,
            stream=True,
            output_format={
                "container": "raw",
                "encoding": "pcm_f32le",
                "sample_rate": SAMPLE_RATE,
            },
            context_id=str(uuid.uuid4()),
        ):
            if output.get("audio"):
                chunks.append(output["audio"])
        return b"".join(chunks)
    finally:
        ws.close()


def forget_socket(sid: str) -> None:
    """Drop the lock for a socket that has left."""
    _locks.pop(sid, None)


async def tts_callback(text, sio, sid, namespace=None, sentence_id=None):
    """Turn one sentence into speech and send it as a base64 blob."""
    if not text or not text.strip():
        return

    lock = _locks.setdefault(sid, asyncio.Lock())
    async with lock:
        try:
            # FIX (frozen server): the Cartesia SDK is synchronous. Calling it
            # directly inside async code stopped the whole event loop until the
            # audio was ready. asyncio.to_thread runs it on a worker thread.
            audio_bytes = await asyncio.to_thread(_synthesize, text)

            if not audio_bytes:
                await sio.emit("ai_error", "TTS returned no audio", to=sid, namespace=namespace)
                return

            await sio.emit(
                "ai_audio_blob",
                {
                    "sentence_id": sentence_id,
                    "audio": base64.b64encode(audio_bytes).decode("utf-8"),
                    "mime": "audio/raw",
                    "sample_rate": SAMPLE_RATE,
                },
                to=sid,
                namespace=namespace,
            )
        except Exception as e:
            print(f"[TTS] Error: {e}")
            await sio.emit("ai_error", f"TTS error: {e}", to=sid, namespace=namespace)
