import statistics
from collections import defaultdict
from typing import Any, DefaultDict, Dict, List

from beanie import PydanticObjectId

from models import Interview
from core.prompts import REPORT_PROMPT
from .ai_service import reporter_ai_response


def performance_band(score_out_of_100: float) -> str:
    if score_out_of_100 >= 80:
        return "excellent"
    if score_out_of_100 >= 60:
        return "good"
    if score_out_of_100 >= 40:
        return "average"
    return "poor"


def compute_result(questions: List[Dict[str, Any]], transcript: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Pure scoring function (no database), so it is easy to unit test.

    1. Group every scored answer by its main question (follow-ups share the index).
    2. Average the 0-10 scores inside each group.
    3. Weighted average across the questions that were actually answered.
    4. Scale to 0-100.
    """
    if not questions:
        raise ValueError("No questions found for this interview")
    if not transcript:
        raise ValueError("The candidate did not answer any question")

    grouped: DefaultDict[int, List[Dict[str, Any]]] = defaultdict(list)
    for entry in transcript:
        idx = entry.get("question_idx")
        if idx is not None and 0 <= idx < len(questions):
            grouped[idx].append(entry)

    default_weight = 1.0 / len(questions)
    weighted_sum = 0.0
    total_weight = 0.0
    details = []

    for idx in sorted(grouped):
        entries = grouped[idx]
        q = questions[idx]
        scores = [e["score"] for e in entries if e.get("score") is not None]
        if not scores:
            continue

        weight = float(q.get("weight") or default_weight)
        avg = statistics.mean(scores)
        weighted_sum += avg * weight
        total_weight += weight

        details.append({
            "question": q.get("question"),
            "category": q.get("category"),
            "difficulty": q.get("difficulty"),
            "weight": round(weight, 3),
            # FIX: the old code stored score*weight here (e.g. 1.6), which looked
            # like a terrible score. Store the real 0-10 average instead.
            "score": round(avg, 2),
            "num_followups": len(entries) - 1,
            "reasonings": [e.get("reasoning") for e in entries if e.get("reasoning")],
        })

    if total_weight <= 0:
        raise ValueError("No scored answers to calculate from")

    overall = round(weighted_sum / total_weight * 10, 1)  # 0-100

    return {
        "overall_score": overall,
        # FIX: the band used to be picked from the un-normalised sum, so a
        # candidate who left early got a worse band than their real score.
        "performance": performance_band(overall),
        "questions_answered": len(details),
        "questions_total": len(questions),
        "details": details,
    }


async def calculate_interview_score(interview_id: str):
    """Score the interview, save it, then ask Gemini for the recruiter report."""
    interview = await Interview.get(PydanticObjectId(interview_id))
    if not interview:
        return {"interview_id": interview_id, "error": "Interview not found"}

    try:
        result = compute_result(interview.questions or [], interview.transcript or [])
    except ValueError as ve:
        # FIX: errors used to be printed and lost, so the recruiter saw
        # "loading" forever. Now the reason is saved on the interview.
        interview.result = {"error": str(ve)}
        await interview.save()
        return {"interview_id": interview_id, "error": str(ve)}

    result["interview_id"] = interview_id
    interview.result = result
    await interview.save()

    report = await reporter_ai_response(REPORT_PROMPT(result))
    if report:
        interview.report = report
    else:
        interview.result = {**result, "report_error": "Gemini could not write the report"}
    await interview.save()

    return result
