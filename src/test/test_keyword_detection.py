"""
Test simple para verificar la detección de keywords del perfil
"""
import sys
sys.path.insert(0, 'c:/Users/inter/OneDrive/Documentos/GitHub/lumi_bot/src')

from utils.keywords_rag import detect_profile_keywords

# Test con un bebé de 3 meses
print("="*70)
print("TEST 1: Bebé de 3 meses con mensaje 'mi bebé tiene ciclos cortos'")
print("="*70)

detected = detect_profile_keywords(
    message="mi bebé tiene ciclos cortos",
    lang='es',
    verbose=True,
    age_months=3
)

print(f"\n✅ Keywords detectados: {len(detected)}")
for kw in detected:
    print(f"   - {kw}")

# Test con un bebé de 8 meses
print("\n" + "="*70)
print("TEST 2: Bebé de 8 meses con mensaje 'duerme en colecho'")
print("="*70)

detected = detect_profile_keywords(
    message="duerme en colecho",
    lang='es',
    verbose=True,
    age_months=8
)

print(f"\n✅ Keywords detectados: {len(detected)}")
for kw in detected:
    print(f"   - {kw}")

# Test con edad None (no debería detectar nada)
print("\n" + "="*70)
print("TEST 3: Sin edad (age_months=None)")
print("="*70)

detected = detect_profile_keywords(
    message="mi bebé tiene ciclos cortos",
    lang='es',
    verbose=True,
    age_months=None
)

print(f"\n✅ Keywords detectados: {len(detected)}")
