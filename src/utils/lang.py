from langdetect import detect, DetectorFactory, LangDetectException

# Para hacer el resultado reproducible
DetectorFactory.seed = 0

SUPPORTED = {"es", "en", "pt"}  # español, inglés, portugués (Brasil)
# Palabras clave exclusivas de cada idioma para mejorar la detección
PORTUGUESE_MARKERS = {
    'quero', 'você', 'voce', 'não', 'nao', 'está', 'esta', 'estão', 'estao',
    'também', 'tambem', 'comigo', 'fazer', 'muito', 'obrigado', 'obrigada',
    'tchau', 'oi', 'sim', 'nós', 'nos', 'vocês', 'voces', 'são', 'sao',
    'têm', 'tem', 'mais', 'por favor', 'bom dia', 'boa tarde', 'boa noite',
    'tudo bem', 'com', 'para', 'onde', 'quando', 'porque', 'porquê'
}

SPANISH_MARKERS = {
    'quiero', 'tú', 'tu', 'usted', 'ustedes', 'también', 'tambien', 'conmigo',
    'hacer', 'mucho', 'gracias', 'adiós', 'adios', 'hola', 'sí', 'si',
    'nosotros', 'vosotros', 'tienen', 'buenos días', 'buenos dias',
    'buenas tardes', 'buenas noches', 'qué tal', 'que tal', 'con',
    'para', 'dónde', 'donde', 'cuándo', 'cuando', 'porque', 'porqué'
}

ENGLISH_MARKERS = {
    'want', 'you', 'with', 'for', 'where', 'when', 'because', 'hello',
    'hi', 'thank you', 'thanks', 'goodbye', 'bye', 'yes', 'no',
    'please', 'good morning', 'good afternoon', 'good evening', 'how are you'
}


def detect_lang(text: str, default: str = "es") -> str:
    """
    Detecta idioma del texto. Devuelve 'es', 'en' o 'pt'.
    
    Estrategia:
    1. Primero intenta detectar por palabras clave exclusivas (más preciso para frases cortas)
    2. Si no hay coincidencias claras, usa langdetect
    3. Si falla o viene vacío, retorna default
    """
    if not text or not text.strip():
        return default

    text_lower = text.lower()
    
    # 1️⃣ Contar coincidencias con palabras clave de cada idioma
    pt_count = sum(1 for marker in PORTUGUESE_MARKERS if marker in text_lower)
    es_count = sum(1 for marker in SPANISH_MARKERS if marker in text_lower)
    en_count = sum(1 for marker in ENGLISH_MARKERS if marker in text_lower)
    
    # 2️⃣ Si hay coincidencias claras, retornar el idioma con más coincidencias
    max_count = max(pt_count, es_count, en_count)
    
    if max_count > 0:
        if pt_count == max_count and pt_count > es_count:
            print(f"🇧🇷 [LANG] Portugués detectado por keywords (score: {pt_count})")
            return "pt"
        elif es_count == max_count and es_count > pt_count:
            print(f"🇪🇸 [LANG] Español detectado por keywords (score: {es_count})")
            return "es"
        elif en_count == max_count and en_count > max(pt_count, es_count):
            print(f"🇬🇧 [LANG] Inglés detectado por keywords (score: {en_count})")
            return "en"
    
    # 3️⃣ Si no hay coincidencias claras o hay empate, usar langdetect
    try:
        lang = detect(text)
        print(f"🔍 [LANG] Idioma detectado por librería: {lang}")
        
        # langdetect devuelve 'pt' para portugués de Brasil
        if lang in SUPPORTED:
            return lang
        
        # Si detecta algo distinto (ej. 'fr'), usa default
        print(f"⚠️ [LANG] Idioma '{lang}' no soportado, usando default: {default}")
        return default
        
    except LangDetectException:
        print(f"⚠️ [LANG] Error en detección, usando default: {default}")
        return default