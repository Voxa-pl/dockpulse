import os
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings:
    PROJECT_NAME: str = "DockPulse"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Absolute path to database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR}/ramparandevu.db")
    
    # DocuLog Bridge
    DOCULOG_BASE_URL: str = os.getenv("DOCULOG_BASE_URL", "http://127.0.0.1:8000")
    DOCULOG_SYNC_ENABLED: bool = os.getenv("DOCULOG_SYNC_ENABLED", "true").lower() == "true"
    
    # Quantum Slot Engine (Minutes)
    QUANTUM_MINUTES: int = 15
    DOCKING_BUFFER_MINUTES: int = 10
    PALLET_HANDLING_MINUTES: float = 1.2
    INSPECTION_DEFAULT_MINUTES: int = 5
    INSPECTION_REEFER_MINUTES: int = 15
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:3000",
        "*"
    ]

settings = Settings()
