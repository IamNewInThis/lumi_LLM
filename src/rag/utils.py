from src.rag.retriever import vs
from collections import defaultdict
from typing import Tuple, List, Dict, Any
from src.utils import keywords_rag
import unicodedata
from rapidfuzz import fuzz


# Construye un string con metadata de origen para cada chunk recuperado
def _format_chunk_with_source(doc) -> str:
    metadata = getattr(doc, "metadata", {}) or {}
    source = metadata.get("source", "unknown")
    chunk_index = metadata.get("chunk")
    page = metadata.get("page")

    info_parts = [f"Fuente: {source}"]
    if page is not None:
        info_parts.append(f"Página: {page}")
    if chunk_index is not None:
        info_parts.append(f"Chunk: {chunk_index}")

    header = " | ".join(info_parts)
    return f"[{header}]\n{doc.page_content}"


# Función para normalizar texto (quitar acentos)
def remove_accents(text: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )

# Consultar hasta 3 documentos para contexto
def get_rag_context(query: str, k: int = 20, top_sources: int = 3, search_id: str = "main") -> Tuple[str, List[str]]:
    """
    Recupera contexto del RAG combinando los documentos más relevantes.
    Si se detectan palabras clave, usa solo las fuentes asociadas (con fuzzy matching).
    """

    query_norm = remove_accents(query.lower())
    matched_sources = []
    matched_keywords = []

    # 🔍 Buscar coincidencias "difusas" entre query y keywords
    for keyword, sources in keywords_rag.keywords.items():
        normalized_keyword = remove_accents(keyword.lower())

        # Calcula similitud fuzzy (0 a 100)
        similarity = fuzz.partial_ratio(normalized_keyword, query_norm)

        # Considerar coincidencia si es >= 80
        if similarity >= 87 or normalized_keyword in query_norm:
            matched_sources.extend(sources)
            matched_keywords.append((keyword, similarity))

    if matched_sources:
        matched_sources = list(dict.fromkeys(matched_sources))
        print(f"🎯 [{search_id.upper()}] Keywords detectadas → {matched_keywords}")
        print(f"📚 Fuentes asociadas → {matched_sources}")

        combined = []
        for src in matched_sources:
            filtered = vs.similarity_search(query, k=5, filter={"source": src})
            combined.extend(filtered)

        if not combined:
            print("⚠️ Sin resultados en fuentes keyword, fallback global...")
            combined = vs.similarity_search(query, k=k)

        context = "\n\n".join(_format_chunk_with_source(doc) for doc in combined)
        return context, matched_sources

    # 🔹 Si no hay keywords detectadas, usa búsqueda semántica estándar
    results = vs.similarity_search(query, k=k)
    if not results:
        return "", []

    source_counts = defaultdict(int)
    for d in results:
        src = d.metadata.get("source", "unknown")
        source_counts[src] += 1

    best_sources = sorted(source_counts, key=source_counts.get, reverse=True)[:top_sources]
    combined = []
    for src in best_sources:
        filtered = vs.similarity_search(query, k=5, filter={"source": src})
        combined.extend(filtered)

    if not combined:
        combined = results

    context = "\n\n".join(_format_chunk_with_source(doc) for doc in combined)
    return context, best_sources

def get_rag_context_simple(query: str, k: int = 20, top_sources: int = 3, search_id: str = "main") -> str:
    """
    Versión simple que solo retorna el contexto (para compatibilidad hacia atrás).
    """
    context, sources = get_rag_context(query, k, top_sources, search_id)
    return context

