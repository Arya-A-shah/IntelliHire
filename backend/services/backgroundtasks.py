import asyncio
from email.mime.text import MIMEText
import aiosmtplib
from sentence_transformers import SentenceTransformer, util
from beanie import PydanticObjectId
from models import Application, Job, Interview
from dependencies import extract_text_from_bytes
from config import settings
from .ai_service import generate_interview_questions
from .scoring import calculate_interview_score

SMTP_HOST = settings.SMTP_HOST
SMTP_PORT = settings.SMTP_PORT
SMTP_USER = settings.SMTP_USER
SMTP_PASS = settings.SMTP_PASS
FROM_EMAIL = settings.FROM_EMAIL

# Load model once at module level (singleton pattern)
_model = None


def get_embedding_model():
    """Lazy-load the embedding model."""
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


# Interview ids whose questions are being generated right now.
questions_in_progress = set()


def _embed(text: str) -> list:
    return get_embedding_model().encode(text, convert_to_tensor=False).tolist()


async def compute_resume_embedding_task(
    application_id: str,
    file_bytes: bytes,
    filename: str,
    content_type: str
):
    """
    Compute embedding for a candidate's resume, calculate match score with job, 
    and update the Application document.

    Args:
        application_id: ID of the application to update
        file_bytes: Raw bytes of the resume file
        filename: Original filename
        content_type: MIME type of the file
    """
    try:
        # Get application and related job
        application = await Application.get(PydanticObjectId(application_id))
        if not application:
            print(f"❌ Application {application_id} not found")
            return

        job = await Job.get(PydanticObjectId(application.job_id))
        if not job:
            print(
                f"❌ Job {application.job_id} not found for application {application_id}")
            return

        # Extract text from resume
        text = await extract_text_from_bytes(file_bytes, filename, content_type)

        if not text.strip():
            print(
                f"⚠️ Resume for application {application_id} contains no readable text")
            return
        
        # Store text in application document to use in question generation
        application.resume_text = text

        # Generate resume embedding
        # FIX: encode() is heavy CPU work; run it off the event loop.
        resume_embedding = await asyncio.to_thread(_embed, text)

        # Calculate match score
        match_score = None
        if job.job_description_embedding:
            # Calculate cosine similarity
            match_score = util.cos_sim(
                resume_embedding,
                job.job_description_embedding
            )
            # Convert to percentage (0-100)
            match_score = float(match_score.item() if hasattr(
                match_score, "item") else match_score)
            match_score = round(match_score * 100, 2)
        else:
            print(f"⚠️ Job {job.id} has no job_description_embedding")

        # Update Application document with both embedding and score
        application.resume_embedding = resume_embedding
        application.match_score = match_score
        await application.save()

        score_text = f"with score {match_score}%" if match_score is not None else "without score (job embedding missing)"
        print(
            f"✅ Successfully generated embedding for application {application_id} {score_text}")

    except Exception as e:
        print(
            f"❌ Failed to generate embedding for application {application_id}: {e}")
        # Optionally: Update application status to indicate embedding failure
        try:
            application = await Application.get(PydanticObjectId(application_id))
            if application:
                application.embedding_error = str(e)
                await application.save()
        except:
            pass


async def compute_job_description_embedding_task(job_id: str, job_description: str):
    """
    Compute embedding for a job description and update the Job document.

    Args:
        job_id: ID of the job to update
        job_description: Text of the job description
    """
    try:
        job = await Job.get(PydanticObjectId(job_id))
        if not job:
            print(f"❌ Job {job_id} not found")
            return
        
        if not job_description.strip():
            print(f"⚠️ Job description for job {job_id} is empty")
            return

        # Generate job description embedding
        jd_embedding = await asyncio.to_thread(_embed, job_description)

        # Update Job document
        job.job_description_embedding = jd_embedding
        await job.save()

        print(f"✅ Successfully generated embedding for job {job_id}")

    except Exception as e:
        print(f"❌ Failed to generate embedding for job {job_id}: {e}")


async def send_email(to_email: str, subject: str, body: str):
    msg = MIMEText(body, "plain")
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject

    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            start_tls=True,
            username=SMTP_USER,
            password=SMTP_PASS,
        )
        print(f"📧 Email sent successfully to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")


async def generate_and_save_questions_task(interview_id: PydanticObjectId, job_description: str, resume_text: str):
    """
    FIX: one Gemini hiccup used to leave the interview with no questions, and the
    candidate's interview then refused to start. Now we retry 3 times with a
    growing wait (2s, 4s) before giving up.
    """
    key = str(interview_id)
    if key in questions_in_progress:
        return  # already being generated; don't call Gemini twice
    questions_in_progress.add(key)
    try:
        questions = None
        attempts = 5
        for attempt in range(1, attempts + 1):
            try:
                questions = await generate_interview_questions(job_description, resume_text)
                break
            except Exception as e:
                print(f"Question generation attempt {attempt}/{attempts} failed: {e}")
                if attempt < attempts:
                    await asyncio.sleep(2 ** attempt)  # 2, 4, 8, 16 s (exponential backoff)

        if not questions:
            print(f"Giving up on questions for interview {interview_id} "
                  f"(they will be retried when the candidate opens the link)")
            return
    finally:
        questions_in_progress.discard(key)

    interview = await Interview.get(PydanticObjectId(interview_id))
    if interview:
        interview.questions = questions
        await interview.save()
        print(f"Questions generated for interview: {interview_id}")
    else:
        print(f"Interview: {interview_id} not found")



# Assuming calculate_interview_score is defined and imported elsewhere
# from .scoring_module import calculate_interview_score 

async def generate_score_report_(interview_id: str):
    """
    Calculates the interview score and generates the report, relying on the 
    calculate_interview_score function.
    """
    try:
        print(f"Starting score calculation and report generation for Interview ID: {interview_id}")
        
        # Call the existing calculation function and wait for the result
        result = await calculate_interview_score(interview_id)
        
        # Check if the result contains an error
        if "error" in result:
            print(f"❌ Failed to calculate score for {interview_id}: {result['error']}")
            return {"status": "failed", "message": result["error"]}
        
        print(f"✅ Successfully calculated score and generated report for {interview_id}.")
        return {"status": "success", "overall_score": result.get("overall_score")}

    except Exception as e:
        # Catch any unexpected errors during the process
        print(f"🚨 Critical error in generate_score_report_ for {interview_id}: {e}")
        return {"status": "error", "message": "An unhandled critical error occurred."}