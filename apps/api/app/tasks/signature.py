from app.celery_app import celery_app


@celery_app.task(name="signature.process_signature")
def process_signature(consent_id: int):
    # TODO: verify signature webhook payload, update DB
    return {"status": "ok", "consent_id": consent_id}
