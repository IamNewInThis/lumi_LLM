"""
Script para listar todas las categorías disponibles en profile_category
y verificar el mapeo con keywords_rag.py
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.rag.retriever import supabase
from src.utils.keywords_rag import keywords_by_concept

def list_profile_categories():
    """
    Lista todas las categorías disponibles en la tabla profile_category
    """
    print("=" * 70)
    print("CATEGORÍAS EN PROFILE_CATEGORY")
    print("=" * 70)
    
    try:
        result = supabase.table("profile_category")\
            .select("id, category")\
            .execute()
        
        if result.data:
            print(f"\n✅ Encontradas {len(result.data)} categorías:\n")
            for i, cat in enumerate(result.data, 1):
                print(f"{i}. {cat['category']}")
                print(f"   UUID: {cat['id']}\n")
        else:
            print("\n⚠️ No se encontraron categorías en la tabla")
            
    except Exception as e:
        print(f"\n❌ Error consultando categorías: {e}")

def verify_mapping():
    """
    Verifica qué categorías de keywords_by_concept están mapeadas
    """
    print("=" * 70)
    print("VERIFICACIÓN DE MAPEO")
    print("=" * 70)
    
    # Categorías únicas en keywords_by_concept
    keyword_categories = set()
    for concept_data in keywords_by_concept.values():
        # Extraer categoría del primer nivel de cada concepto
        # Asumiendo que la estructura es: {'es': {'categoria': {...}}}
        for lang_data in concept_data.get('keywords', {}).values():
            if isinstance(lang_data, dict):
                for key in lang_data.keys():
                    # Extraer la categoría (primer nivel de anidación)
                    if '.' in key:
                        category = key.split('.')[0]
                        keyword_categories.add(category)
    
    print(f"\n📋 Categorías únicas en keywords_by_concept: {len(keyword_categories)}\n")
    
    for i, cat in enumerate(sorted(keyword_categories), 1):
        print(f"{i}. {cat}")
    
    print("\n" + "=" * 70)
    print("RECOMENDACIÓN")
    print("=" * 70)
    print("""
Asegúrate de que cada categoría listada arriba tenga:
1. Un registro en la tabla 'profile_category' en Supabase
2. Un mapeo en BabyProfileService._get_category_id()

Ejemplo de mapeo:
    'sleep_rhythm': 'Sleep and rest',
    'temperament': 'Temperament',
    etc.
    """)

if __name__ == "__main__":
    list_profile_categories()
    print("\n")
    verify_mapping()
