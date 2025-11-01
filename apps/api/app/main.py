from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from .otel import setup_tracer
#from .middleware.purpose_of_use import PurposeOfUseMiddleware
from .routers import health, auth, sessions, agents, appointments, intake, documents, signature, admin, checkin, ops, prechart, pros, tasks, compliance, analytics
from .routers import scribe as scribe_router
from .routers import billing as billing_router


setup_tracer()

app = FastAPI(title="Healthcare API", version="0.1.0")
#app.add_middleware(PurposeOfUseMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(agents.router)
app.include_router(appointments.router)
app.include_router(intake.router)
app.include_router(documents.router)
app.include_router(signature.router)
app.include_router(admin.router)
app.include_router(checkin.router)  
app.include_router(ops.router)    
app.include_router(prechart.router)  
app.include_router(scribe_router.router)
app.include_router(billing_router.router)
app.include_router(pros.router)
app.include_router(tasks.router)
app.include_router(compliance.router)
app.include_router(analytics.router)

Instrumentator().instrument(app).expose(app)
