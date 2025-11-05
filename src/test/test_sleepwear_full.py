"""
Test completo: Detección + Guardado de keywords anidados (sleepwear)
"""
import sys
import os
import asyncio
from pathlib import Path

# Agregar el directorio src al path
sys.path.append(str(Path(__file__).parent.parent))

from utils.keywords_rag import detect_profile_keywords
from services.profile_service import BabyProfileService

async def test_sleepwear_detection_and_save():
    # Test: Detectar y guardar "con body de manga corta"
    message = "El bebé duerme con body de manga corta y con saco liviano"
    age_months = 3
    baby_id = "f3c64a1e-9f77-4621-a5c7-ab3fc87a12a4"  # Baby ID de prueba
    
    print(f"{'='*80}")
    print(f"🧪 TEST: Detección y guardado de keywords anidados (sleepwear)")
    print(f"{'='*80}\n")
    
    print(f"📝 Mensaje: {message}")
    print(f"👶 Edad: {age_months} meses")
    print(f"🆔 Baby ID: {baby_id}")
    print(f"\n{'='*80}\n")
    
    # 1. DETECCIÓN
    print(f"📡 PASO 1: Detectando keywords...")
    print(f"{'='*80}\n")
    
    detected = detect_profile_keywords(message, lang='es', verbose=True, age_months=age_months)
    
    print(f"\n{'='*80}")
    print(f"🎯 Keywords detectados: {len(detected)}")
    print(f"{'='*80}\n")
    
    for i, kw in enumerate(detected, 1):
        print(f"{i}. Keyword:")
        print(f"   Category: {kw.get('category')}")
        print(f"   Age Range: {kw.get('age_range')}")
        print(f"   Subcategory: {kw.get('subcategory')}")
        print(f"   Field: {kw.get('field')}")
        print(f"   Field Key: {kw.get('field_key')}")
        print(f"   Keyword: '{kw.get('keyword')}'")
        print()
    
    # 2. TRADUCCIONES
    print(f"{'='*80}")
    print(f"🌍 PASO 2: Obteniendo traducciones...")
    print(f"{'='*80}\n")
    
    for kw in detected:
        translations = BabyProfileService.get_keyword_translations(kw.get('keyword'), kw)
        print(f"📄 {kw.get('field')}:")
        print(f"   🇪🇸 ES: {translations.get('es')}")
        print(f"   🇬🇧 EN: {translations.get('en')}")
        print(f"   🇧🇷 PT: {translations.get('pt')}")
        print()
    
    # 3. GUARDADO EN BD
    print(f"{'='*80}")
    print(f"💾 PASO 3: Guardando en base de datos...")
    print(f"{'='*80}\n")
    
    saved_count = await BabyProfileService.save_detected_keywords(
        baby_id=baby_id,
        detected_keywords=detected,
        lang='es'
    )
    
    print(f"\n{'='*80}")
    print(f"✅ RESULTADO FINAL:")
    print(f"{'='*80}")
    print(f"   Keywords detectados: {len(detected)}")
    print(f"   Keywords guardados: {saved_count}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(test_sleepwear_detection_and_save())
