from .retriever import vs
from collections import defaultdict

# Consultar hasta 3 documentos para contexto
async def get_rag_context(query: str, k: int = 20, top_sources: int = 3) -> str:
    """
    Recupera contexto del RAG combinando los documentos más relevantes.
    Usa una estrategia híbrida para asegurar cobertura de documentos relevantes.
    """

    # Paso 1: búsqueda global más amplia
    results = vs.similarity_search(query, k=k)
    if not results:
        return ""

    # Contar ocurrencias por fuente
    source_counts = defaultdict(int)
    for d in results:
        src = d.metadata.get("source", "unknown")
        source_counts[src] += 1

    # Elegir top fuentes basado en frecuencia
    best_sources = sorted(source_counts, key=source_counts.get, reverse=True)[:top_sources]
    
    # Paso 2: Búsqueda específica por palabras clave para asegurar cobertura
    keyword_sources = []
    
    # Mapeo de palabras clave a documentos específicos
    keyword_mapping = {
        'disciplina': ['disciplina_sin_lagrimas.pdf', 'limites.pdf'],
        'límites': ['limites.pdf', 'libertad.pdf'],
        'castigos': ['disciplina_sin_lagrimas.pdf'],
        'rabietas': ['disciplina_sin_lagrimas.pdf'],
        'sobreestimulacion': ['simplicity_parenting.pdf'],
        'actividades': ['simplicity_parenting.pdf'],
        'exceso': ['simplicity_parenting.pdf'],
        'rutina': ['rutina_del_bebe.pdf'],
        'sueño': ['rutina_del_bebe.pdf'],
        'alimentación': ['child_of_mine_feeding.pdf'],
        'comida': ['child_of_mine_feeding.pdf'],
        'emociones': ['emociones.pdf'],
        'crianza respetuosa': ['emociones.pdf', 'libertad.pdf'],
        'respetuosa': ['emociones.pdf', 'libertad.pdf'],
    }
    
    query_lower = query.lower()
    for keyword, sources in keyword_mapping.items():
        if keyword in query_lower:
            keyword_sources.extend(sources)
    
    # Combinar fuentes: priorizar keywords, luego frecuencia
    final_sources = []
    
    # Primero agregar fuentes de keywords (alta prioridad)
    for src in keyword_sources:
        if src not in final_sources:
            final_sources.append(src)
    
    # Luego agregar fuentes por frecuencia hasta completar top_sources
    for src in best_sources:
        if src not in final_sources and len(final_sources) < top_sources:
            final_sources.append(src)
    
    print(f"🎯 Documentos dominantes detectados: {final_sources}")

    # Paso 3: búsqueda refinada en esas fuentes
    combined = []
    for src in final_sources:
        filtered = vs.similarity_search(query, k=5, filter={"source": src})
        combined.extend(filtered)

    # Fallback si no hubo nada
    if not combined:
        combined = results

    # Concatenar chunks
    context = "\n\n".join([d.page_content for d in combined])
    return context
