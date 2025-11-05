# src/main.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root directory first, before any other imports
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Now import other modules
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import chat

app = FastAPI(title="Sol Local Chat Proxy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en producción cambia esto
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Lumi LLM API is running in version: 1.2.2."}

print(f"Usando lumi_bot versión 1.2.2")
# Montar rutas
app.include_router(chat.router)

