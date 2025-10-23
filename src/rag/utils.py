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
        'conflictos': ['disciplina_sin_lagrimas.pdf', 'emociones.pdf', 'el_cerebro_del_nino.pdf'],
        'hermanos': ['disciplina_sin_lagrimas.pdf', 'emociones.pdf', 'el_cerebro_del_nino.pdf'],
        'celos': ['disciplina_sin_lagrimas.pdf', 'emociones.pdf', 'el_cerebro_del_nino.pdf', 'limites.pdf'],
        'peleas': ['disciplina_sin_lagrimas.pdf', 'emociones.pdf', 'el_cerebro_del_nino.pdf', 'limites.pdf'],
        'territorialidad': ['disciplina_sin_lagrimas.pdf', 'emociones.pdf', 'el_cerebro_del_nino.pdf', 'limites.pdf'],
        'compartir': ['disciplina_sin_lagrimas.pdf', 'emociones.pdf', 'el_cerebro_del_nino.pdf'],
        'rivalidad': ['disciplina_sin_lagrimas.pdf', 'emociones.pdf', 'el_cerebro_del_nino.pdf'],
        'juguetes': ['el_cerebro_del_nino.pdf', 'emociones.pdf'],
        'sobreestimulacion': ['simplicity_parenting.pdf'],
        'actividades': ['simplicity_parenting.pdf', 'rutina_del_bebe.pdf', 'el_cerebro_del_nino.pdf'],
        'exceso': ['simplicity_parenting.pdf', 'limites.pdf', 'el_cerebro_del_nino.pdf'],
        'rutina': ['rutina_del_bebe.pdf', 'simplicity_parenting.pdf'],
        'sueño': ['acompanar_despertares.pdf','rutina_del_bebe.pdf', 'destete_nocturno.pdf', 'dormir_en_su_cuna.pdf'],
        'alimentación': ['child_of_mine_feeding.pdf', 'el_cerebro_del_nino.pdf'],
        'comida': ['child_of_mine_feeding.pdf', 'el_cerebro_del_nino.pdf'],
        'emociones': ['emociones.pdf', 'el_cerebro_del_nino.pdf'],
        'crianza respetuosa': ['emociones.pdf', 'libertad.pdf', 'simplicity_parenting.pdf'],
        'respetuosa': ['emociones.pdf', 'libertad.pdf'],
        'viajes': ['viajes_con_niños_mc.pdf','tips_viajes_r' ],
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
