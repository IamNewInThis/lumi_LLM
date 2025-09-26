import os
import httpx
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from ..models.chat import ChatRequest
from ..auth import get_current_user
from ..rag.utils import get_rag_context
from ..rag.retriever import supabase
from ..utils.date_utils import calcular_edad, calcular_meses
from ..utils.knowledge_detector import KnowledgeDetector
from ..services.knowledge_service import BabyKnowledgeService
from ..utils.knowledge_cache import confirmation_cache

router = APIRouter()
today = datetime.now().strftime("%d/%m/%Y %H:%M")

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

async def get_user_profiles_and_babies(user_id, supabase_client):
    profiles = supabase_client.table("profiles").select("*").eq("id", user_id).execute()
    babies = supabase_client.table("babies").select("*").eq("user_id", user_id).execute()

    # Obtener conocimiento específico de todos los bebés
    knowledge_by_baby = await BabyKnowledgeService.get_all_user_knowledge(user_id)
    knowledge_context = BabyKnowledgeService.format_knowledge_for_context(knowledge_by_baby)

    profile_texts = [
        f"- Perfil: {p['name']}, fecha de nacimiento {p['birthdate']}, alimentación: {p.get('feeding', 'N/A')}"
        for p in profiles.data
    ] if profiles.data else []

    baby_texts = []
    routines_context = ""
    if babies.data:
        for b in babies.data:
            edad_anios = calcular_edad(b["birthdate"])
            edad_meses = calcular_meses(b["birthdate"])
            rutina = b.get("routines")

            baby_texts.append(
                f"- Bebé: {b['name']}, fecha de nacimiento {b['birthdate']}, "
                f"edad: {edad_anios} años ({edad_meses} meses aprox.), "
                f"alimentación: {b.get('feeding', 'N/A')}"
                f"peso: {b.get('weight', 'N/A')} kg, "
                f"altura: {b.get('height', 'N/A')} cm"
            ) 

            # Si no hay rutina, sugerir crear una pidiendo detalles
            if not rutina:
                routines_context += (
                    f"⚠️ El bebé {b['name']} no tiene rutina registrada. "
                    "Si el usuario pide crear una rutina, primero pregúntale qué actividades y horarios quiere incluir. "
                    "Luego organiza la rutina en formato tabla con columnas: Hora | Actividad | Detalles.\n\n"
                )
            else:
                routines_context += (
                    f"✅ El bebé {b['name']} ya tiene una rutina registrada. "
                    "Si el usuario pide modificarla o revisarla, muéstrala en formato tabla y sugiere mejoras.\n\n"
                )

    context = ""
    if profile_texts:
        context += "Perfiles:\n" + "\n".join(profile_texts) + "\n\n"
    if baby_texts:
        context += "Bebés:\n" + "\n".join(baby_texts) + "\n\n"
    
    # Agregar conocimiento específico si existe
    if knowledge_context:
        context += knowledge_context + "\n\n"

    return context.strip(), routines_context.strip()

async def get_conversation_history(user_id, supabase_client, limit_per_role=5):
    """
    Recupera los últimos mensajes del usuario y del asistente para mantener contexto en la conversación.
    """
    user_msgs = supabase_client.table("conversations") \
        .select("*") \
        .eq("user_id", user_id) \
        .eq("role", "user") \
        .order("created_at", desc=True) \
        .limit(limit_per_role) \
        .execute()

    assistant_msgs = supabase_client.table("conversations") \
        .select("*") \
        .eq("user_id", user_id) \
        .eq("role", "assistant") \
        .order("created_at", desc=True) \
        .limit(limit_per_role) \
        .execute()

    # Combinar y ordenar cronológicamente
    history = (user_msgs.data or []) + (assistant_msgs.data or [])
    history_sorted = sorted(history, key=lambda x: x["created_at"])

    # Convertir al formato que espera OpenAI
    formatted_history = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in history_sorted
    ]

    return formatted_history

