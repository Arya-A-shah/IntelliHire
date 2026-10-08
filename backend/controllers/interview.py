from urllib.parse import parse_qs
from socketio.exceptions import ConnectionRefusedError
import json
from models import Interview, InterviewStatus
from beanie import PydanticObjectId
from core.socket import sio
from core.prompts import INTERVIEWER_PROMPT, ANSWER_EVALUATION_PROMPT
from dependencies import get_current_user
from services.ai_service import stream_ai_response, evaluator_ai_response, stream_text_with_tts
from services.backgroundtasks import generate_score_report_
from services.tts_service import forget_socket
from services.livekit_service import get_detailed_integrity_report, get_integrity_score, stop_video_processor
from sharedstate import active_sessions

conversation_sessions = {}
MAX_FOLLOWUP_DEPTH = 2  # limit follow-ups per question
AI_NS = "/ai"


@sio.event(namespace=AI_NS)
async def connect(sid, environ, auth):
    """Handle AI socket connection"""
    try:
        print(f"\n{'='*60}")
        print(f"[AI] Connection attempt - SID: {sid}")

        token = None
        if auth and isinstance(auth, dict):
            token = auth.get("token")

        print(f"[AI] Token present: {bool(token)}")

        if not token:
            raise ValueError("Missing authentication token")

        user = await get_current_user(token)
        user_id = str(getattr(user, "id", None) or getattr(user, "_id", None))

        query_string = environ.get("QUERY_STRING", "")
        query_params = parse_qs(query_string)
        interview_id = str(query_params.get("interview_id", [None])[0])

        # dummy for testing scoring
#         dummy_transcript_scores = [
#     {
#         "question_idx": 0,
#         "score": 8.5,
#         "reasoning": "The candidate gave a solid explanation of using FastAPI for asynchronous request handling in a financial analytics app. They clearly justified its selection over Express for performance reasons.",
#         "is_follow_up": False
#     },
#     {
#         "question_idx": 1,
#         "score": 7.0,
#         "reasoning": "Answer covered general differences between SQL and NoSQL well, but lacked a concrete example from their past work.",
#         "is_follow_up": False
#     },
#     {
#         "question_idx": 2,
#         "score": 9.0,
#         "reasoning": "Strong technical depth describing Redis caching implementation with TTL policies and cache invalidation. The performance improvements were quantified.",
#         "is_follow_up": False
#     },
#     {
#         "question_idx": 3,
#         "score": 8.0,
#         "reasoning": "Good walkthrough of Kafka-based event flow and use of consumer groups for reliability, though scaling specifics could have been elaborated further.",
#         "is_follow_up": True
#     },
#     {
#         "question_idx": 4,
#         "score": 7.5,
#         "reasoning": "Demonstrated awareness of API design principles, including versioning and JWT authentication. Could have discussed API documentation practices in more detail.",
#         "is_follow_up": False
#     },
#     {
#         "question_idx": 5,
#         "score": 8.8,
#         "reasoning": "Showed a clear deployment plan leveraging AWS EC2 auto-scaling, load balancing, and NGINX reverse proxy configuration. Thorough understanding of scalability.",
#         "is_follow_up": False
#     },
#     {
#         "question_idx": 6,
#         "score": 9.2,
#         "reasoning": "Excellent diagnostic approach—monitoring Redis metrics, analyzing slow logs, and addressing connection pooling. Clear and practical mitigation strategy.",
#         "is_follow_up": False
#     }
# ]

