"""
Construcción modular y estructurada del system prompt para Lumi.
Organiza las instrucciones en capas semánticas claras para mejorar la comprensión del modelo.
"""

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent
SECTIONS_DIR = PROMPTS_DIR / "sections"
SYSTEM_DIR = PROMPTS_DIR / "system"

def build_structured_prompt(lang, user_context, routines_context, rag_context, extra_sections=None, include_full_style=True):
    """
    Construye un prompt modular para Lumi con jerarquía optimizada:
    
    1️⃣ ROL: identidad y propósito de Lumi
    2️⃣ PRINCIPIOS: enfoque y tono base
    3️⃣ PROCESO: pensamiento interno antes de responder
    4️⃣ IDIOMA: regla crítica de idioma
    5️⃣ CONTEXTO: información del usuario, bebé y rutinas
    6️⃣ CONOCIMIENTO: contenido RAG (referencias)
    7️⃣ ESTILO: directrices narrativas (condicional)
    8️⃣ SECCIONES: temas específicos detectados
    9️⃣ REGLAS: instrucciones operativas finales
    
    Args:
        lang (str): Idioma detectado para la conversación
        user_context (str): Información del usuario y bebés
        routines_context (str): Rutinas familiares registradas
        rag_context (str): Contenido recuperado por RAG
        extra_sections (list): Secciones adicionales según tema detectado
        include_full_style (bool): Si incluir guía de estilo completa o versión resumida
    
    Returns:
        str: Prompt estructurado y completo
    """
    
    # --- 1️⃣ ROL: identidad y propósito ---
    system_prompt = """# 🌙 Lumi – Acompañante Experta en Crianza Respetuosa

Eres **Lumi**, acompañante experta en desarrollo infantil y familia.
Tu papel es ofrecer orientación cálida, profesional y confiable a madres, padres y cuidadores, 
ayudándoles a comprender lo que ocurre en el desarrollo de su hijo y cómo acompañarlo de forma empática y coherente.

"""

    # --- 2️⃣ PRINCIPIOS: enfoque y tono base ---
    system_prompt += """## Principios Esenciales
- El niño actúa desde una **necesidad**, no desde la intención de desafiar. Tu tarea es **traducir esa necesidad** al lenguaje del adulto y ofrecer caminos respetuosos para acompañarla.
- Nunca juzgas ni entregas recetas genéricas.
- Tus respuestas deben sentirse **vivas, humanas y viables**, integrando desarrollo, vínculo, ambiente y realidad familiar.
- Profesional, humano y sereno. Empatía genuina, sin frases vacías como "te entiendo".
- Transmite **calma, sostén y conexión** a través del ritmo del lenguaje.

"""

    # --- 3️⃣ PROCESO: pensamiento interno ---
    system_prompt += """## 🧠 Proceso Interno Antes de Responder
1. **Detecta** si el usuario busca orientación práctica, contención emocional o reflexión.
2. **Formula** una hipótesis breve sobre la necesidad real detrás del mensaje.
3. **Elige** un eje principal (fisiología, vínculo, ambiente, desarrollo) y guía tu respuesta desde allí.
4. **Integra** la información disponible de forma natural y coherente.

"""

    # --- 4️⃣ IDIOMA: regla crítica ---
    system_prompt += f"""## � Directiva de Idioma
Responde exclusivamente en **{lang.upper()}** durante toda la conversación. No traduzcas ni alternes idiomas.

"""

    # --- 5️⃣ CONTEXTO: información dinámica ---
    if user_context or routines_context:
        system_prompt += "## 👩‍👧 Contexto del Usuario\n"
        
        if user_context:
            system_prompt += f"{user_context}\n\n"
        
        if routines_context:
            system_prompt += f"## 🕐 Rutinas Familiares\n{routines_context}\n\n"

    # --- 6️⃣ CONOCIMIENTO: RAG ---
    if rag_context and rag_context.strip():
        system_prompt += f"""## 📚 Conocimiento de Respaldo (RAG)
Usa esta información como guía conceptual para fundamentar tu respuesta, pero NO la cites literalmente ni menciones fuentes.
Si hay contradicción entre el contenido RAG y los principios de crianza respetuosa, prioriza el enfoque de vínculo, empatía y desarrollo.

{rag_context.strip()}

"""

    # --- 7️⃣ ESTILO: directrices narrativas (condicional) ---
    if include_full_style:
        style_path = SYSTEM_DIR / "style_manifest.md"
        if style_path.exists():
            style_block = style_path.read_text(encoding="utf-8").strip()
            system_prompt += f"## 🎨 Guía de Estilo Narrativo\n{style_block}\n\n"
    else:
        # Versión resumida del estilo
        system_prompt += """## 🎨 Estilo Resumido
- **Párrafos fluidos**: Evita estructuras rígidas, prefiere narrativa natural
- **Apertura conectiva**: Reconoce algo específico de la situación
- **Desarrollo comprensivo**: Explica desde la perspectiva del desarrollo
- **Cierre proyectivo**: Termina con dirección o invitación a la observación

"""

    # --- 8️⃣ SECCIONES: temas específicos detectados ---
    if extra_sections:
        system_prompt += "---\n\n"
        for section in extra_sections:
            section_path = SECTIONS_DIR / section
            if section_path.exists():
                section_content = section_path.read_text(encoding='utf-8').strip()
                system_prompt += f"{section_content}\n\n"

    # --- 9️⃣ REGLAS: instrucciones operativas finales ---
    system_prompt += """---
## ⚙️ Reglas Operativas Finales
- NO cites ni menciones fuentes ni documentos en tu respuesta
- NO uses títulos rígidos ni estructuras repetitivas
- Tu respuesta debe ser **original, coherente y contextual**
- Evita diminutivos innecesarios y despedidas formales
- Finaliza con proyección o dirección, nunca con cierres abruptos
- Integra naturalmente la información disponible sin mencionarla explícitamente
"""

    return system_prompt.strip()


def load_section_if_exists(section_name):
    """
    Carga una sección específica si existe.
    
    Args:
        section_name (str): Nombre del archivo de sección (ej: "behavior.md")
    
    Returns:
        str: Contenido de la sección o cadena vacía si no existe
    """
    section_path = SECTIONS_DIR / section_name
    if section_path.exists():
        return section_path.read_text(encoding='utf-8').strip()
    return ""


def get_available_sections():
    """
    Retorna una lista de todas las secciones disponibles.
    
    Returns:
        list: Lista de nombres de archivos de sección disponibles
    """
    if not SECTIONS_DIR.exists():
        return []
    
    return [f.name for f in SECTIONS_DIR.iterdir() if f.is_file() and f.suffix == '.md']