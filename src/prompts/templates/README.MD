# 🧠 Carpeta: Templates de Respuesta

Esta carpeta contiene **plantillas estructuradas** que guían al modelo en la redacción de respuestas extensas o especializadas dentro del sistema **Lumi**.

Los templates funcionan como **formatos base reutilizables**, que el modelo invoca automáticamente cuando detecta ciertos temas o palabras clave en la conversación (por ejemplo, “destete”, “rutina diaria”, “rechazo de comida”, “ideas creativas”, etc.).

---

## 🎯 Objetivo general

Asegurar que Lumi mantenga coherencia, estructura y tono profesional en respuestas complejas o con alto componente emocional, sin perder naturalidad ni adaptabilidad.

Cada template:
- Define **bloques funcionales** (comprender → orientar → sostener).  
- Mantiene un tono empático y humano, evitando respuestas genéricas.  
- Permite **personalización dinámica** mediante variables (`[nombre]`, `[edad]`, `[alimento]`, etc.).  
- Garantiza **consistencia narrativa y visual** entre temas diferentes.

---

## 🧩 Templates disponibles

| Archivo | Propósito | Activación por tema |
|----------|------------|--------------------|
| `template_alimentacion_rechazo.md` | Acompaña casos de rechazo o selectividad alimentaria. Explica el proceso evolutivo y ofrece estrategias prácticas sin presión. | “no quiere comer”, “rechaza la comida”, “picky eating” |
| `template_destete_lactancia.md` | Guía procesos de destete nocturno, gradual o completo, desde un enfoque respetuoso y empático. | “destete”, “reducir tomas”, “dejar el pecho”, “tomas nocturnas” |
| `template_ideas_creativas_alimentos.md` | Propone actividades y menús lúdicos semanales para reintroducir alimentos con juego, exploración y curiosidad. | “ideas creativas”, “cómo ofrecer [alimento]”, “juegos con comida” |
| `template_rutina_mejorada.md` | Estructura rutinas diarias personalizadas según edad, contexto familiar y momentos difíciles. | “rutina”, “horarios”, “organizar el día”, “siestas” |

---

## ⚙️ Variables comunes

Todos los templates incluyen variables personalizables que el modelo reemplaza automáticamente según el contexto activo:

| Variable | Descripción |
|-----------|--------------|
| `[nombre]` | Nombre del niño/a |
| `[edad]` | Edad exacta o aproximada |
| `[alimento]` | Alimento principal mencionado |
| `[contexto]` | Descripción del entorno familiar o rutina |
| `[momento difícil]` | Bloques de mayor desafío (ej. “antes de dormir”) |
| `[frase personalizada]` | Frases literales adaptadas a cada situación |

---

## 🧭 Modo de uso interno

- Los templates se activan cuando el **motor de detección semántica** identifica coincidencias con sus temas o palabras clave.  
- El sistema inserta el contenido del template dentro del flujo de generación de respuesta, manteniendo el `system_prompt_base.md` como marco general.  
- Si el usuario ya entregó información específica, el modelo **omite las secciones introductorias** y pasa directamente a la parte personalizada (según las reglas de cada template).

---

## 📏 Reglas generales

1. **No modificar el tono**: mantener estilo empático, profesional y claro.  
2. **No mezclar templates**: cada uno aborda un tema central independiente.  
3. **No añadir instrucciones de guardado o sistema** dentro de los textos.  
4. **Cierre obligatorio**: siempre ofrecer una propuesta práctica o pregunta abierta (“¿Querés que ajustemos esta rutina?”, “¿Te gustaría que armemos la versión imprimible?”).  
5. **Consistencia visual**: mantener encabezados, emojis y formato de tablas según el estándar actual.

---

## 🪶 Ejemplo de activación

> Usuario: “Mi hija ya no quiere comer brócoli, ¿qué puedo hacer?”  
> → El sistema detecta palabras clave (“no quiere comer”, “brócoli”)  
> → Activa `template_alimentacion_rechazo.md`  
> → Genera respuesta combinando estructura, ejemplos y variables personalizadas (edad, nombre, contexto, etc.)

---

**Última actualización:** Octubre 2025  
**Responsable:** Nicolás Ruiz  
**Proyecto:** Lumi – Asistente de Crianza Respetuosa
