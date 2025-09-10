from .retriever import retriever

async def get_rag_context(query: str) -> str:
    # Usar la nueva API invoke en lugar de get_relevant_documents
    docs = retriever.invoke(query)
    if not docs:
        return ""
    context = "\n\n".join([d.page_content for d in docs])
    return f"Contexto de documentos:\n{context}"
