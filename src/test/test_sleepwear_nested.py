"""
Test para verificar detección de keywords anidados (sleepwear)
"""
import sys
sys.path.append('c:\\Users\\inter\\OneDrive\\Documentos\\GitHub\\lumi_bot\\src')

from utils.keywords_rag import detect_profile_keywords

# Test: Detectar "con body de manga corta" para un bebé de 3 meses
message = "El bebé duerme con body de manga corta y con saco liviano"
age_months = 3

print(f"📝 Mensaje: {message}")
print(f"👶 Edad: {age_months} meses")
print(f"\n{'='*80}\n")

detected = detect_profile_keywords(message, lang='es', verbose=True, age_months=age_months)

print(f"\n{'='*80}")
print(f"🎯 RESULTADOS:")
print(f"{'='*80}\n")

for kw in detected:
    print(f"Keyword detectado:")
    print(f"  Category: {kw.get('category')}")
    print(f"  Age Range: {kw.get('age_range')}")
    print(f"  Subcategory: {kw.get('subcategory')}")
    print(f"  Field: {kw.get('field')}")
    print(f"  Field Key: {kw.get('field_key')}")
    print(f"  Keyword: {kw.get('keyword')}")
    print()