#         interview = await Interview.get(PydanticObjectId(interview_id))
#         interview.transcript = dummy_transcript_scores
#         await interview.save()
#         sio.start_background_task(generate_score_report_, interview_id)

        if not interview_id:
            raise ValueError("Missing interview_id in query string")

        print(f"[AI] User: {user_id}, Interview: {interview_id}")
        print(f"[AI] Active sessions: {list(active_sessions.keys())}")

        if interview_id not in active_sessions:
            # Reject connection — interview not active
            raise PermissionError(
                f"Interview {interview_id} is not active or authorized")

        # modify session id on reconnect
        # check if conversation already exist, if not create
        if interview_id in conversation_sessions:
            print(f"[AI] Conversation restored for {interview_id}")
        else:
            interview = await Interview.get(PydanticObjectId(interview_id))
            if not interview:
                raise ValueError("Interview not found in database")

            questions = getattr(interview, "questions", []) or []
            if not questions:
                raise ValueError(
                    "Your interview questions are still being prepared. Please try again in a minute.")

            conversation_sessions[interview_id] = {
                "user_id": user_id,
                "interview_id": interview_id,
                "socket_id": sid,
                "history": [],
                "questions": questions,
                "current_question_index": 0
            }

            print(f"[AI] Created new conversation session for {interview_id}")

        active_sessions[interview_id]["ai_socket_id"] = sid
        conversation_sessions[interview_id]["socket_id"] = sid

        # Ask first question if new interview
        if len(conversation_sessions[interview_id]["history"]) == 0:
            prompt = INTERVIEWER_PROMPT(
                "", conversation_sessions[interview_id]["questions"][0]["question"])

            print(f"[AI] Asking first question...")

            ai_text = await stream_ai_response(
                prompt,
                sio=sio,
                sid=sid,
                namespace=AI_NS
            )
            # await sio.emit("ai_streaming_complete", {"done": True}, to=sid, namespace=AI_NS)
            conversation_sessions[interview_id]["history"].append(
                f"AI Interviewer: {ai_text}")

        print(f"[AI] Connected successfully!")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"[AI] Connection refused: {e}")
        # FIX: refuse with a reason. The browser receives it in its
        # "connect_error" event and can show it, instead of a silent disconnect.
        raise ConnectionRefusedError(str(e))


@sio.event(namespace=AI_NS)
async def user_message(sid, data):
    """
    Handles candidate messages, streams AI response, and maintains conversation history.
    """
    try:
        print(f"[AI] Received message from {sid}: {data}")

        # Find session based on socket_id
        session = next(
            (s for s in conversation_sessions.values() if s.get("socket_id") == sid),
            None
        )

        if not session:
            raise ValueError("Session not found or expired")

        interview_id = session["interview_id"]
        history = session["history"]
        questions = session["questions"]
        idx = session["current_question_index"]
        pending_followup = session.get("pending_followup", False)
        followup_depth = session.get("followup_depth", 0)
        # Use current follow-up question if active, else main question
        current_question = session.get("current_followup_question") or (
            questions[idx]["question"] if idx < len(questions) else "N/A"
        )

        history.append(f"Candidate: {data}")

        # Evaluate candidate answer
        eval_prompt = ANSWER_EVALUATION_PROMPT(
            current_question, data, "\n".join(history[-2 * (followup_depth + 1):-2]))
        # print("Evaluation prompt:", eval_prompt)
        eval_response = await evaluator_ai_response(
            eval_prompt,
            sio=sio,
            sid=sid,
            namespace=AI_NS,
        )

        # FIX: evaluator_ai_response now returns a ready dict (or None), so no
        # json.loads here. If Gemini failed we store score=None, which the
        # scorer skips, instead of inventing a fake "5/10".
        evaluation = eval_response or {
            "score": None,
            "reasoning": "This answer could not be evaluated automatically.",
            "follow_up_question": "None",
        }

        score = evaluation.get("score")
        reasoning = evaluation.get("reasoning", "")
        followup_q = evaluation.get("follow_up_question", "None")

        print(
            f"[AI] Evaluation score={score}, reason={reasoning}, follow_up={followup_q}")

        # Store evaluation result
        session.setdefault("scores", []).append({
            "question_idx": idx,
            "score": score,
            "reasoning": reasoning,
            "is_follow_up": pending_followup
        })

        # Check if follow-up is needed
        should_ask_followup = (
            followup_q and
            followup_q.lower() not in ["none", "null", ""] and
            session.get("followup_depth", 0) < MAX_FOLLOWUP_DEPTH
        )

        # If follow-up is needed
        if should_ask_followup:
            followup_depth += 1
            session["followup_depth"] = followup_depth
            session["pending_followup"] = True
            session["current_followup_question"] = followup_q

            print(
                f"[AI] Asking follow-up (depth={followup_depth}): {followup_q}")

            # stream_text_with_tts already sends ai_streaming_complete
            await stream_text_with_tts(followup_q, sio, sid, namespace=AI_NS)

            history.append(f"AI Interviewer: {followup_q}")
            conversation_sessions[interview_id]["history"] = history

            return

        print(
            f"[AI] Follow-up depth limit ({MAX_FOLLOWUP_DEPTH}) reached. Skipping further follow-ups.")

        # Reset follow-up state when moving to next question
        session["followup_depth"] = 0
        session["pending_followup"] = False
        session["current_followup_question"] = None

        print("[AI] Moving to next main question.")

        next_idx = idx + 1
        next_question = questions[next_idx]["question"] if next_idx < len(
            questions) else None

        prompt = INTERVIEWER_PROMPT(
            conversation_history="\n".join(history[-2:]),
            next_question=next_question or "N/A"
        )

        print(f"[AI] Streaming next question...")

        ai_text = await stream_ai_response(
            prompt,
            sio=sio,
            sid=sid,
            namespace=AI_NS
        )

        history.append(f"AI Interviewer: {ai_text}")

        if next_question:
            session["current_question_index"] = next_idx
            conversation_sessions[interview_id]["history"] = history
        else:
            # Interview concluded naturally - all questions answered
            end_msg = "That concludes the interview. Thank you for your time!"
            await sio.emit("ai_partial", end_msg, to=sid, namespace=AI_NS)
            history.append(f"AI Interviewer: {end_msg}")
            conversation_sessions[interview_id]["history"] = history

            print(
                f"[AI] Interview concluded naturally. Calling leave_interview for {interview_id}")
            # Call leave_interview internally to handle cleanup and report generation
            await leave_interview(sid)

    except Exception as e:
        print(f"[AI] Error in user_message: {e}")
        await sio.emit("ai_error", str(e), to=sid, namespace=AI_NS)