@router.post("/api/chat")
async def chat_openai(payload: ChatRequest, user=Depends(get_current_user)):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message required")

    user_id = user["id"]
    
    # 🔥 NUEVO: Verificar primero si es una respuesta de confirmación
    confirmation_response = confirmation_cache.is_confirmation_response(payload.message)
    if confirmation_response is not None and confirmation_cache.has_pending_confirmation(user_id):
        print(f"🎯 Detectada respuesta de confirmación: {confirmation_response}")
        
        pending_data = confirmation_cache.get_pending_confirmation(user_id)
        if pending_data:
            if confirmation_response:  # Usuario confirmó
                try:
                    saved_items = []
                    
                    for knowledge_item in pending_data["knowledge"]:
                        # Buscar el baby_id basado en el nombre
                        baby_id = await BabyKnowledgeService.find_baby_by_name(
                            user_id, 
                            knowledge_item.get("baby_name", "")
                        )
                        
                        if baby_id:
                            # Preparar datos para guardar
                            knowledge_data = {
                                "category": knowledge_item["category"],
                                "subcategory": knowledge_item.get("subcategory"),
                                "title": knowledge_item["title"],
                                "description": knowledge_item["description"],
                                "importance_level": knowledge_item.get("importance_level", 1)
                            }
                            
                            # Guardar en la base de datos
                            saved_item = await BabyKnowledgeService.save_knowledge(
                                user_id, 
                                baby_id, 
                                knowledge_data
                            )
                            saved_items.append(saved_item)
                    
                    confirmation_cache.clear_pending_confirmation(user_id)
                    
                    response_text = f"✅ ¡Perfecto! He guardado {len(saved_items)} elemento(s) en el perfil. Ahora podré darte respuestas más personalizadas considerando esta información."
                    
                    return {"answer": response_text, "usage": {}}
                    
                except Exception as e:
                    print(f"Error guardando conocimiento confirmado: {e}")
                    confirmation_cache.clear_pending_confirmation(user_id)
                    return {"answer": "❌ Hubo un error guardando la información. Por favor intenta de nuevo.", "usage": {}}
                    
            else:  # Usuario rechazó
                confirmation_cache.clear_pending_confirmation(user_id)
                return {"answer": "👌 Entendido, no guardaré esa información.", "usage": {}}

    # Contexto RAG, perfiles/bebés e historial de conversación
    rag_context = await get_rag_context(payload.message)
    user_context, routines_context = await get_user_profiles_and_babies(user["id"], supabase)
    history = await get_conversation_history(user["id"], supabase)  # 👈 historial del backend


    print(f"📚 Contexto RAG recuperado:\n{rag_context[:500]}...\n")
    
    # Prompt de sistema
    system_prompt = (
        "Eres un acompañante cercano para madres y padres. Tu nombre es Lumi. "
        "Responde de forma cálida, breve y coloquial, usando ejemplos simples y naturales. "
        "Si hay información en el contexto de documentos, úsala de manera explícita en tu respuesta. "
        "Nunca inventes información fuera de los documentos, solo completa con empatía si el contexto no tiene la respuesta. "
        "No empieces siempre tus respuestas con 'Hola' o saludos, salvo que el usuario te salude primero. "
        "Si el usuario solo saluda, responde también con un saludo corto y amistoso, sin consejos extra. "
        "Evita sonar académico o demasiado formal. "
        f"La fecha de hoy es {today}. Si el usuario pregunta por la fecha actual, responde con esta. "
        "Cuando alguien te hace una consulta sobre crianza, empieza por considerar la edad exacta del niño o niña, "
        "ya que esto define qué comportamientos son esperables y cómo acompañarlos. "
        "Explica brevemente por qué ocurre lo que pasa, desde el desarrollo emocional, neurológico o conductual, "
        "para que el adulto entienda el trasfondo y no solo el síntoma. "
        "Si faltan datos importantes, pídelos antes de avanzar. "
        "A partir de ahí, propone estrategias concretas y realistas, siempre desde una mirada respetuosa "
        "que prioriza el vínculo y la seguridad emocional. "
        "Cuando corresponda, incluye ejemplos de frases que ayuden a poner en palabras lo que ocurre. "
        "Termina tus respuestas con una pregunta abierta que permita seguir ajustando la guía a la situación real. "
        "La idea no es dar fórmulas mágicas, sino acompañar a construir respuestas que tengan sentido y funcionen en la familia."
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
            {"role": "system", "content": f"Contexto de rutinas:\n{routines_context}"},
            {"role": "system", "content": f"Usa estrictamente la siguiente información del libro si es relevante:\n\n{rag_context}"},
            *history,  
            {"role": "user", "content": payload.message},
        ],
        "max_tokens": 1000,
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

    # NUEVA FUNCIONALIDAD: Detectar conocimiento importante en el mensaje del usuario
    try:
        print(f"🔍 Analizando mensaje para conocimiento: {payload.message}")
        
        # Obtener información de bebés para el contexto
        babies = supabase.table("babies").select("*").eq("user_id", user_id).execute()
        babies_context = babies.data or []
        print(f"👶 Bebés encontrados: {len(babies_context)}")
        
        # Analizar el mensaje para detectar información importante
        detected_knowledge = await KnowledgeDetector.analyze_message(
            payload.message, 
            babies_context
        )
        print(f"🧠 Conocimiento detectado: {detected_knowledge}")
        
        # Si se detecta conocimiento importante, guardar en caché y preguntar
        if detected_knowledge and KnowledgeDetector.should_ask_confirmation(detected_knowledge):
            print("✅ Se debe preguntar confirmación")
            
            # Guardar en caché para confirmación posterior
            confirmation_cache.set_pending_confirmation(user_id, detected_knowledge, payload.message)
            
            confirmation_message = KnowledgeDetector.format_confirmation_message(detected_knowledge)
            
            # Agregar la pregunta de confirmación a la respuesta
            assistant_with_confirmation = f"{assistant}\n\n💡 {confirmation_message}"
            
            return {
                "answer": assistant_with_confirmation, 
                "usage": usage
            }
        else:
            print("❌ No se debe preguntar confirmación")
        
    except Exception as e:
        print(f"Error en detección de conocimiento: {e}")
        import traceback
        traceback.print_exc()
        # Continuar normalmente si falla la detección
        pass

    return {"answer": assistant, "usage": usage}

