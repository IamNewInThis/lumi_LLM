#!/usr/bin/env python3
"""
Debug: Análisis de por qué no se detectó la rutina
"""

def debug_routine_detection():
    """Debug para la respuesta que no fue detectada"""
    print("🔍 DEBUG: ANÁLISIS DE DETECCIÓN DE RUTINAS")
    print("=" * 60)
    
    # La respuesta actual que no se detectó
    lumi_response = """¡Perfecto, gracias por compartir estos detalles! Vamos a crear una rutina diaria para Javier que sea flexible y se adapte a sus necesidades, así como a las tuyas. Consideraremos los momentos difíciles y cómo podemos suavizarlos con actividades adecuadas.

## 🧭 RUTINA DIARIA PARA JAVIER (3 años)

## 🌅 MAÑANA

**7:30–8:30**  
🛏️ **Despertar + Higiene suave**  
- Comienza el día con un despertar tranquilo. Puedes cantar una canción suave mientras lo ayudas a vestirse y lavarse la cara.

**8:30–9:00**  
🍞 **Desayuno compartido**  
- Un desayuno nutritivo juntos. Puedes involucrarlo en tareas sencillas como poner la mesa o elegir su fruta favorita.

**9:00–10:00**  
🎨 **Juego compartido**  
- Actividades como dibujar, construir con bloques o jugar con plastilina. Esto fomenta la creatividad y el vínculo.

**10:00–11:00**  
🏃 **Juego libre**  
- Tiempo para que explore y juegue de manera independiente mientras tú haces tareas de la casa. Puedes dejarle juguetes seguros y libros a su alcance.

## ☀️ MEDIODÍA

**11:00–12:00**  
📚 **Actividad tranquila**  
- Leer cuentos o hacer rompecabezas. Esto puede ayudar a calmar la irritabilidad antes del almuerzo.

**12:00–12:30**  
🍽️ **Almuerzo**  
- Un almuerzo relajado. Puedes involucrarlo en pequeñas tareas como mezclar ensaladas o servir agua.

**12:30–14:00**  
😴 **Siesta**  
- Tiempo de descanso. Asegúrate de que el ambiente sea tranquilo y oscuro para un sueño reparador.

## 🌇 TARDE

**14:00–15:00**  
🌳 **Juego al aire libre**  
- Si es posible, salir al patio o al parque. Correr y jugar al aire libre puede ser revitalizante después de la siesta.

**15:00–16:00**  
🖍️ **Actividad creativa**  
- Manualidades, pintura o música. Puedes unirte a él o dejar que explore por su cuenta.

**16:00–17:00**  
🍎 **Merienda y juego libre**  
- Una merienda ligera seguida de tiempo de juego libre. Esto te da un respiro para organizar lo que necesites.

## 🌆 FINAL DE TARDE (Momento desafiante)

**17:00–18:00**  
🎶 **Juego compartido suave**  
- Juegos tranquilos como construir con bloques o escuchar música. Esto puede ayudar a suavizar la transición hacia la cena.

**18:00–19:00**  
🍽️ **Cena**  
- Cena en familia. Puedes usar este tiempo para hablar sobre el día y planificar el siguiente.

## 🌙 NOCHE

**19:00–20:00**  
🛁 **Baño y preparación para dormir**  
- Un baño relajante seguido de ponerse el pijama. Puedes hacer un juego de burbujas o cantar canciones.

**20:00–20:30**  
📖 **Cuento y a dormir**  
- Leer un cuento y acurrucarse antes de dormir. Usa siempre el mismo ritual para que sepa que es hora de descansar.

## ✅ RESUMEN VISUAL (por bloques)

| Horario     | Actividad principal                |
| ----------- | ---------------------------------- |
| 7:30–9:00   | Despertar + desayuno + juego compartido |
| 9:00–10:00  | Juego libre                        |
| 10:00–11:00 | Actividad tranquila                |
| 11:00–12:00 | Almuerzo                           |
| 12:30–14:00 | Siesta                             |
| 14:00–15:00 | Juego al aire libre                |
| 15:00–16:00 | Actividad creativa                 |
| 16:00–17:00 | Merienda y juego libre             |
| 17:00–18:00 | Juego compartido suave             |
| 18:00–19:00 | Cena                               |
| 19:00–20:30 | Baño, cuento y a dormir            |

¿Quieres que te lo prepare en versión imprimible con íconos visuales por bloques? ¿O preferís ir ajustando esta primera propuesta según cómo funcione en los próximos días?"""

    print("\n1️⃣ VERIFICACIÓN DE PATRONES ACTUALES")
    print("-" * 40)
    
    # Patrones que usamos en el código
    routine_patterns = [
        "rutina diaria", "horario", "📅", "🌅", "mañana", "mediodía", "tarde", "noche",
        "despertar", "desayuno", "almuerzo", "siesta", "cena", "baño",
        "resumen visual", "bloques", "actividad principal"
    ]
    
    found_patterns = [pattern for pattern in routine_patterns if pattern in lumi_response.lower()]
    print(f"📋 Patrones actuales encontrados: {found_patterns}")
    print(f"📊 Total de patrones: {len(found_patterns)}")
    
    # Verificar patrones de horarios
    import re
    time_patterns = re.findall(r'\*\*\d{1,2}:\d{2}[–-]\d{1,2}:\d{2}\*\*', lumi_response)
    print(f"⏰ Horarios encontrados: {time_patterns}")
    print(f"📊 Total de horarios: {len(time_patterns)}")
    
    print("\n2️⃣ DIAGNÓSTICO DEL PROBLEMA")
    print("-" * 40)
    
    has_routine_patterns = len(found_patterns) > 0
    has_enough_time_patterns = len(time_patterns) >= 3
    
    print(f"✅ Tiene patrones de rutina: {has_routine_patterns}")
    print(f"✅ Tiene suficientes horarios (>=3): {has_enough_time_patterns}")
    print(f"🎯 Debería detectarse como rutina: {has_routine_patterns and has_enough_time_patterns}")
    
    if has_routine_patterns and has_enough_time_patterns:
        print("🤔 PROBLEMA: Los criterios se cumplen pero no se detectó")
        print("🔍 Posibles causas:")
        print("   1. Error en el código de detección")
        print("   2. Problema con las palabras clave del RoutineDetector")
        print("   3. Excepción no manejada en el proceso")
    
    print("\n3️⃣ ANÁLISIS DETALLADO DE KEYWORDS")
    print("-" * 40)
    
    # Keywords del RoutineDetector (del archivo original)
    routine_detector_keywords = [
        "rutina", "horario", "cronograma", "schedule", "agenda",
        "despertar", "desayuno", "almuerzo", "cena", "siesta",
        "dormir", "sueño", "baño", "leche", "comida",
        "jardín", "colegio", "actividades", "estudio", "estudiar",
        "tareas", "deberes", "matemáticas", "lectura", "escritura",
        "ciencias", "arte", "lunes", "miércoles", "viernes",
        "después de", "de la tarde", "pm", "3:00", "15:00",
        "tres días", "semana", "establecer", "crear"
    ]
    
    found_detector_keywords = [keyword for keyword in routine_detector_keywords if keyword in lumi_response.lower()]
    print(f"📋 Keywords del RoutineDetector encontradas: {found_detector_keywords}")
    print(f"📊 Total: {len(found_detector_keywords)}")
    
    if len(found_detector_keywords) > 0:
        print("✅ RoutineDetector DEBERÍA activarse")
    else:
        print("❌ RoutineDetector NO se activaría")
        print("🔧 SOLUCIÓN: Agregar keywords faltantes")
    
    print("\n4️⃣ IDENTIFICACIÓN DE KEYWORDS FALTANTES")
    print("-" * 40)
    
    # Keywords presentes en la respuesta que NO están en el detector
    words_in_response = set(lumi_response.lower().split())
    detector_keywords_set = set(routine_detector_keywords)
    
    # Palabras importantes que deberían estar en el detector
    important_missing = []
    important_words = [
        "mañana", "mediodía", "tarde", "noche", "despertar", "vestuario", 
        "higiene", "compartido", "libre", "creativa", "tranquila", 
        "merienda", "bloques", "imprimible"
    ]
    
    for word in important_words:
        if word in words_in_response and word not in detector_keywords_set:
            important_missing.append(word)
    
    print(f"📝 Keywords importantes que faltan en el detector: {important_missing}")
    
    print("\n5️⃣ RECOMENDACIONES")
    print("-" * 40)
    print("🔧 Agregar keywords al RoutineDetector:")
    print(f"   {important_missing}")
    print("🔧 Verificar logs del sistema para errores")
    print("🔧 Revisar si el análisis se está ejecutando correctamente")

if __name__ == "__main__":
    debug_routine_detection()