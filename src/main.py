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
from src.knowledge_base import initialize_knowledge_service

app = FastAPI(title="Lumi LLM API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar el sistema de base de conocimiento estructurada
@app.on_event("startup")
async def startup_event():
    knowledge_base_path = Path(__file__).parent / "knowledge_base"
    style_manifest_path = Path(__file__).parent / "prompts" / "style_manifest.md"
    
    initialize_knowledge_service(
        str(knowledge_base_path), 
        str(style_manifest_path)
    )

# Montar rutas
app.include_router(chat.router)

