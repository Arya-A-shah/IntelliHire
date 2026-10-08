"""
Offline smoke test: runs the whole hiring + interview flow against an
in-memory MongoDB with Gemini, Cartesia, LiveKit and ImageKit faked out.

    pip install mongomock-motor httpx
    python tests/smoke_test.py        (from the backend folder)
"""
import os, sys, asyncio, types, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import stubs  # noqa  (fake embedding model, so no torch download needed)
from datetime import datetime, timedelta
import httpx
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie

import main
from models import User, Job, Application, Interview
import routers.applications as ra, routers.interviews as ri
import services.backgroundtasks as bt, services.scoring as sc
import controllers.interview as ci, controllers.proctoring as cp
import services.livekit_service as ls, services.ai_service as ai, services.tts_service as tts
from sharedstate import active_sessions

QUESTIONS = [
    {"category": "technical", "difficulty": "easy", "weight": 0.2, "question": "What is FastAPI?"},
    {"category": "technical", "difficulty": "medium", "weight": 0.3, "question": "Explain async."},
    {"category": "behavioral", "difficulty": "hard", "weight": 0.5, "question": "Tell me about a conflict."},
]
ok = lambda m: print("PASS", m)

class FakeSio:
    def __init__(s): s.events = []
    async def emit(s, ev, data=None, **k): s.events.append((ev, data))
    async def disconnect(s, sid, namespace=None): s.events.append(("__disconnect", sid))
    async def leave_room(s, *a, **k): pass
    async def enter_room(s, *a, **k): pass
    async def close_room(s, *a, **k): pass
    def start_background_task(s, fn, *a): s.bg = asyncio.ensure_future(fn(*a))

