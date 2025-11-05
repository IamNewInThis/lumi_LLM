# Debug del mapeo de keywords
import asyncio
from src.rag.utils import get_rag_context

async def debug_keywords():
    query = "sobreestimulación en niños"
    
    keyword_mapping = {
        'disciplina': ['disciplina_sin_lagrimas.pdf', 'limites.pdf'],
        'límites': ['limites.pdf', 'libertad.pdf'],
        'castigos': ['disciplina_sin_lagrimas.pdf'],
        'rabietas': ['disciplina_sin_lagrimas.pdf'],
        'sobreestimulación': ['simplicity_parenting.pdf'],
        'sobreestimulacion': ['simplicity_parenting.pdf'],
        'actividades': ['simplicity_parenting.pdf'],
        'exceso': ['simplicity_parenting.pdf'],
        'rutina': ['rutina_del_bebe.pdf'],
        'sueño': ['rutina_del_bebe.pdf'],
        'alimentación': ['child_of_mine_feeding.pdf'],
        'alimentacion': ['child_of_mine_feeding.pdf'],
        'comida': ['child_of_mine_feeding.pdf'],
        'emociones': ['emociones.pdf'],
        'crianza respetuosa': ['emociones.pdf', 'libertad.pdf'],
        'respetuosa': ['emociones.pdf', 'libertad.pdf'],
    }
    
    query_lower = query.lower()
    print(f"Query: '{query}'")
    print(f"Query lower: '{query_lower}'")
    
    keyword_sources = []
    for keyword, sources in keyword_mapping.items():
        if keyword in query_lower:
            print(f"✅ Keyword '{keyword}' found in query")
            keyword_sources.extend(sources)
        else:
            print(f"❌ Keyword '{keyword}' NOT found in query")
    
    print(f"\nKeyword sources found: {keyword_sources}")

if __name__ == "__main__":
    asyncio.run(debug_keywords())