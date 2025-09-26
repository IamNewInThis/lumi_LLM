# src/utils/knowledge_detector.py
import json
import httpx
import os
from typing import Dict, List, Optional, Tuple

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

class KnowledgeDetector:
    """
    Clase para detectar información importante sobre bebés en las conversaciones
    que debería ser guardada en el perfil para mejorar futuras respuestas.
    """
    
    CATEGORIES = {
        "alergias": {
            "subcategories": ["alimentarias", "ambientales", "medicamentos", "cutaneas"],
            "importance": 5,
            "keywords": ["alergia", "alergico", "reaccion", "sarpullido", "hinchazón", "dificultad respirar"]
        },
        "alimentacion": {
            "subcategories": ["gustos", "no_le_gusta", "intolerancias", "habitos", "horarios"],
            "importance": 3,
            "keywords": ["no le gusta", "le encanta", "rechaza", "come bien", "no quiere comer"]
        },
        "juguetes": {
            "subcategories": ["favoritos", "no_le_interesan", "edad_apropiados", "educativos"],
            "importance": 2,
            "keywords": ["juguete favorito", "le gusta jugar", "no le interesa", "se divierte con"]
        },
        "comportamiento": {
            "subcategories": ["miedos", "preferencias", "habitos", "reacciones", "personalidad"],
            "importance": 3,
            "keywords": ["tiene miedo", "le molesta", "se pone nervioso", "le calma", "personalidad"]
        },
        "salud": {
            "subcategories": ["condiciones", "medicamentos", "sintomas_frecuentes", "desarrollo"],
            "importance": 4,
            "keywords": ["problema de salud", "medicamento", "sintoma", "condicion", "desarrollo"]
        },
        "rutinas": {
            "subcategories": ["sueño", "comidas", "actividades", "horarios"],
            "importance": 3,
            "keywords": ["horario", "rutina", "duerme", "siesta", "actividad diaria"]
        },
        "desarrollo": {
            "subcategories": ["motor", "lenguaje", "social", "cognitivo", "hitos"],
            "importance": 4,
            "keywords": ["ya camina", "dice palabras", "gatea", "sonrie", "hito desarrollo"]
        }
    }

    @classmethod
    async def analyze_message(cls, message: str, babies_context: List[Dict] = None) -> List[Dict]:
        """
        Analiza un mensaje para detectar información importante que debería guardarse
        
        Returns:
            List[Dict]: Lista de conocimiento detectado con formato:
            {
                'baby_name': str,
                'category': str,
                'subcategory': str,
                'title': str,
                'description': str,
                'importance_level': int,
                'confidence': float
            }
        """
        if not message or len(message.strip()) < 10:
            return []

        babies_names = []
        if babies_context:
            babies_names = [baby.get('name', '') for baby in babies_context if baby.get('name')]

        system_prompt = f"""
        Eres un experto en detectar información importante sobre bebés que debería guardarse para personalizar futuras conversaciones.

        BEBÉS EN EL CONTEXTO: {', '.join(babies_names) if babies_names else 'No hay información de bebés específicos'}

        CATEGORÍAS A DETECTAR:
        1. **alergias** (CRÍTICO - importancia 5): Cualquier alergia alimentaria, ambiental, cutánea o medicamentosa
        2. **alimentacion** (importancia 3): Gustos, rechazos, intolerancias, hábitos alimentarios, horarios
           - Detecta: "no come X", "no le gusta Y", "rechaza Z", "le encanta W", "intolerante a"
        3. **juguetes** (importancia 2): Juguetes favoritos, tipos que no le interesan, preferencias de juego  
        4. **comportamiento** (importancia 3): Miedos, personalidad, reacciones, hábitos, preferencias
        5. **salud** (importancia 4): Condiciones médicas, medicamentos, síntomas frecuentes
        6. **rutinas** (importancia 3): Horarios de sueño, comidas, actividades, estructura diaria
        7. **desarrollo** (importancia 4): Hitos del desarrollo, habilidades motoras, lenguaje, sociales

        EJEMPLOS DE DETECCIÓN:
        - "mi bebé no come mantequilla" → alimentacion/no_le_gusta
        - "Franco es alérgico al huevo" → alergias/alimentarias  
        - "le encantan los bloques" → juguetes/favoritos
        - "tiene miedo a los perros" → comportamiento/miedos

        INSTRUCCIONES CRÍTICAS:
        - SIEMPRE detecta restricciones alimentarias, rechazos de comida, o preferencias claras
        - Solo detecta información ESPECÍFICA y FACTUAL sobre el bebé/niño
        - NO detectes: preguntas generales, dudas, información ya obvia por la edad
        - SI detectas: datos concretos que ayuden a personalizar futuras respuestas
        - Si no hay nombres específicos, usa "el bebé" o "el niño"
        - Para alimentación, usa confianza alta (0.8-0.9) si es claro el rechazo/preferencia

        Responde SOLO con un JSON array válido. Si no detectas nada importante, responde [].
        
        Formato esperado:
        [
            {{
                "baby_name": "nombre del bebé o 'el bebé'",
                "category": "categoria",
                "subcategory": "subcategoria específica", 
                "title": "Título breve (máx 50 chars)",
                "description": "Descripción completa del conocimiento",
                "importance_level": 1-5,
                "confidence": 0.1-1.0
            }}
        ]
        """

        user_message = f"Analiza este mensaje: '{message}'"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    json={
                        "model": OPENAI_MODEL,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message}
                        ],
                        "max_tokens": 500,
                        "temperature": 0.1,
                    },
                    headers={
                        "Authorization": f"Bearer {OPENAI_KEY}",
                        "Content-Type": "application/json"
                    }
                )

            if response.status_code != 200:
                print(f"Error en OpenAI API: {response.status_code} - {response.text}")
                return []

            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if not content.strip():
                return []

            # Parsear JSON response
            try:
                detected_knowledge = json.loads(content.strip())
                if isinstance(detected_knowledge, list):
                    # Validar y filtrar resultados con baja confianza
                    valid_knowledge = []
                    for item in detected_knowledge:
                        if (isinstance(item, dict) and 
                            item.get('confidence', 0) >= 0.6 and  # Solo alta confianza
                            item.get('category') in cls.CATEGORIES):
                            valid_knowledge.append(item)
                    
                    return valid_knowledge
                
            except json.JSONDecodeError:
                print(f"Error parsing JSON response: {content}")
                return []

        except Exception as e:
            print(f"Error en análisis de conocimiento: {e}")
            return []

        return []

    @classmethod
    def should_ask_confirmation(cls, detected_knowledge: List[Dict]) -> bool:
        """
        Determina si se debe preguntar al usuario antes de guardar
        """
        if not detected_knowledge:
            return False
        
        # Preguntar si hay al menos un elemento con importancia >= 2 o confianza >= 0.6
        for item in detected_knowledge:
            if (item.get('importance_level', 0) >= 2 or 
                item.get('confidence', 0) >= 0.6):
                return True
        
        return False

    @classmethod
    def format_confirmation_message(cls, detected_knowledge: List[Dict]) -> str:
        """
        Genera el mensaje de confirmación para el usuario
        """
        if not detected_knowledge:
            return ""

        if len(detected_knowledge) == 1:
            item = detected_knowledge[0]
            return (f"¿Te parece si guardo que {item.get('description', item.get('title', ''))} "
                   f"en el perfil de {item.get('baby_name', 'tu bebé')} para recordarlo en futuras conversaciones?")
        else:
            baby_name = detected_knowledge[0].get('baby_name', 'tu bebé')
            items_text = ', '.join([item.get('title', '') for item in detected_knowledge])
            return (f"¿Te parece si guardo esta información sobre {baby_name} "
                   f"({items_text}) en su perfil para futuras conversaciones?")