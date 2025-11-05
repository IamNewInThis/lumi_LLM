# Test específico para sobreestimulación
import asyncio
from src.rag.utils import get_rag_context

async def test_sobreestimulacion():
    query = "sobreestimulación en niños"
    context = await get_rag_context(query)
    print(f"\n🔎 Query: {query}")
    print("Resultado:")
    print(context[:800], "..." if len(context) > 800 else "")

if __name__ == "__main__":
    asyncio.run(test_sobreestimulacion())