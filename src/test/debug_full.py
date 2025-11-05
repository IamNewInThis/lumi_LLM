# Debug completo del proceso
import asyncio
from src.rag.retriever import vs
from collections import defaultdict

async def debug_full_process():
    query = "sobreestimulación en niños"
    k = 20
    top_sources = 3
    
    print(f"🔍 Query: '{query}'")
    
    # Paso 1: búsqueda global
    results = vs.similarity_search(query, k=k)
    print(f"📊 Resultados globales: {len(results)}")
    
    # Contar por fuente
    source_counts = defaultdict(int)
    for d in results:
        src = d.metadata.get("source", "unknown")
        source_counts[src] += 1
    
    print(f"📁 Fuentes por frecuencia: {dict(source_counts)}")
    
    # Top fuentes por frecuencia
    best_sources = sorted(source_counts, key=source_counts.get, reverse=True)[:top_sources]
    print(f"🎯 Best sources por frecuencia: {best_sources}")
    
    # Paso 2: Keywords
    keyword_mapping = {
        'sobreestimulación': ['simplicity_parenting.pdf'],
    }
    
    keyword_sources = []
    query_lower = query.lower()
    for keyword, sources in keyword_mapping.items():
        if keyword in query_lower:
            print(f"✅ Keyword '{keyword}' → {sources}")
            keyword_sources.extend(sources)
    
    print(f"🔑 Keyword sources: {keyword_sources}")
    
    # Combinar fuentes
    all_sources = list(dict.fromkeys(best_sources + keyword_sources))[:top_sources]
    print(f"🎯 Fuentes finales: {all_sources}")
    
    # Buscar en cada fuente
    for src in all_sources:
        print(f"\n📖 Buscando en {src}:")
        filtered = vs.similarity_search(query, k=3, filter={"source": src})
        for i, doc in enumerate(filtered):
            preview = doc.page_content[:100].replace('\n', ' ')
            print(f"  {i+1}. {preview}...")

if __name__ == "__main__":
    asyncio.run(debug_full_process())