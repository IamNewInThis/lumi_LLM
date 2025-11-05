# tests/test_retriever.py
import asyncio
from src.rag.utils import get_rag_context

async def main():
    # Tests específicos por categoría de documentos subidos
    queries = [
        # Tests de SUEÑO (docs/1/)
        # "mi bebé no duerme toda la noche",
        # "cómo hacer rutina de sueño",
        # "despertares nocturnos frecuentes",
        # "destete nocturno gradual",
        
        # Tests de ALIMENTACIÓN 
        # "mi niño no quiere comer",
        # "rechaza la comida nueva",
        # "crear hábitos alimentarios saludables",
        
        # Tests de DISCIPLINA/DESARROLLO
        # "cómo manejar las rabietas",
        # "disciplina sin gritos",
        # "desarrollo del cerebro infantil",
        # "conexión antes que corrección",
        
        # Tests GENERALES - ya probados
        # "presencia emocional de los padres",
        # "simplificar la crianza", 
        # "manejo de emociones infantiles",
        
        # Tests adicionales para evaluar cobertura
        "disciplina positiva sin castigos",
        "sobreestimulación en niños", 
        "crianza respetuosa",
        "límites sin gritos",
        "exceso de actividades infantiles",
        
        # Test de contenido que NO debería estar
        # "naves espaciales en la crianza"  
    ]

    for q in queries:
        context = await get_rag_context(q)
        print(f"\n🔎 Query: {q}")
        print("Resultado:")
        print(context[:800], "..." if len(context) > 800 else "")

if __name__ == "__main__":
    asyncio.run(main())
