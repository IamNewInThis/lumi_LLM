import os
import httpx
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from ..models.chat import ChatRequest
from ..auth import get_current_user
from ..rag.utils import get_rag_context
from ..rag.retriever import supabase
from ..utils.date_utils import calcular_edad, calcular_meses

router = APIRouter()
today = datetime.now().strftime("%d/%m/%Y")

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

if not OPENAI_KEY:
    raise RuntimeError("Falta OPENAI_API_KEY en variables de entorno (.env)")


async def get_user_profiles_and_babies(user_id, supabase_client):
    profiles = supabase_client.table("profiles").select("*").eq("id", user_id).execute()
    babies = supabase_client.table("babies").select("*").eq("user_id", user_id).execute()

    profile_texts = [
        f"- Perfil: {p['name']}, fecha de nacimiento {p['birthdate']}, alimentación: {p.get('feeding', 'N/A')}"
        for p in profiles.data
    ] if profiles.data else []

    baby_texts = []
    if babies.data:
        for b in babies.data:
            edad_anios = calcular_edad(b["birthdate"])
            edad_meses = calcular_meses(b["birthdate"])
            baby_texts.append(
                f"- Bebé: {b['name']}, fecha de nacimiento {b['birthdate']}, "
                f"edad: {edad_anios} años ({edad_meses} meses aprox.), "
                f"alimentación: {b.get('feeding', 'N/A')}"
                f"peso: {b.get('weight', 'N/A')} kg, "
                f"altura: {b.get('height', 'N/A')} cm"
            ) 

    context = ""
    if profile_texts:
        context += "Perfiles:\n" + "\n".join(profile_texts) + "\n\n"
    if baby_texts:
        context += "Bebés:\n" + "\n".join(baby_texts)

    return context.strip()


@router.post("/api/chat")
async def chat_openai(payload: ChatRequest, user=Depends(get_current_user)):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message required")

    # Contexto RAG y perfiles/bebés
    rag_context = await get_rag_context(payload.message)
    user_context = await get_user_profiles_and_babies(user["id"], supabase)

    # Prompt de sistema
    system_prompt = (
        "Eres un acompañante cercano para madres y padres. "
        "Responde de forma cálida, breve y coloquial, usando ejemplos simples y naturales. "
        "Si hay información en el contexto de documentos, úsala de manera explícita en tu respuesta. "
        "Nunca inventes información fuera de los documentos, solo completa con empatía si el contexto no tiene la respuesta. "
        "No empieces siempre tus respuestas con 'Hola' o saludos, salvo que el usuario te salude primero. "
        "Si el usuario solo saluda, responde también con un saludo corto y amistoso, sin consejos extra. "
        "Evita sonar académico o demasiado formal. "
        f"La fecha de hoy es {today}. Si el usuario pregunta por la fecha actual, responde con esta."
    )

    # Formatear el perfil que viene en el payload
    profile_text = ""
    if payload.profile:
        profile_data = payload.profile
        profile_text = (
            "Perfil actual:\n"
            f"- Fecha de nacimiento: {profile_data.get('dob')}\n"
            f"- Alimentación: {profile_data.get('feeding')}\n"
        )

    # Construcción del body con separación clara de roles
    body = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": f"Contexto de usuario:\n{user_context}"},
            {"role": "system", "content": f"Contexto del perfil enviado:\n{profile_text}"},
            {"role": "system", "content": f"Usa estrictamente la siguiente información del libro si es relevante:\n\n{rag_context}"},
            {"role": "user", "content": payload.message},
        ],
        "max_tokens": 500,
        "temperature": 0.3,
    }

    headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)

    if resp.status_code >= 300:
        raise HTTPException(status_code=502, detail={"openai_error": resp.text})

    data = resp.json()
    assistant = data.get("choices", [])[0].get("message", {}).get("content", "")
    usage = data.get("usage", {})

    return {"answer": assistant, "usage": usage}
