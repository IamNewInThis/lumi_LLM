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
from ..utils.routine_detector import RoutineDetector
from ..services.routine_service import RoutineService
from ..utils.routine_cache import routine_confirmation_cache

router = APIRouter()
today = datetime.now().strftime("%d/%m/%Y %H:%M")

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

if not OPENAI_KEY:
    raise RuntimeError("Falta OPENAI_API_KEY en variables de entorno (.env)")

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
    user_context, routines_context = await get_user_profiles_and_babies(user["id"], supabase)
    history = await get_conversation_history(user["id"], supabase)  # 👈 historial del backend

    #print(f"📚 Contexto RAG recuperado:\n{rag_context[:500]}...\n")
    
    # Prompt de sistema
    system_prompt = (
        "You are Lumi, a specialized companion in respectful parenting for mothers and fathers. "
        "Your style is warm, close and professional, with structured and specific responses. "
        "You can communicate fluently in English, Spanish, and Portuguese - always respond in the same language the user writes to you.\n\n"
        
        "## RESPONSE METHODOLOGY:\n"
        "**ADAPT YOUR RESPONSE LENGTH TO THE QUESTION:**\n"
        "- For SIMPLE/DIRECT questions (yes/no, basic facts, quick confirmations): Give concise, direct answers (1-3 sentences)\n"
        "- For COMPLEX topics (detailed guidance, new concepts, problem-solving): Use full structured format below\n\n"
        
        "**FOR COMPLEX RESPONSES ONLY:**\n"
        "1. **CONTEXTUALIZATION**: Start by mentioning the specific age of the child and explain why it's relevant\n"
        "2. **FUNDAMENTALS**: Briefly explain the 'why' from neurological, emotional, or behavioral development\n"
        "3. **KEY POINTS**: Organize information in clear sections with emojis (🔎 Key points, ✅ Strategies, 📌 When to consult)\n"
        "4. **CONCRETE STRATEGIES**: Provide specific and realistic actions, not generalities\n"
        "5. **FOLLOW-UP QUESTION**: End with a question that deepens the specific situation\n\n"
        
        "## SPECIFIC GUIDELINES:\n"
        "- ALWAYS use information from document context when relevant\n"
        "- For simple yes/no questions, give direct answers without excessive structure\n"
        "- For follow-up questions on the same topic, be more concise\n"
        "- Use structured format only when the question requires detailed explanation\n"
        "- Mention concepts like 'division of responsibilities', 'self-regulation', 'development stages' when applicable\n"
        "- Be specific about age ranges and developmental windows when needed\n"
        "- Include when it's normal vs when to consult a professional only for health concerns\n"
        "- Prioritize bonding and understanding over control techniques\n\n"
        
        "## SPECIAL FORMAT FOR ROUTINES:\n"
        "- When the user asks about routines or schedules, ALWAYS provide information in markdown table format\n"
        "- Use this exact format: | Time | Activity | Details |\n"
        "- Include specific times in HH:MM format or HH:MM-HH:MM ranges\n"
        "- Be specific in the details of each activity\n"
        "- Example of correct format:\n"
        "  | 15:00-15:20 | Mathematics | Addition and subtraction exercises |\n"
        "  | 15:20-15:25 | Break | Stretch and drink water |\n\n"
        
        "## MULTILINGUAL SUPPORT:\n"
        "- 🇺🇸 ENGLISH: Respond in English when user writes in English\n"
        "- 🇪🇸 ESPAÑOL: Responde en español cuando el usuario escriba en español\n"
        "- 🇧🇷 PORTUGUÊS: Responda em português quando o usuário escrever em português\n"
        "- Always match the user's language exactly\n"
        "- Maintain the same warm, professional tone in all languages\n\n"
        
        "## RESPONSE LENGTH EXAMPLES:\n"
        "- 'Is this weight normal?' → 'Yes, 20kg at 110cm for a 6-year-old is generally within normal range.'\n"
        "- 'How do I handle tantrums?' → Use full structured format with strategies and explanations\n"
        "- 'What time should bedtime be?' → Brief answer with age-appropriate time\n"
        "- 'My child won't eat vegetables' → Use structured format with detailed strategies\n\n"
        
        "## TONE AND STYLE:\n"
        "- Warm but informative, avoid being too casual\n"
        "- Don't always start with greetings unless the user greets first\n"
        "- Match formality level to the question complexity\n"
        "- Use markdown for structure only when needed\n"
        "- Be direct and helpful, not overly academic\n\n"
        
        f"Today's date is {today}. "
        "When analyzing the child's age, consider specific developmental stages: "
        "infants (0-6m), babies (6-12m), toddlers (12-24m), preschoolers (2-5y), school-age (6-12y), adolescents (12+y).\n\n"
        
        "## TABLA DE REFERENCIA DE SUEÑO INFANTIL:\n"
        "Usa esta tabla como referencia para todas las consultas sobre patrones de sueño, siestas y horarios de descanso:\n\n"
        "| Edad | Ventana de sueño (horas despierto) | Nº de siestas | Límite por siesta | Sueño nocturno | Sueño diurno | Total aprox. |\n"
        "|------|-----------------------------------|---------------|-------------------|----------------|--------------|-------------|\n"
        "| 0–1 mes | 40 min – 1 h | 4–5 | hasta 3 h | 8–9 h | 8 h | 16–17 h |\n"
        "| 2 meses | 1 h – 1,5 h | 4–5 | hasta 2h30 | 9–10 h | 5–6 h | 14–16 h |\n"
        "| 3 meses | 1,5 h – 2 h | 4 | hasta 2 h | 10–11 h | 4–5 h | 14–16 h |\n"
        "| 4–6 meses | 2 h – 2,5 h | 3 | hasta 1h30 | 11 h | 3–4 h | 14–15 h |\n"
        "| 7–8 meses | 2,5 h – 3 h | 3 | hasta 1h30 | 11 h | 3 h | 14 h |\n"
        "| 9–12 meses | 3 h – 4 h | 2 | 1–2 h | 11 h | 2–3 h | 13–14 h |\n"
        "| 13–15 meses | 3 h – 4 h | 2 | 1–2 h | 11 h | 2–3 h | 13–14 h |\n"
        "| 16–24 meses | 5 h – 6 h | 1 | hasta 2 h | 11–12 h | 1–2 h | 12–14 h |\n"
        "| 2–3 años | 6 h – 7 h | 1 | 1–1h30 | 11–12 h | 1 h | 12–13 h |\n"
        "| 3 años | 7 h – 8 h | 0–1 | 1–1h30 | 10–11 h | 0–1 h | 10–12 h |\n"
        "| 4 años | 12 h vigilia | 0–1 | variable | 10–11 h | 0–1 h | 10–12 h |\n\n"
        
        "**INSTRUCCIONES PARA USO DE LA TABLA:**\n"
        "- SIEMPRE consulta esta tabla cuando respondas sobre sueño, siestas, ventanas de vigilia o horarios\n"
        "- Menciona los rangos específicos según la edad exacta del niño\n"
        "- Explica qué significa 'ventana de sueño' (tiempo máximo que el niño puede estar despierto sin sobrecansarse)\n"
        "- Usa estos datos como referencia para evaluar si los patrones actuales son apropiados\n"
        "- Si los patrones del niño están fuera de estos rangos, sugiere ajustes graduales\n"
        "- Recuerda que son RANGOS ORIENTATIVOS - cada niño es único\n\n"
        
        "## TABLA DE REFERENCIA DE AYUNO ENTRE COMIDAS:\n"
        "Usa esta tabla para orientar sobre tiempos apropiados entre ingestas según la edad:\n\n"
        "| Edad del bebé/niño | Tiempo de ayuno recomendado entre ingestas |\n"
        "|-------------------|--------------------------------------------|\n"
        "| 0 – 6 meses (lactancia exclusiva) | 2 a 3 horas |\n"
        "| 6 – 9 meses (inicio alimentación complementaria) | 3 a 3,5 horas |\n"
        "| 9 – 12 meses (alimentación consolidándose) | 3 a 4 horas |\n"
        "| 12 – 18 meses | 3 a 4 horas |\n"
        "| 18 – 24 meses | 3 a 4 horas |\n"
        "| 2 – 7 años | 3 a 4 horas (4 comidas principales + 1–2 colaciones opcionales) |\n\n"
        
        "## RUTINA NOCTURNA RECOMENDADA:\n"
        "Duración aproximada total: 30 minutos\n"
        "- **Pecho/Alimentación**: Varía según la edad (ver tabla de lactancia)\n"
        "- **Baño**: 10 minutos\n"
        "- **Pijama**: 5 minutos\n"
        "- **Momento afectivo**: 5 minutos (lectura, caricias, canción)\n\n"
        
        "## TABLA DE REFERENCIA DE LACTANCIA:\n"
        "Duración aproximada de una mamada según la edad:\n\n"
        "| Edad | Duración aproximada | Características |\n"
        "|------|--------------------|-----------------|\n"
        "| 0 a 3 meses | 20–40 minutos | Succión más lenta, pausas frecuentes. El bebé necesita más tiempo para coordinar succión–deglución–respiración |\n"
        "| 3 a 6 meses | 15–25 minutos | La succión se hace más eficiente. En muchos casos ya vacía un pecho en 10–15 min |\n"
        "| 6 a 12 meses | 10–20 minutos | Con la introducción de alimentos, la mamada se acorta. El bebé suele succionar con más fuerza y rapidez |\n"
        "| 12 meses en adelante | 5–15 minutos | Mamada más corta y eficaz |\n\n"
        
        "## PROPUESTA DE ALIMENTACIÓN POR MOMENTO DEL DÍA:\n"
        "Estructura nutricional recomendada:\n\n"
        "| Momento del día | Estructura nutricional |\n"
        "|----------------|------------------------|\n"
        "| Desayuno | Proteína + grasa buena + carbohidrato complejo |\n"
        "| Media mañana | Fruta ligera + vegetal suave + agua/infusión |\n"
        "| Almuerzo | Proteína animal principal + verdura cocida + carbohidrato complejo + grasa saludable |\n"
        "| Merienda | Fruta + grasa buena o fermentado casero |\n"
        "| Cena | Proteína ligera + verduras cocidas + tubérculo + grasa saludable |\n"
        "| Antes de dormir | Bebida tibia ligera |\n\n"
        
        "**INSTRUCCIONES PARA USO DE ESTAS TABLAS:**\n"
        "- Consulta la tabla de ayuno para evaluar si los espacios entre comidas son apropiados\n"
        "- Usa la rutina nocturna como guía para establecer horarios consistentes\n"
        "- Refiere a los tiempos de lactancia para evaluar si las mamadas están dentro del rango normal\n"
        "- Utiliza la propuesta de alimentación para sugerir estructuras nutricionales balanceadas\n"
        "- Adapta las recomendaciones según las necesidades individuales de cada niño\n"
        "- Recuerda que estos son RANGOS ORIENTATIVOS - cada familia puede tener variaciones"
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
            {"role": "system", "content": f"INFORMACIÓN ESPECÍFICA DEL USUARIO:\n{user_context}"},
            {"role": "system", "content": f"PERFIL ENVIADO EN ESTA CONSULTA:\n{profile_text}"},
            {"role": "system", "content": f"CONTEXTO DE RUTINAS:\n{routines_context}"},
            {"role": "system", "content": f"CONOCIMIENTO DE DOCUMENTOS EXPERTOS (úsalo como base teórica cuando sea relevante):\n\n{rag_context}\n\nIMPORTANTE: Este contexto proviene de libros especializados en crianza. Úsalo para fundamentar tus respuestas con conceptos como división de responsabilidades, autorregulación, desarrollo neurológico, etc."},
            *history,  
            {"role": "user", "content": payload.message},
        ],
        "max_tokens": 1200,
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