async def run():
    await init_beanie(database=AsyncMongoMockClient()["t"], document_models=[User, Job, Application, Interview])

    async def fake_upload(f): return "https://example.com/resume.txt"
    ra.upload_resume_to_imagekit = fake_upload
    async def fake_email(*a, **k): pass
    ra.send_email = fake_email
    async def fake_q(jd, rt): return QUESTIONS
    bt.generate_interview_questions = fake_q
    async def noop(*a, **k): pass
    ri.start_video_processor = noop; ri.stop_video_processor = noop

    tr = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=tr, base_url="http://t") as c:
        r = await c.post("/auth/signup", json={"email": "rec@x.com", "password": "pw", "name": "Rec", "role": "recruiter"}); assert r.status_code == 200, r.text
        rec = {"Authorization": "Bearer " + r.json()["access_token"]}
        r = await c.post("/auth/signup", json={"email": "can@x.com", "password": "pw", "name": "Can", "role": "candidate"})
        can_token = r.json()["access_token"]; can = {"Authorization": "Bearer " + can_token}
        r = await c.post("/auth/signup", json={"email": "other@x.com", "password": "pw", "name": "Oth", "role": "candidate"})
        oth = {"Authorization": "Bearer " + r.json()["access_token"]}
        r = await c.post("/auth/login", json={"email": "can@x.com", "password": "pw", "role": "candidate"}); assert r.status_code == 200
        r = await c.post("/auth/login", json={"email": "can@x.com", "password": "bad", "role": "candidate"}); assert r.status_code == 401
        ok("signup / login / wrong password")

        r = await c.post("/jobs/", json={"title": "Backend Dev", "description": "Python FastAPI MongoDB", "location": "Remote", "type": "Full-time", "tags": ["python"]}, headers=rec)
        assert r.status_code == 200, r.text; job_id = r.json()["_id"]
        r = await c.get("/jobs/", headers=can); assert len(r.json()) == 1
        ok("create + list jobs")

        r = await c.post("/applications/", data={"job_id": job_id}, files={"resume": ("cv.txt", b"Python FastAPI developer", "text/plain")}, headers=can)
        assert r.status_code == 200, r.text; app_id = r.json()["_id"]
        app = await Application.get(app_id); assert app.resume_text and app.match_score is not None, app
        r = await c.get(f"/jobs/{job_id}/ranked", headers=rec); assert len(r.json()) == 1
        ok(f"apply, resume parsed, match score {app.match_score}%, ranked list")

        r = await c.patch(f"/applications/{app_id}", json={"status": "interview"}, headers=rec); assert r.status_code == 200, r.text
        iv = await Interview.find_one(Interview.application_id == app_id)
        assert iv.questions == QUESTIONS and iv.meeting_url.startswith("http://localhost:5173/interview/")
        iid = str(iv.id)
        ok("shortlist -> interview created, questions saved, link uses FRONTEND_URL")

        r = await c.get(f"/interviews/report/{app_id}", headers=rec)
        assert r.status_code == 200 and r.json()["report_status"] == "pending", r.text
        ok("report endpoint says 'pending' before the interview (was a 404 error)")

        r = await c.post(f"/interviews/start/{iid}", headers=oth); assert r.status_code == 403, r.text
        ok("another candidate cannot start this interview (403)")
        r = await c.post(f"/interviews/start/{iid}", headers=can); assert r.status_code == 200, r.text
        assert r.json()["token"] and r.json()["room_name"] == f"interview_{iid}"
        active_sessions[iid]["ai_socket_id"] = "keep-me"
        r = await c.post(f"/interviews/start/{iid}", headers=can); assert r.status_code == 200
        assert active_sessions[iid]["ai_socket_id"] == "keep-me"
        ok("start returns LiveKit token; calling it twice keeps the session")

    # ---- AI socket flow with fake Gemini ----
    fs = FakeSio(); ci.sio = fs
    async def fake_stream(prompt, sio, sid, namespace=None): return "Hello, here is your question."
    evals = iter([
        {"score": 4, "reasoning": "shallow", "follow_up_question": "Can you go deeper?"},
        {"score": 7, "reasoning": "better", "follow_up_question": "None"},
        None,  # Gemini failure -> score None, skipped by scorer
        {"score": 9, "reasoning": "great", "follow_up_question": "None"},
    ])
    async def fake_eval(*a, **k): return next(evals)
    async def fake_tts_stream(*a, **k): pass
    ci.stream_ai_response = fake_stream; ci.evaluator_ai_response = fake_eval; ci.stream_text_with_tts = fake_tts_stream
    async def fake_report(prompt):
        assert "/ 100" in prompt; return "**Overview:** Solid candidate.\n\nStrong on async."
    sc.reporter_ai_response = fake_report
    ci.get_integrity_score = lambda i: {"score": 0.5, "grade": "A", "status": "Excellent", "total_windows": 2, "average": 0.5, "max": 1}
    ci.get_detailed_integrity_report = lambda i: {"windows": []}
    ci.stop_video_processor = noop

    from socketio.exceptions import ConnectionRefusedError as CRE
    try:
        await ci.connect("sid1", {"QUERY_STRING": "interview_id=000000000000000000000000"}, {"token": can_token})
        raise AssertionError("should refuse")
    except CRE as e:
        ok(f"AI socket refuses an inactive interview with a reason: {e}")

    await ci.connect("sid1", {"QUERY_STRING": f"interview_id={iid}"}, {"token": can_token})
    for answer in ["FastAPI is a framework", "It uses Pydantic and ASGI", "async lets IO overlap", "I resolved a conflict by..."]:
        await ci.user_message("sid1", answer)
    await asyncio.sleep(0.2)
    if hasattr(fs, "bg"): await fs.bg
    names = [e[0] for e in fs.events]
    assert "interview_ended" in names and "__disconnect" in names, names
    iv = await Interview.get(iid)
    assert iv.status == "completed" and len(iv.transcript) == 4
    assert [t["is_follow_up"] for t in iv.transcript] == [False, True, False, False]
    ok("interview loop: follow-up asked, failed eval tolerated, ends + socket closed")

    # q0: (4+7)/2=5.5 w0.2 ; q1: None skipped ; q2: 9 w0.5 -> (1.1+4.5)/0.7*10 = 80.0
    res = iv.result
    assert res["overall_score"] == 80.0 and res["performance"] == "excellent", res
    assert res["details"][0]["score"] == 5.5 and res["details"][0]["num_followups"] == 1
    assert iv.report.startswith("**Overview")
    ok(f"score {res['overall_score']}/100 ({res['performance']}), per-question score is the real 0-10 average, report saved")

    tr = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=tr, base_url="http://t") as c:
        r = await c.get(f"/interviews/report/{app_id}", headers=rec); j = r.json()
        assert j["report_status"] == "ready" and j["score"] == 80.0 and j["details"], j
        ok("report endpoint returns score + details (were always null)")
        active_sessions[iid]["status"] = "active"
        r = await c.post(f"/interviews/end/{iid}", headers=can); assert r.status_code == 200, r.text
        ok("end endpoint works (always 404 before)")

    # ---- failure paths ----
    async def bad_report(p): return None
    sc.reporter_ai_response = bad_report
    iv.report = None; await iv.save()
    await sc.calculate_interview_score(iid)
    iv = await Interview.get(iid); assert iv.report is None and iv.result.get("report_error")
    ok("Gemini report failure is recorded as failed, not saved as the report text")

    # ---- proctoring leave (used to crash: KeyError + wrong signature) ----
    cp.sio = FakeSio(); cp.stop_video_processor = noop
    active_sessions["x"] = {"interview_id": "x", "proc_socket_id": "psid"}
    await cp.leave_interview("psid", {"interview_id": "x"})
    ok("/proc leave_interview accepts the payload the browser sends")

    # ---- integrity tracker ----
    t = ls.IntegrityScoreTracker()
    t.interview_start_time = datetime.now() - timedelta(minutes=10)
    t.current_window["start_time"] = datetime.now() - timedelta(seconds=5)
    for _ in range(3): t.add_alert("looking_left")
    s = t.get_integrity_score()
    assert s["total_windows"] in (20, 21) and s["grade"] == "A", s
    r1 = t.get_detailed_report(); r2 = t.get_detailed_report()
    assert len(r1["windows"]) == len(r2["windows"]) == 1 and r2["integrity_score"]["total_alerts"] == 3
    ok("integrity: 3 alerts in 10 min = grade A (was C); report twice doesn't double count")

    # ---- sentence streaming + audio order with fake Gemini/Cartesia ----
    class Chunk:
        def __init__(s, t): s.text = t; s.candidates = []
    class FakeAio:
        async def generate_content_stream(s, **k):
            async def gen():
                for p in ["Hello there. This is a te", "st of streaming! And the l", "ast part"]:
                    yield Chunk(p)
            return gen()
    ai._client = types.SimpleNamespace(aio=types.SimpleNamespace(models=FakeAio()))
    import time
    def slow_synth(text):
        time.sleep(0.3 if text.startswith("Hello") else 0.01)  # first sentence slowest
        return text.encode()
    tts._synthesize = slow_synth
    fs2 = FakeSio()
    out = await ai.stream_ai_response("p", fs2, "s2", "/ai")
    await asyncio.sleep(1.0)
    texts = [d["text"] for e, d in fs2.events if e == "ai_partial"]
    audio = [__import__("base64").b64decode(d["audio"]).decode() for e, d in fs2.events if e == "ai_audio_blob"]
    assert texts == ["Hello there.", "This is a test of streaming!", "And the last part"], texts
    assert audio == texts, audio
    ok("sentences split correctly and audio arrives in order even when sentence 1 is slowest")

    print("\nALL BACKEND CHECKS PASSED")

asyncio.run(run())
