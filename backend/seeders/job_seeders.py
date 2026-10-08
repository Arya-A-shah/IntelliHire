import asyncio
from datetime import datetime
from beanie import init_beanie
from pymongo import AsyncMongoClient
from models import Job, User
from config import settings


async def seed_jobs():
    # Connect to MongoDB
    client = AsyncMongoClient(settings.MONGODB_URI)
    db = client[settings.MONGO_DB_NAME]

    # Initialize Beanie with models
    await init_beanie(
        database=db,
        document_models=[User, Job]
    )

    # Sample jobs
    sample_jobs = [
        Job(
            title="Frontend Engineer",
            description="Build interactive UIs with React, TypeScript, and TailwindCSS.",
            recruiter_id="68dcf90045328b07fb297103",
            location="Remote",
            type="Full-Time",
            tags=["React", "TypeScript", "UI"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        Job(
            title="ML Engineer",
            description="Work on LLMs, Python pipelines, and MLOps tasks.",
            recruiter_id="68ea18c8bd772e1b8a1dfc91",
            location="San Francisco, CA",
            type="Full-Time",
            tags=["Python", "LLMs", "MLOps"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        Job(
            title="Product Designer",
            description="Design user-friendly interfaces and do UX research.",
            recruiter_id="68dcf90045328b07fb297103",
            location="New York, NY",
            type="Contract",
            tags=["Figma", "Prototyping", "Research"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        Job(
            title="Backend Engineer",
            description="Develop scalable APIs using Node.js and MongoDB.",
            recruiter_id="68ea18c8bd772e1b8a1dfc91",
            location="Remote",
            type="Full-Time",
            tags=["Node.js", "MongoDB", "Express"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        Job(
            title="Data Analyst",
            description="Analyze datasets and provide insights for product growth.",
            recruiter_id="68dcf90045328b07fb297103",
            location="Austin, TX",
            type="Part-Time",
            tags=["SQL", "Python", "Tableau"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        Job(
            title="DevOps Engineer",
            description="Maintain CI/CD pipelines and cloud infrastructure.",
            recruiter_id="68ea18c8bd772e1b8a1dfc91",
            location="Seattle, WA",
            type="Full-Time",
            tags=["AWS", "Docker", "Kubernetes"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
    ]

    # Insert jobs into the database
    for job in sample_jobs:
        await job.insert()

    print("Seeded jobs successfully!")
    await client.close()


if __name__ == "__main__":
    asyncio.run(seed_jobs())
