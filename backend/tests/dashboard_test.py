"""
Offline test for the dashboard endpoints (recruiter Candidates / Interviews /
Overview tabs and the candidate's applications list).

    python tests/dashboard_test.py        (from the backend folder)
"""
import os, sys, asyncio
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import stubs  # noqa

import httpx
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie

import main
import routers.applications as ra, routers.interviews as ri, services.backgroundtasks as bt
from models import User, Job, Application, Interview, InterviewStatus

ok = lambda m: print("PASS", m)


async def run():
    await init_beanie(database=AsyncMongoMockClient()["d"], document_models=[User, Job, Application, Interview])
    async def fake_upload(f): return "https://example.com/cv.txt"
    async def noop(*a, **k): pass
    async def fake_q(jd, rt): return [{"category": "technical", "difficulty": "easy", "weight": 1.0, "question": "Q?"}]
    ra.upload_resume_to_imagekit = fake_upload; ra.send_email = noop
    bt.generate_interview_questions = fake_q; ri.start_video_processor = noop

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://t") as c:
        async def signup(email, role):
            r = await c.post("/auth/signup", json={"email": email, "password": "pw", "name": email.split("@")[0], "role": role})
            return {"Authorization": "Bearer " + r.json()["access_token"]}
        rec = await signup("rec@x.com", "recruiter")
        can1 = await signup("ana@x.com", "candidate")
        can2 = await signup("bob@x.com", "candidate")

        r = await c.get("/jobs/stats", headers=rec); s = r.json()
        assert r.status_code == 200 and s["active_jobs"] == 0 and s["offer_rate"] == 0, s
        ok("stats work with an empty account")

        jobs = []
        for title in ("Backend Dev", "Frontend Dev"):
            r = await c.post("/jobs/", json={"title": title, "description": f"{title} role", "location": "Remote", "type": "Full-time", "tags": []}, headers=rec)
            jobs.append(r.json()["_id"])
        for hdr, job in ((can1, jobs[0]), (can2, jobs[0]), (can2, jobs[1])):
            r = await c.post("/applications/", data={"job_id": job}, files={"resume": ("cv.txt", b"Python developer", "text/plain")}, headers=hdr)
            assert r.status_code == 200, r.text

        # one application whose match score is not ready yet
        a = await Application.find_one(Application.job_id == jobs[1]); a.match_score = None; await a.save()

        r = await c.get("/applications/recruiter", headers=rec); rows = r.json()
        assert r.status_code == 200 and len(rows) == 3, rows
        assert rows[-1]["match_score"] is None, "unscored should be last"
        assert all(row["candidate"]["name"] and row["job"]["title"] for row in rows)
        assert not any(k in str(rows) for k in ("hashed_password", "resume_embedding", "job_description_embedding"))
        ok("Candidates tab without a job: all 3 applicants, unscored last, no password hashes or embeddings")

        r = await c.get(f"/jobs/{jobs[1]}/ranked", headers=rec)
        assert len(r.json()) == 1
        ok("per-job list now includes an applicant whose score isn't ready (was hidden)")

        r = await c.get("/jobs/my", headers=rec)
        assert r.json()[0]["description"] and "tags" in r.json()[0]
        r = await c.put(f"/jobs/{jobs[0]}", json={"title": "Senior Backend Dev"}, headers=rec)
        assert r.status_code == 200 and r.json()["title"] == "Senior Backend Dev"
        ok("job list has description/tags for Edit; PUT updates the job")

        rows = (await c.get("/applications/recruiter", headers=rec)).json()
        ana_app = next(r for r in rows if r["candidate"]["email"] == "ana@x.com")["_id"]
        r = await c.get(f"/interviews/report/{ana_app}", headers=rec)
        assert r.status_code == 200 and r.json()["report_status"] == "no_interview"
        ok("report for a not-shortlisted candidate is 'no_interview' (was a 404 error)")

        await c.patch(f"/applications/{ana_app}", json={"status": "interview"}, headers=rec)
        bob_rows = [r for r in rows if r["candidate"]["email"] == "bob@x.com"]
        await c.patch(f"/applications/{bob_rows[0]['_id']}", json={"status": "offer"}, headers=rec)

        r = await c.get("/jobs/stats", headers=rec); s = r.json()
        stages = {p["stage"]: p["count"] for p in s["pipeline"]}
        assert s["active_jobs"] == 2 and s["total_candidates"] == 3 and s["new_candidates_7d"] == 3
        assert s["interviews_scheduled"] == 1 and stages == {"Applied": 1, "Screening": 0, "Interview": 1, "Offer": 1, "Rejected": 0}
        assert s["offer_rate"] == 33
        ok(f"stats are real: {s['active_jobs']} jobs, 3 candidates, 1 interview, offer rate {s['offer_rate']}%")

        r = await c.get("/interviews/my", headers=rec); iv = r.json()
        assert len(iv) == 1 and iv[0]["status"] == "scheduled" and iv[0]["application"]["candidate"]["email"] == "ana@x.com"
        assert iv[0]["questions_ready"] is True and iv[0]["meeting_url"]
        ok("Interviews tab lists the interview with candidate, job and link")

        r = await c.get("/applications/", headers=can1); mine = r.json()
        assert mine[0]["interview"]["status"] == "scheduled" and mine[0]["interview"]["id"] == iv[0]["interview_id"]
        r = await c.get("/applications/", headers=can2)
        assert all(a["interview"] is None for a in r.json())
        ok("candidate sees their interview (for the Start interview button)")

        doc = await Interview.get(iv[0]["interview_id"])
        doc.status = InterviewStatus.completed; doc.result = {"overall_score": 72.0, "performance": "good"}; await doc.save()
        r = await c.post(f"/interviews/start/{doc.id}", headers=can1)
        assert r.status_code == 409 and "already been completed" in r.text
        r = await c.get("/applications/", headers=can1)
        assert r.json()[0]["interview"]["score"] == 72.0
        ok("a completed interview can't be restarted; candidate Results get the score")

    print("\nALL DASHBOARD CHECKS PASSED")

asyncio.run(run())
