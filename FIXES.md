# AI_Interviewer_fixed

A copy of `AI_Interviewer` with bugs fixed. The original folder is untouched.
`git diff HEAD` in this folder shows every change (the last commit, "baseline",
is your original code including your uncommitted edits).

## Run it (macOS)

Not copied: `.venv*`, `node_modules`, `dist`. Recreate them once.

### Backend
```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python check_services.py          # tests every API key: OK / FAIL per service
python main.py                    # API + sockets on http://localhost:8000
```
If check_services says the Gemini model is not available, set
`GEMINI_MODEL=<a name it lists>` in `backend/.env`.

### Frontend (second terminal)
```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173
```

### Offline test (no keys needed)
```bash
cd backend && pip install mongomock-motor httpx
python tests/smoke_test.py        # 16 checks, ends with ALL BACKEND CHECKS PASSED
```

## What was fixed (file: problem -> fix)

Report
- `frontend/.../report-text.jsx` (new), `candidate-drawer.jsx`: Gemini's Markdown
  was shown as raw text (`**`, `##`) -> rendered properly; fenced/JSON reports unwrapped.
- `services/ai_service.py`: on failure the error sentence was saved AS the report -> saved as "failed".
- `routers/interviews.py` report endpoint: score/details always null (getattr on a dict) -> fixed;
  404 while the report was being written -> returns `report_status` pending/ready/failed.
- `hooks/interviewHooks.js`: polls every 5 s until the report is ready.
- `candidate-drawer.jsx`: integrity bar was backwards (more alerts = greener) -> grade-coloured.

Scoring
- `services/scoring.py`: performance band chosen before normalising; per-question score showed
  score x weight -> fixed; scoring errors now saved instead of lost.
- `controllers/interview.py`: failed evaluation invented a 5/10 -> stored as "not evaluated" and skipped.
- `services/ai_service.py` evaluator: read `parts[0].text` + json.loads (breaks with thinking models)
  -> uses `response.parsed`.
- `services/livekit_service.py`: quiet 30 s windows were not counted (one bad moment = bad grade),
  report counted alerts twice, last 10 s of alerts dropped -> fixed.

Interview flow
- `pages/InterviewScreen.jsx`: socket cleanup was inside setTimeout so sockets never closed;
  `/interviews/start` called twice (also in Proctoring) -> called once, token passed down; errors shown.
- `routers/interviews.py`: `/end` always 404 (ObjectId vs string key); any candidate could start any
  interview -> ownership check; calling /start twice wiped the session; 409 if questions not ready.
- `controllers/proctoring.py`: leave_interview crashed (missing `interview_id` key, wrong signature,
  Python-3.12-only f-string).
- `controllers/interview.py`: socket never actually closed at the end; refusals now give a reason;
  browser gets `interview_ended`.
- `services/backgroundtasks.py`: question generation retried 3 times.

Performance
- Gemini now uses the async client; Cartesia and MediaPipe run off the event loop
  (before, one candidate's request froze every other candidate). Audio order kept with a per-socket lock.

Setup
- `requirements.txt` was missing cartesia, livekit, sentence-transformers, imagekitio, aiosmtplib,
  pdfplumber, python-docx, torch -> rewritten.
- `main.py`, `seeders`: Motor -> PyMongo AsyncMongoClient (what Beanie 2.0 expects).
- `core/config.py`: removed unused ElevenLabs / old Gemini SDK / extra sync Mongo client;
  model name in one place (`GEMINI_MODEL`).
- CORS limited to the frontend; `FRONTEND_URL` used for email links; one `API_URL` in the frontend.
- React Query v5 removed `onError` on queries -> global error toast in `App.jsx`.
- `/interview/:id` route now requires login and returns there after login.

Dashboards (second round)
- Recruiter Candidates tab was empty unless you came from "View candidates" -> new
  `GET /applications/recruiter`; applicants whose match score isn't ready are no longer hidden.
- Recruiter responses no longer include password hashes or 384-number embeddings.
- Overview stats and pipeline chart were hard-coded sample numbers -> `GET /jobs/stats`.
- Interviews tab was a fixed message -> `GET /interviews/my` table (score, integrity, report, copy link).
- Export buttons had no onClick -> CSV download. "Import Candidates" had no backend -> replaced by "Export Candidates".
- Job "Edit" button had no onClick -> opens the job dialog in edit mode (`PUT /jobs/{id}`, re-embeds description).
- Candidate dashboard: real stats, Results tab filled, "Start interview" button, empty states,
  working Account / Find Jobs / Log out, resume picker no longer offers .doc (server rejects it).
- Report shows for every stage (was hidden after moving a candidate to Offer/Rejected).
- A completed interview can no longer be restarted (would overwrite its transcript).
- Gemini: several fallback models (`GEMINI_FALLBACK_MODEL=a,b`), retries with backoff,
  questions regenerate when the candidate opens the link.
- Tests: `python tests/dashboard_test.py` (9 checks) alongside `tests/smoke_test.py`.
