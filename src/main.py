# src/main.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root directory first, before any other imports
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import chat

app = FastAPI(title="Lumi LLM API", version="1.1.0")

@app.get("/api")
async def root():
    return {"message": "Lumi LLM API is running in version: 1.1.0."}

print(f"Usando lumi versión 1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar rutas
app.include_router(chat.router)
