"""
Test simplificado: Solo detección y traducciones de keywords anidados
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from utils.keywords_rag import detect_profile_keywords
from utils.keywords_profile_es import KEYWORDS_PROFILE_ES
from utils.keywords_profile_en import KEYWORDS_PROFILE_EN
from utils.keywords_profile_pt import KEYWORDS_PROFILE_PT

def find_keyword_in_dict(field_path: str, keywords_dict: dict) -> str:
    """Busca un keyword siguiendo un path"""
    parts = field_path.split('.')
    current = keywords_dict
    
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    
    return current if isinstance(current, str) else None

def get_translations(kw: dict) -> dict:
    """Obtiene traducciones de un keyword detectado"""
    category = kw.get('category', '')
    age_range = kw.get('age_range', '')
    field = kw.get('field', '')
    
    full_path = f"{category}.{age_range}.{field}"
    
    return {
        'es': find_keyword_in_dict(full_path, KEYWORDS_PROFILE_ES),
        'en': find_keyword_in_dict(full_path, KEYWORDS_PROFILE_EN),
        'pt': find_keyword_in_dict(full_path, KEYWORDS_PROFILE_PT)
    }

def test_sleepwear():
    message = "El bebé duerme con body de manga corta y con saco liviano"
    age_months = 3
    
    print(f"{'='*80}")
    print(f"🧪 TEST: Detección y traducciones de keywords anidados (sleepwear)")
    print(f"{'='*80}\n")
    
    print(f"📝 Mensaje: {message}")
    print(f"👶 Edad: {age_months} meses\n")
    print(f"{'='*80}\n")
    
    # 1. DETECCIÓN
    print(f"📡 PASO 1: Detectando keywords...\n")
    
    detected = detect_profile_keywords(message, lang='es', verbose=True, age_months=age_months)
    
    print(f"\n{'='*80}")
    print(f"🎯 Keywords detectados: {len(detected)}")
    print(f"{'='*80}\n")
    
    # 2. TRADUCCIONES
    print(f"🌍 PASO 2: Obteniendo traducciones...\n")
    
    for i, kw in enumerate(detected, 1):
        print(f"{i}. {kw.get('field')}:")
        print(f"   Keyword detectado: '{kw.get('keyword')}'")
        print(f"   Path completo: {kw.get('category')}.{kw.get('age_range')}.{kw.get('field')}\n")
        
        translations = get_translations(kw)
        
        print(f"   Traducciones:")
        print(f"   🇪🇸 ES: {translations.get('es')}")
        print(f"   🇬🇧 EN: {translations.get('en')}")
        print(f"   🇧🇷 PT: {translations.get('pt')}")
        print()
    
    # 3. VERIFICACIÓN DE ESTRUCTURA DE GUARDADO
    print(f"{'='*80}")
    print(f"💾 PASO 3: Cómo se guardaría en BD...")
    print(f"{'='*80}\n")
    
    for kw in detected:
        field_path = kw.get('field')
        subcategory = kw.get('subcategory')
        
        # Determinar si es anidado o simple
        if '.' in field_path:
            profile_key = field_path  # Anidado
            print(f"📊 Estructura ANIDADA:")
        else:
            profile_key = subcategory  # Simple
            print(f"📊 Estructura SIMPLE:")
        
        print(f"   baby_profile.key = '{profile_key}'")
        print(f"   baby_profile_value:")
        
        translations = get_translations(kw)
        print(f"      value_es = '{translations.get('es')}'")
        print(f"      value_en = '{translations.get('en')}'")
        print(f"      value_pt = '{translations.get('pt')}'")
        print()
    
    print(f"{'='*80}")
    print(f"✅ TEST COMPLETADO")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    test_sleepwear()
