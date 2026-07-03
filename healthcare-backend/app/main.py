from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import auth as auth_router
from app.routers import doctor as doctor_router
from app.routers import patient as patient_router
from app.routers import appointment as appointment_router

# Create tables on startup. Swap for Alembic migrations in production.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="Registration, login, JWT + refresh tokens, forgot/reset password, and role-based access control.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(doctor_router.router)
app.include_router(patient_router.router)
app.include_router(appointment_router.router)


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "module": "authentication", "env": settings.ENV}