@sio.event(namespace=AI_NS)
async def leave_interview(sid, data=None):
    """
    Client leaves an interview room - handles cleanup and report generation.
    Can be called externally by frontend or internally when interview concludes.
    """
    try:
        print(f"[AI] leave_interview called for sid: {sid}")

        # Find session based on socket_id
        session = next(
            (s for s in conversation_sessions.values() if s.get("socket_id") == sid),
            None
        )

        if not session:
            print(f"[AI] No conversation session found for sid: {sid}")
            # Try to find in active_sessions by ai_socket_id
            session = next(
                (s for s in active_sessions.values()
                 if s.get("ai_socket_id") == sid),
                None
            )
            if not session:
                print(
                    f"[AI] Session not found in active_sessions or conversation_sessions")
                return

        interview_id = session["interview_id"]

        print(f"[AI] Processing leave_interview for interview: {interview_id}")

        # Check if conversation session exists (might have been deleted already)
        if interview_id not in conversation_sessions:
            print(
                f"[AI] Conversation session already cleaned up for {interview_id}")
            return

        # --- Save conversation history to database and update status ---
        user_transcript = conversation_sessions[interview_id].get("scores", [])
        interview = await Interview.get(PydanticObjectId(interview_id))

        if not interview:
            print(f"[AI] Interview {interview_id} not found in database")
            return

        interview.transcript = user_transcript
        interview.status = InterviewStatus.completed

        # Get integrity score
        integrity_score = get_integrity_score(PydanticObjectId(interview_id))
        integrity_report = get_detailed_integrity_report(
            PydanticObjectId(interview_id))
        await stop_video_processor(interview_id)

        print("--- Integrity score ---")
        print(integrity_score)
        print("*" * 8)
        print(integrity_report)

        interview.integrity_score = integrity_score
        interview.integrity_report = integrity_report

        await interview.save()

        # Update interview status in active session
        if interview_id in active_sessions:
            active_sessions[interview_id]["status"] = "ended"

        # Clear conversation session
        if interview_id in conversation_sessions:
            del conversation_sessions[interview_id]
            print(f"[AI] Deleted conversation session for {interview_id}")

        # Leave the room
        print(f"[AI] Client {sid} leaving interview room: {interview_id}")
        await sio.leave_room(sid, f"interview_{interview_id}", namespace=AI_NS)

        # Fire a background task to calc score and generate report using data in database
        print(
            f"[AI] Starting background task to generate score report for {interview_id}")
        sio.start_background_task(generate_score_report_, interview_id)

        print(
            f"[AI] Successfully processed leave_interview for {interview_id}")

        # FIX: `await disconnect(sid)` only called our own print-only handler;
        # it never closed the socket. Tell the browser it's over, then close.
        await sio.emit("interview_ended", {"interview_id": interview_id}, to=sid, namespace=AI_NS)
        forget_socket(sid)
        await sio.disconnect(sid, namespace=AI_NS)

    except Exception as e:
        print(f"[AI] Error in leave_interview: {e}")
        import traceback
        traceback.print_exc()


@sio.event(namespace=AI_NS)
async def disconnect(sid):
    """
    Handle client disconnection. Optionally save state before removal.
    """
    print(f"[AI] Client disconnected: {sid}")
