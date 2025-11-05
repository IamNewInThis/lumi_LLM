# Debug para entender mejor la búsqueda
import asyncio
from src.rag.retriever import vs

async def debug_search():
    query = "disciplina positiva sin castigos"
    
    # Búsqueda básica
    results = vs.similarity_search(query, k=15)
    
    print(f"🔍 Analizando query: '{query}'")
    print(f"📊 Total resultados: {len(results)}")
    
    # Agrupar por source
    by_source = {}
    for i, doc in enumerate(results):
        source = doc.metadata.get("source", "unknown")
        if source not in by_source:
            by_source[source] = []
        by_source[source].append({
            'index': i,
            'content_preview': doc.page_content[:100].replace('\n', ' '),
            'metadata': doc.metadata
        })
    
    print(f"\n📁 Documentos encontrados:")
    for source, docs in by_source.items():
        print(f"\n{source}: {len(docs)} chunks")
        for doc in docs[:2]:  # Solo los primeros 2 de cada fuente
            content_preview = doc['content_preview']
            print(f"  - Pos {doc['index']}: {content_preview}...")
    
    # Ahora búsqueda específica en disciplina_sin_lagrimas
    print(f"\n🎯 Búsqueda específica en disciplina_sin_lagrimas.pdf:")
    disciplina_results = vs.similarity_search(
        query, 
        k=5, 
        filter={"source": "disciplina_sin_lagrimas.pdf"}
    )
    
    for i, doc in enumerate(disciplina_results):
        content_preview = doc.page_content[:150].replace('\n', ' ')
        print(f"  {i+1}. {content_preview}...")

if __name__ == "__main__":
    asyncio.run(debug_search())