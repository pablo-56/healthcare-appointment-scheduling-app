# apps/api/app/tasks/analytics.py
import random
from celery import shared_task
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from app.db import engine  # your db.py exposes "engine" for SessionLocal/engine
from app.models import Experiment, ExperimentAssignment

SessionLocal = sessionmaker(bind=engine)

@shared_task(name="analytics.assign_variant")
def assign_variant(experiment_id: int, subject_id: int):
    """Deterministic or random variant assignment, then write an assignment row."""
    session = SessionLocal()
    try:
        exp = session.get(Experiment, experiment_id)
        if not exp or not exp.variants or exp.status != "open":
            return {"ok": False, "reason": "experiment not open or missing"}

        keys = sorted(list(exp.variants.keys()))
        if not keys:
            return {"ok": False, "reason": "no variants"}

        # Simple hash-based bucketing for stability:
        bucket = abs(hash((experiment_id, subject_id))) % len(keys)
        chosen = keys[bucket]

        assignment = ExperimentAssignment(
            experiment_id=experiment_id,
            subject_id=subject_id,
            channel=exp.variants[chosen].get("channel"),
            variant=chosen,
            meta={"decider": "hash"},
        )
        session.add(assignment)
        session.commit()
        return {"ok": True, "variant": chosen, "assignment_id": assignment.id}
    finally:
        session.close()

@shared_task(name="analytics.nightly_rollups")
def nightly_rollups():
    """Placeholder: run nightly aggregations for dashboards if needed."""
    # If you add materialized views later, refresh them here.
    return {"ok": True}