async def get_all_reference_chunks_from_file(source_file: str, search_id: str = "references") -> List[Dict[str, Any]]:
    """
    Obtiene chunks relevantes de un archivo específico para consultas de referencias.
    Prioriza chunks con ref=true, pero si no los encuentra, devuelve chunks relevantes del archivo.
    
    Args:
        source_file: Nombre del archivo (ej: 'ae_ref.pdf' o 'ae.pdf')
        search_id: ID para logging
    
    Returns:
        List[Dict]: Lista de chunks con metadata completa
    """
    try:
        # Buscar todos los chunks de este archivo específico usando un filtro amplio
        # Usamos una query muy genérica para obtener todos los chunks del archivo
        all_chunks = vs.similarity_search(
            "información contenido documento", 
            k=1000,  # Número alto para obtener todos los chunks
            filter={"source": source_file}
        )
        
        print(f"🔍 [{search_id.upper()}] Encontrados {len(all_chunks)} chunks totales en {source_file}")
        
        if not all_chunks:
            print(f"❌ [{search_id.upper()}] No se encontraron chunks en {source_file}")
            return []
        
        # Convertir a formato dict
        all_chunks_data = []
        for doc in all_chunks:
            chunk_data = {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "source": doc.metadata.get("source", "unknown"),
                "ref": doc.metadata.get("ref", False),
                "type": doc.metadata.get("type", "unknown"),
                "chunk": doc.metadata.get("chunk", 0),
                "version": doc.metadata.get("version", 1),
                "category": doc.metadata.get("category", "General")
            }
            all_chunks_data.append(chunk_data)
        
        # Filtrar chunks que tienen ref=true (prioridad)
        reference_chunks = [chunk for chunk in all_chunks_data if chunk.get("ref") is True]
        
        if reference_chunks:
            print(f"✅ [{search_id.upper()}] Encontrados {len(reference_chunks)} chunks con ref=true en {source_file}")
            return reference_chunks
        else:
            # Si no hay chunks con ref=true, devolver los primeros chunks del archivo como fallback
            print(f"⚠️ [{search_id.upper()}] No hay chunks con ref=true en {source_file}")
            print(f"🔄 [{search_id.upper()}] Usando chunks generales como fallback (primeros 3)")
            
            # Devolver máximo 3 chunks como muestra del contenido
            fallback_chunks = all_chunks_data[:3]
            return fallback_chunks
        
    except Exception as e:
        print(f"❌ Error obteniendo chunks de {source_file}: {e}")
        return []

async def get_rag_context_with_sources(query: str, k: int = 20, top_sources: int = 3, search_id: str = "references") -> Tuple[str, List[Dict[str, Any]]]:
    """
    Versión especial de get_rag_context que devuelve tanto el contexto como los chunks con metadata.
    Especialmente útil para consultas de referencias que necesitan acceso a metadata como 'ref: true'.
    
    Returns:
        Tuple[str, List[Dict]]: (contexto_texto, lista_de_chunks_con_metadata)
    """
    
    # Paso 1: búsqueda global más amplia
    results = vs.similarity_search(query, k=k)
    if not results:
        return "", []

    # Contar ocurrencias por fuente
    source_counts = defaultdict(int)
    for d in results:
        src = d.metadata.get("source", "unknown")
        source_counts[src] += 1

    # Elegir top fuentes basado en frecuencia
    best_sources = sorted(source_counts, key=source_counts.get, reverse=True)[:top_sources]
    
    print(f"🎯 [{search_id.upper()}] Documentos dominantes detectados sources: {best_sources}")

    # Paso 2: búsqueda refinada en esas fuentes
    combined = []
    for src in best_sources:
        filtered = vs.similarity_search(query, k=5, filter={"source": src})
        combined.extend(filtered)

    # Fallback si no hubo nada
    if not combined:
        combined = results

    # Preparar contexto y chunks con metadata
    context = "\n\n".join(_format_chunk_with_source(doc) for doc in combined)
    
    # Convertir chunks a formato dict con metadata completa
    chunks_with_metadata = []
    for doc in combined:
        chunk_data = {
            "content": doc.page_content,
            "metadata": doc.metadata,
            # Extraer campos específicos de metadata para fácil acceso
            "source": doc.metadata.get("source", "unknown"),
            "ref": doc.metadata.get("ref", False),
            "type": doc.metadata.get("type", "unknown"),
            "chunk": doc.metadata.get("chunk", 0),
            "version": doc.metadata.get("version", 1),
            "category": doc.metadata.get("category", "General")
        }
        chunks_with_metadata.append(chunk_data)
    
    # Filtrar chunks que tienen ref: true para referencias
    reference_chunks = [chunk for chunk in chunks_with_metadata if chunk.get("ref") is True]
    
    print(f"📚 [{search_id.upper()}] Total chunks: {len(chunks_with_metadata)}, Chunks con ref=true: {len(reference_chunks)}")
    
    return context, reference_chunks