@router.get("/api/test-knowledge")
async def test_knowledge():
    """
    Endpoint de prueba para verificar que el sistema funciona
    """
    return {
        "message": "Sistema de conocimiento funcionando",
        "detector_available": "KnowledgeDetector" in globals(),
        "service_available": "BabyKnowledgeService" in globals()
    }

@router.get("/api/test-cache/{user_id}")
async def test_cache(user_id: str):
    """
    Endpoint de prueba para ver el estado del caché
    """
    pending = confirmation_cache.get_pending_confirmation(user_id)
    return {
        "has_pending": confirmation_cache.has_pending_confirmation(user_id),
        "pending_data": pending
    }

@router.post("/api/test-detect")
async def test_detect(payload: ChatRequest, user=Depends(get_current_user)):
    """
    Endpoint de prueba para probar solo la detección de conocimiento
    """
    try:
        # Obtener información de bebés para el contexto
        babies = supabase.table("babies").select("*").eq("user_id", user["id"]).execute()
        babies_context = babies.data or []
        
        # Analizar el mensaje para detectar información importante
        detected_knowledge = await KnowledgeDetector.analyze_message(
            payload.message, 
            babies_context
        )
        
        return {
            "message": payload.message,
            "babies_found": len(babies_context),
            "babies_names": [b.get('name', '') for b in babies_context],
            "detected_knowledge": detected_knowledge,
            "should_confirm": KnowledgeDetector.should_ask_confirmation(detected_knowledge)
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "traceback": traceback.format_exc()}