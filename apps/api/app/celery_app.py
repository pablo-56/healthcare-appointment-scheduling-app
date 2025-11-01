
########################## ###########################"""

# apps/api/app/celery_app.py
import os
from celery import Celery

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

celery_app = Celery(
    "app",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=[
        "app.tasks.compliance",  # Phase 10 tasks
        "app.tasks.chartprep",
        "app.tasks.claims",
        "app.tasks.events",
        "app.tasks.intake",
        "app.tasks.scribe",
        "app.tasks.signature",
        "app.tasks.eligibility", 
        "app.tasks.analytics",        # keep other task modules here if you have them
    ],
)

celery_app.conf.update(
    task_default_queue=os.getenv("CELERY_DEFAULT_QUEUE", "default"),
    task_routes={
        "compliance.*": {"queue": "compliance"},
    },
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Dev convenience: run tasks inline when set
    task_always_eager=os.getenv("CELERY_TASK_ALWAYS_EAGER", "0") == "1",
    task_eager_propagates=True,
)



######################### Celery Configuration #########################

