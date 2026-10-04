from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import crops, assistant, profile, auth, weather, schemes
from api.google_auth import router as google_auth_router
from config.database import Base, engine
import os

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AgroNex API", description="Smart Farming Backend", version="1.0.0")

# Determine allowed origins based on environment variable
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
origins = [frontend_url]
if os.getenv("ALLOW_ALL_ORIGINS") == "true":
    origins = ["*"]

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(google_auth_router)
app.include_router(crops.router, prefix="/api/crops", tags=["Crops"])
app.include_router(assistant.router, prefix="/api/assistant", tags=["AI Assistant"])
app.include_router(weather.router, prefix="/api/weather", tags=["Weather"])
app.include_router(schemes.router, prefix="/api/schemes", tags=["Schemes"])
app.include_router(profile.router, prefix="/api/profile", tags=["Profile"])

@app.get("/")
def read_root():
    return {"message": "Welcome to AgroNex API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
