# IntelliHire: AI interview platform

Recruiters post jobs; candidates apply and take a **live voice interview with an AI interviewer**. The system asks role-specific questions, listens, follows up, proctors the session, and produces a scored report for the recruiter.

## Features

- **Real-time voice interview** over LiveKit (WebRTC), with a natural-sounding interviewer voice (Cartesia TTS)
- **Question generation and answer evaluation** with Google Gemini, using separate evaluator and report-writer roles
- **Proctoring**: face detection and eye-contact tracking with MediaPipe + OpenCV
- **Voice analysis** of answers (tone / confidence signals)
- **Recruiter dashboard**: job postings, candidate pipeline chart, candidate drawer with the full AI report, CSV export
- **Candidate dashboard**: applications, interview status, results
- Resume parsing (PDF / DOCX), media storage on ImageKit, email notifications

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | React 19, Vite, Tailwind CSS, shadcn/ui, TanStack Query, Zustand, LiveKit components |
| Backend | FastAPI, python-socketio, Beanie (MongoDB ODM), JWT auth |
| AI / media | Gemini, Cartesia, LiveKit, MediaPipe, OpenCV, sentence-transformers |
| Database | MongoDB |

## Run locally

**Backend** (Python 3.12)
```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # fill in your own keys
python check_services.py          # checks every API key: OK / FAIL per service
python main.py                    # API + sockets on http://localhost:8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173
```

**Offline smoke test** (no API keys needed)
```bash
cd backend && pip install mongomock-motor httpx
python tests/smoke_test.py
```

See `FIXES.md` for the list of bugs fixed in this version.
