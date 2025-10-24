# 💬 Carpeta: Sections

## 🎯 Propósito
Esta carpeta contiene los **módulos conversacionales** del asistente.  
Cada documento define **cómo debe responder, acompañar y estructurar el diálogo** en torno a un tema o necesidad específica de crianza.

Los módulos de esta carpeta no entregan datos técnicos, sino **guías de interacción**: tono, lenguaje, estructura, enfoque emocional y pasos de acompañamiento.

---

## 🧠 Función general
Cada archivo representa una **sección temática del modelo**, como sueño, conducta, alimentación o pareja, y establece:

- Cuándo debe activarse (palabras clave o contexto de consulta)  
- El tono y enfoque relacional del diálogo  
- Las fases o pasos que debe seguir la respuesta  
- Frases modelo y cierres colaborativos  
- Estructuras visuales o ejemplos de formato

---

## 🧩 Estructura recomendada por módulo
Cada documento dentro de `/sections` debe incluir:

1. **Título del módulo y activación**  
   - Ejemplo: `## Módulo: Desmame Nocturno`  
   - Explica cuándo debe activarse.

2. **Fundamento o base conceptual**  
   - Breve explicación del enfoque (neurológico, emocional o conductual).

3. **Flujo conversacional**  
   - Pasos que el asistente debe seguir (validar, explicar, proponer, acompañar).

4. **Frases o estructuras modelo**  
   - Ejemplos literales de cómo debe expresarse el asistente.

5. **Tono**  
   - Cercano, empático, profesional y humano.

6. **Cierre colaborativo**  
   - Siempre termina ofreciendo opciones, no imposiciones.

---

## 📁 Organización actual

| Archivo | Tema principal |
|----------|----------------|
| `behavior.md` | Interpretación de comportamientos y vocalizaciones |
| `night_weaning.md` | Desmame nocturno y reducción de tomas |
| `partner_support.md` | Acompañamiento en pareja y turnos nocturnos |
| `routines.md` | Construcción colaborativa de rutinas diarias |

---

## ⚙️ Criterios de mantenimiento
- Usar lenguaje claro y cálido, sin tecnicismos excesivos.  
- Mantener la coherencia estructural: validación → explicación → acompañamiento → cierre.  
- Actualizar frases modelo y tono solo si cambia la identidad de marca o el estilo base.  
- Evitar redundancias con los `templates/` (estos solo sirven para generar piezas completas).

---

> 🧩 **En resumen:**  
> `/sections` define **cómo habla y acompaña el asistente**, guiando la interacción emocional y pedagógica en cada contexto de crianza.
