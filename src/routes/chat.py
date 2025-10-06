# src/routes/chat.py
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from pathlib import Path
from ..models.chat import ChatRequest, KnowledgeConfirmRequest
from ..auth import get_current_user
from src.rag.utils import get_rag_context
from src.utils.date_utils import calcular_edad, calcular_meses
from ..rag.retriever import supabase
from ..utils.knowledge_detector import KnowledgeDetector
from ..services.knowledge_service import BabyKnowledgeService
from ..utils.knowledge_cache import confirmation_cache
from ..utils.routine_detector import RoutineDetector
from ..services.routine_service import RoutineService
from ..utils.routine_cache import routine_confirmation_cache

router = APIRouter()
today = datetime.now().strftime("%d/%m/%Y %H:%M")

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

if not OPENAI_KEY:
    raise RuntimeError("Falta OPENAI_API_KEY en variables de entorno (.env)")

def load_system_prompt():
    """Carga el prompt base desde archivo template."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "system_prompt_base.md"
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise RuntimeError(f"No se encontró el archivo de prompt en: {prompt_path}")

def format_llm_output(text):
    """Limpia y formatea la salida del LLM para que sea más natural y legible."""
    # Limpiar exceso de símbolos de markdown
    text = text.replace("###", "##")
    text = text.replace("****", "**")
    
    # Remover líneas vacías excesivas
    import re
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    
    # Limpiar espacios al inicio y final
    text = text.strip()
    
    return text

async def get_user_profiles_and_babies(user_id, supabase_client):
    profiles = supabase_client.table("profiles").select("*").eq("id", user_id).execute()
    babies = supabase_client.table("babies").select("*").eq("user_id", user_id).execute()

    # Obtener conocimiento específico de todos los bebés
    knowledge_by_baby = await BabyKnowledgeService.get_all_user_knowledge(user_id)
    knowledge_context = BabyKnowledgeService.format_knowledge_for_context(knowledge_by_baby)
    
    # Obtener rutinas de todos los bebés
    routines_by_baby = await RoutineService.get_all_user_routines(user_id)
    routines_context = RoutineService.format_routines_for_context(routines_by_baby)

    profile_texts = [
        f"- Perfil: {p['name']}, fecha de nacimiento {p['birthdate']}, alimentación: {p.get('feeding', 'N/A')}"
        for p in profiles.data
    ] if profiles.data else []

    baby_texts = []
    if babies.data:
        for b in babies.data:
            edad_anios = calcular_edad(b["birthdate"])
            edad_meses = calcular_meses(b["birthdate"])

            # Determinar etapa de desarrollo
            etapa_desarrollo = ""
            if edad_meses <= 6:
                etapa_desarrollo = "lactante"
            elif edad_meses <= 12:
                etapa_desarrollo = "bebé"
            elif edad_meses <= 24:
                etapa_desarrollo = "caminador/toddler"
            elif edad_anios <= 5:
                etapa_desarrollo = "preescolar"
            elif edad_anios <= 12:
                etapa_desarrollo = "escolar"
            else:
                etapa_desarrollo = "adolescente"

            baby_texts.append(
                f"- Bebé: {b['name']}, fecha de nacimiento {b['birthdate']}, "
                f"edad: {edad_anios} años ({edad_meses} meses aprox.), "
                f"etapa de desarrollo: {etapa_desarrollo}, "
                f"alimentación: {b.get('feeding', 'N/A')}, "
                f"peso: {b.get('weight', 'N/A')} kg, "
                f"altura: {b.get('height', 'N/A')} cm"
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

async def get_conversation_history(user_id, supabase_client, limit_per_role=7):
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
    
    # Verificar si es una respuesta de confirmación de preferencias (KNOWLEDGE)
    confirmation_response = confirmation_cache.is_confirmation_response(payload.message)
    if confirmation_response is not None and confirmation_cache.has_pending_confirmation(user_id):
        print(f"🎯 Detectada respuesta de confirmación de conocimiento: {confirmation_response}")
        
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

    # Verificar si es una respuesta de confirmación de RUTINA
    routine_confirmation_response = routine_confirmation_cache.is_confirmation_response(payload.message)
    if routine_confirmation_response is not None and routine_confirmation_cache.has_pending_confirmation(user_id):
        print(f"🎯 Detectada respuesta de confirmación de rutina: {routine_confirmation_response}")
        
        pending_routine_data = routine_confirmation_cache.get_pending_confirmation(user_id)
        if pending_routine_data:
            if routine_confirmation_response:  # Usuario confirmó la rutina
                try:
                    routine_data = pending_routine_data["routine"]
                    
                    # Buscar el baby_id basado en el nombre
                    baby_id = await RoutineService.find_baby_by_name(
                        user_id, 
                        routine_data.get("baby_name", "")
                    )
                    
                    if baby_id:
                        # 1. GUARDAR LA RUTINA en tablas específicas
                        saved_routine = await RoutineService.save_routine(
                            user_id, 
                            baby_id, 
                            routine_data
                        )
                        
                        # 2. TAMBIÉN GUARDAR COMO CONOCIMIENTO GENERAL
                        try:
                            routine_name = routine_data.get("routine_name", "Rutina")
                            routine_summary = routine_data.get("context_summary", "Rutina establecida")
                            
                            # Crear entrada de conocimiento basada en la rutina
                            knowledge_data = {
                                "category": "rutinas",
                                "subcategory": "estructura diaria",
                                "title": routine_name,
                                "description": routine_summary,
                                "importance_level": 3
                            }
                            
                            # Guardar también en baby_knowledge
                            await BabyKnowledgeService.save_knowledge(
                                user_id, 
                                baby_id, 
                                knowledge_data
                            )
                            
                            print(f"✅ Rutina guardada en AMBOS sistemas: rutinas + conocimiento")
                            
                        except Exception as knowledge_error:
                            print(f"⚠️ Error guardando conocimiento de rutina: {knowledge_error}")
                            # No fallar si el conocimiento falla, la rutina ya se guardó
                        
                        routine_confirmation_cache.clear_pending_confirmation(user_id)
                        
                        activities_count = saved_routine.get("activities_count", 0)
                        
                        response_text = f"✅ ¡Excelente! He guardado la rutina **{routine_name}** con {activities_count} actividades en el sistema de rutinas y también como conocimiento general. Ahora podré ayudarte mejor con horarios y sugerencias personalizadas."
                        
                        return {"answer": response_text, "usage": {}}
                    else:
                        routine_confirmation_cache.clear_pending_confirmation(user_id)
                        return {"answer": "❌ No pude encontrar el bebé mencionado. Por favor intenta de nuevo.", "usage": {}}
                        
                except Exception as e:
                    print(f"Error guardando rutina confirmada: {e}")
                    routine_confirmation_cache.clear_pending_confirmation(user_id)
                    return {"answer": "❌ Hubo un error guardando la rutina. Por favor intenta de nuevo.", "usage": {}}
                    
            else:  # Usuario rechazó la rutina
                routine_confirmation_cache.clear_pending_confirmation(user_id)
                return {"answer": "👌 Entendido, no guardaré esa rutina.", "usage": {}}

    # Contexto RAG, perfiles/bebés e historial de conversación
    rag_context = await get_rag_context(payload.message)
    
    # Búsqueda RAG especializada para temas específicos
    specialized_rag = ""
    message_lower = payload.message.lower()
    
    # Detectar consultas de desmame nocturno y agregar contexto especializado
    if any(keyword in message_lower for keyword in [
        "tomas nocturnas", "destete nocturno", "desmame nocturno", 
        "disminuir tomas", "reducir tomas", "quitar tomas", "lorena furtado"
    ]):
        specialized_rag = await get_rag_context("desmame nocturno etapas Lorena Furtado destete respetuoso")
        print(f"🌙 Búsqueda RAG especializada para desmame nocturno")
    
    # Detectar consultas sobre trabajo con pareja y agregar contexto neurológico específico
    elif any(keyword in message_lower for keyword in [
        "pareja", "esposo", "papá", "padre", "dividir", "ayuda", "trabajo nocturno", 
        "acompañar", "turno", "por turnos"
    ]):
        specialized_rag = await get_rag_context("pareja acompañamiento neurociencia asociación materna trabajo nocturno firmeza tranquila")
        print(f"👫 Búsqueda RAG especializada para trabajo con pareja")
    
    # Detectar consultas sobre vocalizaciones y comportamientos específicos
    elif any(keyword in message_lower for keyword in [
        "llora", "ruido", "grita", "alega", "canta", "om", "gruñe", "hace sonido", 
        "vocaliza", "emite", "sonido raro", "llanto diferente", "se queja"
    ]):
        specialized_rag = await get_rag_context("vocalizaciones autorregulación desarrollo emocional llanto descarga neurociencia infantil")
        print(f"🎵 Búsqueda RAG especializada para vocalizaciones y comportamientos")
    
    # Combinar contextos RAG
    combined_rag_context = f"{rag_context}\n\n--- CONTEXTO ESPECIALIZADO ---\n{specialized_rag}" if specialized_rag else rag_context
    user_context, routines_context = await get_user_profiles_and_babies(user["id"], supabase)
    history = await get_conversation_history(user["id"], supabase)  # 👈 historial del backend

    #print(f"📚 Contexto RAG recuperado:\n{rag_context[:500]}...\n")
    
    # Formatear el perfil que viene en el payload
    profile_text = ""
    if payload.profile:
        profile_data = payload.profile
        profile_text = (
            "**Perfil actual en esta consulta:**\n"
            f"- Fecha de nacimiento: {profile_data.get('dob')}\n"
            f"- Alimentación: {profile_data.get('feeding')}\n"
        )

    # Cargar y formatear el prompt maestro
    system_prompt_template = load_system_prompt()
    
    # Preparar contextos para el template
    formatted_system_prompt = system_prompt_template.format(
        today=today,
        user_context=user_context if user_context else "No hay información específica del usuario disponible.",
        profile_context=profile_text if profile_text else "No se proporcionó perfil específico en esta consulta.",
        routines_context=routines_context if routines_context else "No hay rutinas específicas registradas.",
        rag_context=combined_rag_context if combined_rag_context else "No hay contexto especializado disponible para esta consulta."
    )

    # Construcción del body con prompt unificado
    body = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": formatted_system_prompt},
            *history,  
            {"role": "user", "content": payload.message},
        ],
        "max_tokens": 1800,
        "temperature": 0.4,
        "top_p": 0.9,
    }

    headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)

    if resp.status_code >= 300:
        raise HTTPException(status_code=502, detail={"openai_error": resp.text})

    data = resp.json()
    assistant = data.get("choices", [])[0].get("message", {}).get("content", "")
    
    # Formatear la respuesta para mayor naturalidad
    assistant = format_llm_output(assistant)
    
    usage = data.get("usage", {})

    # Variables para controlar el flujo de detección dual
    routine_detected_and_saved = False
    assistant_with_routine_confirmation = ""

    # PRIMERA PRIORIDAD: Detectar rutinas en el mensaje del usuario
    try:
        print(f"� Analizando mensaje para rutinas: {payload.message}")
        
        # Usar el mismo contexto de bebés
        babies = supabase.table("babies").select("*").eq("user_id", user_id).execute()
        babies_context = babies.data or []
        
        # Analizar el mensaje para detectar información de rutinas
        detected_routine = await RoutineDetector.analyze_message(
            payload.message, 
            babies_context
        )
        print(f"🕐 Rutina detectada: {detected_routine}")
        
        # Si se detecta una rutina, guardar en caché y preguntar confirmación
        if detected_routine and RoutineDetector.should_ask_confirmation(detected_routine):
            print("✅ Se debe preguntar confirmación de rutina")
            
            # Guardar en caché para confirmación posterior
            routine_confirmation_cache.set_pending_confirmation(user_id, detected_routine, payload.message)
            
            confirmation_message = RoutineDetector.format_confirmation_message(detected_routine)
            
            # Agregar la pregunta de confirmación a la respuesta
            assistant_with_routine_confirmation = f"{assistant}\n\n� {confirmation_message}"
            
            return {
                "answer": assistant_with_routine_confirmation, 
                "usage": usage
            }
        else:
            print("❌ No se debe preguntar confirmación de rutina")
        
    except Exception as e:
        print(f"Error en detección de rutinas: {e}")
        import traceback
        traceback.print_exc()
        # Continuar normalmente si falla la detección
        pass

    # SEGUNDA PRIORIDAD: Detectar conocimiento importante en el mensaje del usuario
    try:
        print(f"� Analizando mensaje para conocimiento: {payload.message}")
        
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
            assistant_with_confirmation = f"{assistant}\n\n� {confirmation_message}"
            
            return {
                "answer": assistant_with_confirmation, 
                "usage": usage
            }
        else:
            print("❌ No se debe preguntar confirmación de conocimiento")
        
    except Exception as e:
        print(f"Error en detección de conocimiento: {e}")
        import traceback
        traceback.print_exc()
        # Continuar normalmente si falla la detección
        pass

    return {"answer": assistant, "usage": usage}