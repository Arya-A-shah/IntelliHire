from urllib.parse import parse_qs
import asyncio
from beanie import PydanticObjectId
from core.socket import sio
from dependencies import get_current_user
from services.livekit_service import stop_video_processor
from sharedstate import active_sessions

PROC_NS = "/proc"


@sio.event(namespace=PROC_NS)
async def connect(sid, environ, auth):
    """
    Handle client connection for /proc namespace.
    """
    try:
        print(f"\n{'='*60}")
        print(f"[PROC] Connection attempt - SID: {sid}")
        print(f"[PROC] Auth received: {auth}")
        print(f"[PROC] Query string: {environ.get('QUERY_STRING', '')}")

        # --- Extract token from auth ---
        if not auth or not isinstance(auth, dict):
            raise ValueError("Missing auth data")

        token = auth.get("token")

        if not token:
            raise ValueError("Missing authentication token")

        print(f"[PROC] Token present: {bool(token)}")

        # --- Extract interview_id from QUERY PARAMS (not auth!) ---
        query_string = environ.get("QUERY_STRING", "")
        query_params = parse_qs(query_string)
        interview_id = str(query_params.get("interview_id", [None])[0])

        print(f"[PROC] Interview ID from query: {interview_id}")

        if not interview_id:
            raise ValueError("Missing interview_id in query params")

        # --- Verify user ---
        user = await get_current_user(token)
        user_id = str(getattr(user, "id", None))
        if not user_id:
            raise ValueError("Invalid user")

        print(f"[PROC] User authenticated: {user_id}")
        print(f"[PROC] Active sessions keys: {list(active_sessions.keys())}")

        # Check if interview is active
        if interview_id in active_sessions:
            print(f"[PROC] ✅ Found session with string key")
        else:
            available = list(active_sessions.keys())
            raise PermissionError(
                f"Interview {interview_id} not in active session. "
                f"Available: {available}"
            )

        # --- Join room ---
        active_sessions[interview_id]['proc_socket_id'] = sid
        room_name = f"interview_{interview_id}"
        await sio.enter_room(sid, room_name, namespace=PROC_NS)

        print(f"[PROC] ✅ User {user_id} joined room: {room_name}")
        print(f"{'='*60}\n")

        # --- Emit confirmation ---
        await sio.emit(
            "joined_interview",
            {
                "interview_id": interview_id,
                "status": "connected",
                "message": f"Welcome! Proctoring active."
            },
            to=sid,
            namespace=PROC_NS,
        )

    except Exception as e:
        print(f"[PROC] ❌ Connection error: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")

        # Try to emit error before disconnecting
        try:
            await sio.emit("proc_error", {"error": str(e)}, to=sid, namespace=PROC_NS)
        except:
            pass

        await sio.disconnect(sid, namespace=PROC_NS)


@sio.event(namespace=PROC_NS)
async def disconnect(sid):
    """Handle client disconnection"""
    print(f"[PROC] Client disconnected: {sid}")


@sio.event(namespace=PROC_NS)
async def leave_interview(sid, data=None):
    """Client leaves an interview room"""
    session = next(
            (s for s in active_sessions.values() if s.get("proc_socket_id") == sid),
            None
        )
    if not session:
        print(f"[PROC] Client not found in active proctoring sessions")
    else:
        # FIX: session["interview_id"] used to raise KeyError because the
        # session dict never stored its own id (now /start saves it).
        # Quotes inside an f-string's {} also only work on Python 3.12+,
        # so pull the value out first.
        interview_id = session["interview_id"]
        await stop_video_processor(interview_id)
        print(f"[PROC] Client {sid} leaving interview {interview_id}")
        await sio.leave_room(sid, f"interview_{interview_id}", namespace=PROC_NS)
