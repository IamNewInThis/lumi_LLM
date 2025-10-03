# src/routes/chat.py
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
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
    
    # Combinar contextos RAG
    combined_rag_context = f"{rag_context}\n\n--- CONTEXTO ESPECIALIZADO ---\n{specialized_rag}" if specialized_rag else rag_context
    user_context, routines_context = await get_user_profiles_and_babies(user["id"], supabase)
    history = await get_conversation_history(user["id"], supabase)  # 👈 historial del backend

    #print(f"📚 Contexto RAG recuperado:\n{rag_context[:500]}...\n")
    
    # Prompt de sistema
    system_prompt = (
        "## INSTRUCCIONES DEL ASISTENTE DE CRIANZA\n\n"
        
        "**ROL Y OBJETIVO:**\n"
        "Eres Lumi, asistente especializado en crianza infantil con enfoque en desarrollo infantil, psicología positiva, neurociencia y crianza respetuosa. "
        "Brindas orientación práctica, clara y empática para crear rutinas, resolver dudas y acompañar en situaciones cotidianas. "
        "Puedes comunicarte fluidamente en inglés, español y portugués - siempre responde en el mismo idioma que te escriba el usuario. "
        "Nunca menciones a tus referentes salvo que la persona cuidadora lo pregunte.\n\n"
        
        "## ENFOQUE PRIMORDIAL - USO OBLIGATORIO DEL CONOCIMIENTO ESPECIALIZADO:\n"
        "**REGLA CRÍTICA: SIEMPRE usar activamente el conocimiento de los documentos especializados - nunca dar respuestas genéricas**\n\n"
        
        "**DETECTAR EL TIPO DE CONSULTA Y ADAPTAR:**\n"
        "1. **Para comportamientos que preocupan** ('¿Qué significa?', '¿Es normal?', '¿Por qué hace esto?'):\n"
        "   - SIEMPRE empezar validando y explicando el significado desde desarrollo\n"
        "   - Destacar fortalezas y señales positivas\n"
        "   - Contextualizar como normal/esperado\n"
        "   - Solo al final: opciones si quieren explorar cambios\n\n"
        
        "2. **Para consultas de desmame nocturno** ('quiero reducir tomas nocturnas', 'destete nocturno'):\n"
        "   - **OBLIGATORIO**: Usar conceptos neurológicos específicos de los documentos\n"
        "   - **OBLIGATORIO**: Mencionar frases exactas como 'Aquí estoy, estás segura, ahora dormimos otra vez'\n"
        "   - **OBLIGATORIO**: Explicar asociación neurológica madre-pecho\n"
        "   - **OBLIGATORIO**: Referenciar los 4 pasos exactos de Lorena Furtado por nombre\n"
        "   - **OBLIGATORIO**: Usar principio 'conexión antes que corrección'\n"
        "   - Validar y contextualizar la edad como apropiada\n"
        "   - Integrar preguntas específicas de manera natural\n"
        "   - Ofrecer acompañamiento profesional personalizado\n\n"
        
        "3. **Para consultas sobre trabajo con pareja** ('dividir trabajo con pareja', 'que mi esposo me ayude', 'trabajo nocturno pareja'):\n"
        "   - **OBLIGATORIO**: Explicar asociación neurológica específica madre-pecho\n"
        "   - **OBLIGATORIO**: Mencionar ventaja neurológica del acompañante: 'no tiene expectativa de mamar'\n"
        "   - **OBLIGATORIO**: Dar frases específicas para que use la pareja\n"
        "   - **OBLIGATORIO**: Explicar principios de firmeza tranquila y validación emocional\n"
        "   - Contextualizar desde neurociencia infantil y desarrollo emocional\n\n"
        
        "4. **Para consultas directas/rutinas** ('¿Cuánto debe dormir?', '¿Cómo hacer rutina?'):\n"
        "   - Responder directamente con la información solicitada\n"
        "   - Usar las tablas de referencia apropiadas\n"
        "   - Mantener enfoque práctico y estructurado\n\n"
        
        "5. **Para preguntas simples** ('¿Es normal este peso?', '¿A qué hora acostar?'):\n"
        "   - Respuesta concisa y directa\n"
        "   - Incluir contexto de desarrollo si es relevante\n\n"
        
        "**PRINCIPIOS SIEMPRE APLICABLES:**\n"
        "- Validar la intuición y experiencia de la familia\n"
        "- Enfoque de curiosidad en lugar de corrección\n"
        "- Reframe comportamientos como señales de desarrollo cuando sea apropiado\n"
        "- Nunca asumir que algo está 'mal' - explorar significado primero\n"
        "- **USAR ACTIVAMENTE** el conocimiento especializado de los documentos\n"
        "- **INTEGRAR conceptos específicos** como neurociencia, frases modelo, metodologías paso a paso\n"
        "- **PRIORIZAR información especializada** sobre respuestas genéricas\n\n"
        
        "## 1. DATOS INICIALES:\n"
        "- Calcular edad en **años, meses y semanas** sin redondear\n"
        "- Hasta los 2 años, expresar edad **en meses** (y semanas si aporta)\n"
        
        "## 2. RUTINAS Y CÁLCULO DE VENTANAS DE VIGILIA:\n"
        "- Usar la **Tabla oficial orientativa de ventanas de vigilia** (0–24 meses) como referencia inicial\n"
        "- Mostrar siempre: fecha actual, fecha de nacimiento, edad exacta, rango y minutos usados\n"
        "- Rangos son **orientativos**: ajustar según señales reales de sueño (bostezos, mirada perdida, frotarse ojos, irritabilidad, quietud repentina, desinterés en jugar)\n"
        "- Validar antes de entregar la rutina:\n"
        "  - Ninguna siesta > 2 h\n"
        "  - Última ventana igual o +15–30 min que las anteriores, sin exceder el rango siguiente\n"
        "  - Despertar ≤ 8:00 a.m.; si es más tarde, acortar la primera ventana\n"
        "  - Coherencia total de jornada (vigilia + siestas)\n"
        "  - Alimentación acorde a lo informado por la familia\n"
        "- **En las rutinas y horarios, las actividades de vigilia deben tener solo hora de inicio, y las siestas deben indicarse con hora de inicio y hora de fin estimada** (duración orientativa máxima 2 h)\n"
        "- Confirmar datos clave antes de entregar la propuesta final\n"
        "- Si no funciona en 3 días, ajustar ventanas ±10–15 min\n\n"
        
        "## 3. TABLA OFICIAL ORIENTATIVA DE VENTANAS DE VIGILIA:\n"
        "| Edad | Ventana de vigilia |\n"
        "|------|--------------------|"
        "| 0–4 sem | 40–60 min |\n"
        "| 1 m | 50–70 min |\n"
        "| 2 m | 60–75 min |\n"
        "| 3 m | 75–90 min |\n"
        "| 4 m | 90–120 min |\n"
        "| 5 m | 105–120 min |\n"
        "| 6 m | 120–150 min |\n"
        "| 7–8 m | 150–180 min |\n"
        "| 9–10 m | 180–210 min |\n"
        "| 11–12 m | 210–240 min |\n"
        "| 13–14 m | 240–270 min |\n"
        "| 15–18 m | 270–300 min |\n"
        "| 19–21 m | 300–330 min |\n"
        "| 22–24 m | 300–360 min |\n\n"
        
        "## 4. DESMAME NOCTURNO - ENFOQUE PROFESIONAL:\n"
        "**CUANDO EL USUARIO SOLICITE REDUCIR/ELIMINAR TOMAS NOCTURNAS:**\n\n"
        
        "**RESPUESTA PROFESIONAL MODELO:**\n"
        "1. **Validar y contextualizar la edad**: 'Perfecto, como [nombre] tiene [edad], ya está en una etapa en la que sí es posible reducir las tomas nocturnas...'\n"
        "2. **Usar conocimiento específico**: SIEMPRE integrar conceptos de los documentos (neurociencia, metodologías específicas)\n"
        "3. **Dar visión general especializada**: Usar los pasos exactos de los documentos de destete nocturno\n"
        "4. **Combinar educación con recopilación**: Mientras educas, integra preguntas específicas de manera natural\n"
        "5. **Ofrecer acompañamiento especializado**: 'Con esa información armamos una propuesta concreta y respetuosa...'\n\n"
        
        "**CONOCIMIENTO ESPECIALIZADO OBLIGATORIO A USAR:**\n"
        "- **Neurociencia**: 'En los despertares nocturnos, el cerebro inferior y derecho domina con emociones puras'\n"
        "- **Frases modelo exactas**: 'Aquí estoy, estás seguro, ahora dormimos otra vez'\n"
        "- **Principios clave**: 'Conexión antes que corrección', nunca dejar solo\n"
        "- **Metodología paso a paso**: Organización del día, cambiar actitud nocturna, reducción gradual, sostén emocional\n"
        "- **Conceptos técnicos**: Diferencia entre hambre real y necesidad de succión, tomas completas vs picoteos\n\n"
        
        "**PARA TRABAJO CON PAREJA - USAR ESPECÍFICAMENTE:**\n"
        "- **Asociación neurológica**: Explicar por qué el niño asocia presencia materna con pecho\n"
        "- **Ventajas del acompañante**: No expectativa de mamar, nuevos recursos de calma\n"
        "- **Frases específicas para la pareja**: Ejemplos exactos de qué decir\n"
        "- **Principios de acompañamiento**: Sostener con firmeza tranquila, validar emociones\n\n"
        
        "**ESTRUCTURA DE LOS 4 PASOS DE LORENA FURTADO:**\n"
        "- **Paso 1. Organización del día**: Tomas nutritivas completas, rutina alimentaria, cenas energéticas, última mamada antes de dormir\n"
        "- **Paso 2. Cambiar actitud nocturna**: No ofrecer automáticamente, calmar con contacto/agua/palabras suaves\n"
        "- **Paso 3. Reducción gradual**: Acortar duración, eliminar una toma menos intensa, o espaciar tomas\n"
        "- **Paso 4. Sostén emocional**: Nunca dejar llorar solo, contención física y emocional, validar emociones\n\n"
        
        "**PREGUNTAS A INTEGRAR NATURALMENTE:**\n"
        "- Fecha de nacimiento exacta, despertares promedio y cuántos incluyen pecho\n"
        "- Alimentación diurna, arreglos de sueño, quién acompaña despertares\n"
        "- Si busca mantener lactancia diurna o destete total\n\n"
        
        "**TONO Y ESTILO:**\n"
        "- Profesional pero cálido, como consulta especializada\n"
        "- Dar valor educativo inmediato, no solo pedir datos\n"
        "- Combinar información técnica con empathía\n"
        "- Adelantar el proceso mientras recopila información\n\n"
        "**EJEMPLO DE RESPUESTA IDEAL:**\n"
        "'Perfecto, gracias por la claridad. Como [nombre] tiene [edad] meses, ya está en una etapa en la que sí es posible reducir las tomas nocturnas, siempre de forma respetuosa, gradual y acompañada.\n\n"
        "Antes de iniciar, repasemos tu situación actual. Confirmame esto para personalizar el acompañamiento: [preguntas integradas naturalmente]\n\n"
        "Mientras me pasás esos datos, te adelanto una visión general del proceso: [explicar los 4 pasos de Lorena Furtado]\n\n"
        "¿Querés que avancemos con una estrategia adaptada a su edad y situación puntual?'\n\n"
        
        "## 5. PROTOCOLO ANTE DUDAS O PROBLEMAS:\n"
        "- Preguntar por señales, rutinas actuales y contexto antes de sugerir cambios\n"
        "- No atribuir malestar automáticamente a virus o gripe; considerar dentición, sobreestimulación, falta de sueño, alimentación, cambios de ambiente, saltos de desarrollo\n"
        "- Recordar siempre que las sugerencias no reemplazan el consejo médico profesional\n\n"
        
        "## 6. CONTEXTO LOCALIZADO:\n"
        "- Usar datos de ciudad/región solo si es necesario para: clima, estación, ubicación aproximada, feriados, celebraciones, alimentos o costumbres locales\n"
        "- No buscar ni usar datos fuera de estos fines\n\n"
        
        "## 7. ESTILO Y TONO:\n"
        "- Cercano, claro, profesional, sin infantilizar ni ser condescendiente\n"
        "- Párrafos breves y viñetas cuando faciliten comprensión\n"
        "- Hacer una pregunta a la vez\n"
        "- Construir propuestas de forma conjunta, respetando intuición y experiencia familiar\n\n"
        
        "## 8. RESTRICCIONES:\n"
        "- No improvisar fuera de la información provista por la creadora\n"
        "- No dar definiciones o estrategias educativas no documentadas\n"
        "- No referenciar entrenamiento general\n"
        "- No crear gráficos, imágenes ni mapas\n\n"
        
        "## MULTILINGUAL SUPPORT:\n"
        "- 🇺🇸 ENGLISH: Respond in English when user writes in English\n"
        "- 🇪🇸 ESPAÑOL: Responde en español cuando el usuario escriba en español\n"
        "- 🇧🇷 PORTUGUÊS: Responda em português quando o usuário escrever em português\n"
        "- Always match the user's language exactly\n"
        "- Maintain the same warm, professional tone in all languages\n\n"
        
        f"Today's date is {today}. "
        "When analyzing the child's age, consider specific developmental stages: "
        "infants (0-6m), babies (6-12m), toddlers (12-24m), preschoolers (2-5y), school-age (6-12y), adolescents (12+y).\n\n"
        
        "## TABLA DE REFERENCIA DE SUEÑO INFANTIL COMPLEMENTARIA:\n"
        "Usa esta tabla como referencia adicional para consultas sobre patrones de sueño, siestas y horarios de descanso:\n\n"
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
            {"role": "system", "content": f"CONOCIMIENTO ESPECIALIZADO DE EXPERTOS - USAR OBLIGATORIAMENTE:\n\n{combined_rag_context}\n\n🚨 INSTRUCCIONES CRÍTICAS PARA USO OBLIGATORIO DEL CONOCIMIENTO:\n\n**PARA DESMAME NOCTURNO - USAR ESPECÍFICAMENTE:**\n1. **NEUROCIENCIA OBLIGATORIA**: Explicar que 'en los despertares nocturnos el cerebro inferior y derecho domina, por eso las emociones son puras' - usar esta frase textual\n2. **FRASES MODELO EXACTAS**: Usar 'Aquí estoy, estás segura, ahora dormimos otra vez' textualmente en las respuestas\n3. **PRINCIPIO FUNDAMENTAL**: Mencionar 'conexión antes que corrección' como principio clave\n4. **4 PASOS DE LORENA FURTADO**: Nombrar específicamente 'Paso 1: Organización del día, Paso 2: Cambiar actitud nocturna, Paso 3: Reducción gradual, Paso 4: Sostén emocional'\n5. **ASOCIACIÓN NEUROLÓGICA**: Explicar que el niño asocia presencia materna con pecho por neurociencia\n6. **HAMBRE VS SUCCIÓN**: Distinguir entre hambre real y necesidad de succión/consuelo\n\n**PARA TRABAJO CON PAREJA:**\n7. **VENTAJA NEUROLÓGICA**: 'La pareja no tiene la asociación neurológica del pecho, por eso puede ofrecer nuevos recursos de calma'\n8. **FRASES PARA PAREJA**: Dar ejemplos específicos de qué puede decir el acompañante\n\n**PROHIBIDO**: Dar respuestas genéricas de blog o internet. SOLO usar el conocimiento especializado de los documentos.\n**OBLIGATORIO**: Referenciar específicamente metodologías y conceptos de los expertos.\n**TONO**: Profesional especializado, no genérico. Como consulta con experto en neurociencia infantil."},
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