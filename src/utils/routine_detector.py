#src/utils/routine_detector.py
import json
import httpx
import os
from typing import List, Dict, Any, Optional
from datetime import time

class RoutineDetector:
    
    @staticmethod
    async def analyze_message(message: str, babies_context: List[Dict]) -> Optional[Dict]:
        """
        Analiza un mensaje para detectar información sobre rutinas
        """
        
        # Palabras clave que indican conversaciones sobre rutinas
        routine_keywords = [
            # Español
            "rutina", "horario", "cronograma", "agenda",
            "despertar", "desayuno", "almuerzo", "cena", "siesta",
            "dormir", "sueño", "baño", "leche", "comida",
            "jardín", "colegio", "actividades", "estudio", "estudiar",
            "tareas", "deberes", "matemáticas", "lectura", "escritura",
            "ciencias", "arte", "lunes", "miércoles", "viernes",
            "después de", "de la tarde", "semana", "establecer", "crear",
            # Inglés
            "routine", "schedule", "timetable", "plan", "agenda",
            "wake up", "breakfast", "lunch", "dinner", "nap",
            "sleep", "bath", "milk", "meal", "snack",
            "kindergarten", "school", "activities", "study", "homework",
            "math", "reading", "writing", "science", "art",
            "monday", "wednesday", "friday",
            "afternoon", "evening", "pm", "am",
            # Portugués
            "rotina", "horário", "horario", "cronograma", "agenda",
            "acordar", "despertar", "café da manhã", "cafe da manha", "almoco", "almoço", "jantar", "soneca",
            "dormir", "sono", "banho", "leite", "comida",
            "escola", "creche", "atividades", "atividades", "estudo", "estudar",
            "tarefas", "deveres", "matemática", "matematica", "leitura", "escrita",
            "ciências", "ciencias", "arte", "segunda", "quarta", "sexta",
            "tarde", "manhã", "manha", "rotina diária", "rotina diaria"
        ]

        message_lower = message.lower()

        diaper_tokens = [
            "pañal", "panal", "diaper", "fralda",
            "cambiar pañal", "cambiar panal", "cambio de pañal",
            "cambiarle el pañal", "cambiarle el panal"
        ]
        if any(token in message_lower for token in diaper_tokens):
            print("🔁 Mensaje identificado como cambio de pañal. Saltando detección de rutinas.")
            return None
        
        # Verificar si hay palabras clave relacionadas con rutinas
        has_routine_keywords = any(keyword in message_lower for keyword in routine_keywords)
        
        print(f"🔍 Mensaje: '{message}'")
        print(f"🔍 Keywords encontradas: {[k for k in routine_keywords if k in message_lower]}")
        print(f"🔍 Tiene keywords de rutina: {has_routine_keywords}")
        
        if not has_routine_keywords:
            print("❌ No hay keywords de rutina, saltando detección")
            return None
            
        # Si hay contexto de bebés, usar el primero como referencia
        baby_context = babies_context[0] if babies_context else {}
        baby_name = baby_context.get("name", "el bebé")
        
        # Calcular edad correctamente desde birthdate
        baby_age_months = 0
        if baby_context.get("birthdate"):
            from src.utils.date_utils import calcular_meses
            baby_age_months = calcular_meses(baby_context["birthdate"])
        
        print(f"👶 Bebé detectado: {baby_name} ({baby_age_months} meses)")
        
        prompt = f"""
Analiza este mensaje del usuario sobre rutinas para su bebé:

MENSAJE: "{message}"
BEBÉ: {baby_name} ({baby_age_months} meses)

¿El mensaje contiene información específica sobre horarios o actividades? 

Si el mensaje menciona rutinas, horarios, actividades específicas o días de la semana, crea una rutina DETALLADA y REALISTA.

Para rutinas de ESTUDIO (niños 3+ años), incluye múltiples actividades 
Ejemplo de respuesta para rutina de estudio:

{{
    "has_routine_info": true,
    "confidence": 0.8,
    "routine_type": "special",
    "routine_name": "Rutina de Estudio de {baby_name}",
    "activities": [
        {{
            "time_start": "16:00",
            "time_end": "16:20",
            "activity": "Matemáticas",
            "details": "Ejercicios de suma, resta y números. Juegos con bloques.",
            "activity_type": "learning"
        }},
        {{
            "time_start": "16:20",
            "time_end": "16:35",
            "activity": "Lectura",
            "details": "Cuentos ilustrados, identificar letras y palabras.",
            "activity_type": "learning"
        }},
        {{
            "time_start": "16:35",
            "time_end": "16:45",
            "activity": "Descanso",
            "details": "Estirarse, tomar agua, merienda ligera.",
            "activity_type": "care"
        }},
        {{
            "time_start": "16:45",
            "time_end": "17:00",
            "activity": "Escritura",
            "details": "Practicar trazos, dibujos, formar letras.",
            "activity_type": "learning"
        }},
        {{
            "time_start": "17:00",
            "time_end": "17:15",
            "activity": "Ciencias",
            "details": "Experimentos simples, observar la naturaleza.",
            "activity_type": "learning"
        }}
    ],
    "baby_name": "{baby_name}",
    "context_summary": "Rutina de estudio completa solicitada por el usuario"
}}

IMPORTANTE: 
- Crea actividades específicas o los que pida el usuario
- Horarios realistas o segun los pida el usuario
- Usa formato 24h (ej. 14:30)
- Si no hay horarios, crea una rutina estándar para la edad
- Si no hay actividades, crea una rutina diaria típica para la edad
- Incluye descansos entre actividades intensas
- Adapta según la edad: {baby_age_months} meses

Si NO hay información clara de rutina, responde: {{"has_routine_info": false}}
"""

        try:
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key:
                print("❌ No hay OPENAI_API_KEY configurada")
                return None
                
            # print(f"🤖 Enviando prompt a OpenAI...")
            # print(f"🤖 Prompt: {prompt[:500]}...")
                
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openai_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": os.getenv("OPENAI_MODEL", "gpt-4o"),
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 1000
                    }
                )
                
                print(f"🤖 Respuesta OpenAI status: {response.status_code}")
                
                if response.status_code != 200:
                    print(f"❌ Error en OpenAI API: {response.status_code}")
                    print(f"❌ Response: {response.text}")
                    return None
                    
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                print(f"🤖 Contenido recibido: {content}")
                
                # Parsear respuesta JSON
                try:
                    result = json.loads(content)
                    print(f"🧠 JSON parseado: {result}")
                    
                    if not result.get("has_routine_info", False):
                        print("❌ OpenAI dice que no hay info de rutina")
                        return None
                        
                    # Validar estructura de actividades
                    activities = result.get("activities", [])
                    validated_activities = []
                    
                    for i, activity in enumerate(activities):
                        if activity.get("time_start") and activity.get("activity"):
                            validated_activities.append({
                                "time_start": activity["time_start"],
                                "time_end": activity.get("time_end"),
                                "activity": activity["activity"],
                                "details": activity.get("details", ""),
                                "activity_type": activity.get("activity_type", "care"),
                                "order_index": i + 1
                            })
                    
                    if not validated_activities:
                        return None
                        
                    return {
                        "confidence": result.get("confidence", 0.7),
                        "routine_type": result.get("routine_type", "daily"),
                        "routine_name": result.get("routine_name", f"Rutina de {baby_name}"),
                        "activities": validated_activities,
                        "baby_name": baby_name,
                        "context_summary": result.get("context_summary", ""),
                        "detected_from_message": message
                    }
                    
                except json.JSONDecodeError as e:
                    print(f"❌ Error parseando JSON de OpenAI: {e}")
                    print(f"Contenido recibido: {content}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error en RoutineDetector: {e}")
            return None
    
    @staticmethod
    def should_ask_confirmation(detected_routine: Dict) -> bool:
        """
        Determina si se debe preguntar confirmación al usuario
        """
        if not detected_routine:
            return False
            
        confidence = detected_routine.get("confidence", 0.0)
        activities_count = len(detected_routine.get("activities", []))
        
        # Pedir confirmación si:
        # - Confianza > 0.5 Y al menos 1 actividad
        # - Básicamente, si detectamos algo con confianza razonable
        return confidence > 0.5 and activities_count >= 1
    
    @staticmethod
    def format_confirmation_message(detected_routine: Dict) -> str:
        """
        Formatea el mensaje de confirmación para el usuario
        """
        routine_name = detected_routine.get("routine_name", "Rutina")
        activities = detected_routine.get("activities", [])
        baby_name = detected_routine.get("baby_name", "tu bebé")
        
        if not activities:
            return ""
            
        # Crear mensaje de confirmación simple (sin tabla duplicada)
        activities_count = len(activities)
        routine_type_text = "rutina de estudio" if "estudio" in routine_name.lower() else "rutina"
        
        preview = f"💡 ¿Te parece bien que guarde esta {routine_type_text} para {baby_name}? "
        preview += f"Incluye {activities_count} actividades desde las {activities[0]['time_start']}. "
        preview += "(Responde 'sí' o 'no')"
        
        return preview
