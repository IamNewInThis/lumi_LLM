"""
Script de prueba para verificar el guardado automático de keywords del perfil
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.services.profile_service import BabyProfileService

async def test_profile_service():
    """
    Prueba el servicio de perfil con datos de ejemplo
    """
    print("="*70)
    print("TEST: BabyProfileService - Guardar keywords del perfil")
    print("="*70)
    
    # Simular un baby_id de ejemplo (deberías usar un ID real de tu base de datos)
    # NOTA: Cambiar este ID por uno real para pruebas reales
    test_baby_id = "00000000-0000-0000-0000-000000000000"
    
    # Simular keywords detectados (formato de detect_profile_keywords)
    detected_keywords = [
        {
            'category': 'sleep_rhythm',
            'field': 'sleep_rhythm.short_cycles',
            'field_key': 'short_cycles',
            'keyword': 'ciclos cortos'
        },
        {
            'category': 'temperament',
            'field': 'temperament.very_sensitive',
            'field_key': 'very_sensitive',
            'keyword': 'muy sensible'
        },
        {
            'category': 'sleepwear',
            'field': 'sleepwear.base.short_sleeve_bodysuit',
            'field_key': 'short_sleeve_bodysuit',
            'keyword': 'con body de manga corta'
        }
    ]
    
    print(f"\nSimulando guardado de {len(detected_keywords)} keywords...")
    print(f"Baby ID: {test_baby_id}")
    print(f"Idioma: es\n")
    
    # Probar guardar keywords individuales
    print("--- Test 1: Guardar keywords individuales ---")
    for i, kw in enumerate(detected_keywords, 1):
        print(f"\n{i}. Guardando: {kw['category']}.{kw['field_key']}")
        print(f"   Valor: '{kw['keyword']}'")
        
        result = await BabyProfileService.save_or_update_profile_keyword(
            baby_id=test_baby_id,
            category=kw['category'],
            key=kw['field_key'],
            value_es=kw['keyword']
        )
        
        if result:
            print(f"   ✅ Guardado exitosamente (ID: {result.get('id', 'N/A')})")
        else:
            print(f"   ❌ Error al guardar")
    
    # Probar guardar múltiples keywords a la vez
    print("\n--- Test 2: Guardar múltiples keywords a la vez ---")
    saved_count = await BabyProfileService.save_detected_keywords(
        baby_id=test_baby_id,
        detected_keywords=detected_keywords,
        lang='es'
    )
    print(f"\n✅ Total guardados: {saved_count}/{len(detected_keywords)}")
    
    # Probar obtener perfil completo
    print("\n--- Test 3: Obtener perfil completo ---")
    profile = await BabyProfileService.get_baby_profile(test_baby_id)
    print(f"\nRegistros en perfil: {len(profile)}")
    
    if profile:
        print("\nPrimeros 3 registros:")
        for i, record in enumerate(profile[:3], 1):
            print(f"\n{i}. {record.get('category_id')}.{record.get('key')}")
            print(f"   ES: {record.get('value_es', 'N/A')}")
            print(f"   EN: {record.get('value_en', 'N/A')}")
            print(f"   PT: {record.get('value_pt', 'N/A')}")
    
    # Probar formateo para contexto
    print("\n--- Test 4: Formatear para contexto ---")
    formatted = BabyProfileService.format_profile_for_context(profile)
    print("\nContexto formateado:")
    print(formatted)
    
    print("\n" + "="*70)
    print("TEST COMPLETADO")
    print("="*70)

# Para ejecutar el test
if __name__ == "__main__":
    import asyncio
    
    print("\n⚠️  ADVERTENCIA: Este test requiere:")
    print("   1. Una conexión válida a Supabase")
    print("   2. Un baby_id real de la base de datos")
    print("   3. La tabla 'baby_profile' debe existir\n")
    
    # Descomentar para ejecutar el test
    # asyncio.run(test_profile_service())
    
    print("✅ Script de prueba listo.")
    print("   Edita el test_baby_id con un ID real y descomenta asyncio.run() para ejecutar.")
