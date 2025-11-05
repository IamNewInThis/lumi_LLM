import os, math
from supabase import create_client
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from pathlib import Path
from dotenv import load_dotenv

def get_supabase_config():
    load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / '.env')
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en .env")
    
    return supabase_url, supabase_key

# Initialize variables that will be used by the functions
SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY = get_supabase_config()  
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
emb = OpenAIEmbeddings(model="text-embedding-3-small")
DEFAULT_METADATA_VERSION = os.getenv("KNOWLEDGE_VERSION", "1.0")

vectorstore = SupabaseVectorStore(
    client=supabase,
    table_name="documents",
    query_name="match_documents",
    embedding=emb,
)

def pdf_to_text(path):
    reader = PdfReader(path)
    pages = [p.extract_text() or "" for p in reader.pages]
    return "\n\n".join(pages)

def clean_text(text: str) -> str:
    """Limpia saltos de línea múltiples y espacios extra"""
    return " ".join(text.split())

def chunk(text):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200, chunk_overlap=150, separators=["\n\n", "\n", " ", ""]
    )
    return splitter.split_text(text)

def ingest_pdf(path, source_name, category, version=None, ref=False):
    raw = pdf_to_text(path)
    chunks = chunk(raw)
    cleaned_chunks = [clean_text(c) for c in chunks]

    source_name = source_name.lower().strip()
    if not category:
        raise ValueError(f"Debe indicar la categoría para '{source_name}'.")
    version = version or DEFAULT_METADATA_VERSION
    
    metas = [
        {
            "source": source_name,
            "type": "pdf",
            "chunk": i,
            "category": category,
            "version": version,
            "ref": ref
        }
        for i, _ in enumerate(cleaned_chunks)
    ]
    vectorstore.add_texts(texts=cleaned_chunks, metadatas=metas)
    ref_text = " (REF)" if ref else ""
    print(f"✅ Ingestado {len(chunks)} chunks de {source_name}{ref_text} - Categoría: {category} | Versión: {version}")

if __name__ == "__main__":
    """
    Define aquí los documentos que querés ingerir.
    Para cada uno puedes especificar una versión distinta (por ejemplo, "v1", "v2", "2024.10").
    Si no indicás versión se usará la definida en `DEFAULT_METADATA_VERSION`.
    """
    DOCUMENTS_TO_INGEST = [
        # Documentos de referencias con etiqueta ref: true
        # {"path": "docs/1/referencias/Alteraciones_del_sueño_ref.pdf", "name": "Alteraciones_del_sueño_ref.pdf", "category": "Sueño y descanso", "version": 1, "ref": True},
        # {"path": "docs/1/referencias/Bedtime_ref.pdf", "name": "Bedtime_ref.pdf", "category": "Sueño y descanso", "version": 1, "ref": True},
        # {"path": "docs/1/referencias/Destete_Lumi_ref.pdf", "name": "Destete_Lumi_ref.pdf", "category": "Alimentación", "version": 1, "ref": True},
        # {"path": "docs/1/referencias/Dormir_en_su_cuna_ref.pdf", "name": "Dormir_en_su_cuna_ref.pdf", "category": "Sueño y descanso", "version": 1, "ref": True},
        # {"path": "docs/1/referencias/Estimulacion_sensorial_y_sueño_ref.pdf", "name": "Estimulacion_sensorial_y_sueño_ref.pdf", "category": "Sueño y descanso", "version": 1, "ref": True},
        # {"path": "docs/1/referencias/Estrategias_destete_nocturno_(12–36meses)_ref.pdf", "name": "Estrategias_destete_nocturno_(12–36meses)_ref.pdf", "category": "Sueño y descanso", "version": 1, "ref": True},
        # {"path": "docs/1/referencias/Rutina_del_bebé_ref.pdf", "name": "Rutina_del_bebé_ref.pdf", "category": "Rutinas y cuidados", "version": 1, "ref": True},
        # {"path": "docs/1/referencias/Siestas_ref.pdf", "name": "Siestas_ref.pdf", "category": "Sueño y descanso", "version": 1, "ref": True},
        # {"path": "docs/1/referencias/Sueño_infantil_ref.pdf", "name": "Sueño_infantil_ref.pdf", "category": "Sueño y descanso", "version": 1, "ref": True},
        # {"path": "docs/1/referencias/Sueño_infantil_temperatura_ref.pdf", "name": "Sueño_infantil_temperatura_ref.pdf", "category": "Sueño y descanso", "version": 1, "ref": True},
        # {"path": "docs/1/referencias/Temperamento_y_sueño_ref.pdf", "name": "Temperamento_y_sueño_ref.pdf", "category": "Sueño y descanso", "version": 1, "ref": True},
        
        # {"path": "docs/1/Alteraciones_del_sueño.pdf", "name": "Alteraciones_del_sueño.pdf", "category": "Sueño y descanso", "version": 1},
        # {"path": "docs/1/Bedtime.pdf", "name": "Bedtime.pdf", "category": "Sueño y descanso", "version": 1},
        # {"path": "docs/1/Destete_Lumi.pdf", "name": "Destete_Lumi.pdf", "category": "Alimentación", "version": 1},
        # {"path": "docs/1/Dormir_en_su_cuna.pdf", "name": "Dormir_en_su_cuna.pdf", "category": "Sueño y descanso", "version": 1},
        # {"path": "docs/1/Estimulacion_sensorial_y_sueño.pdf", "name": "Estimulacion_sensorial_y_sueño.pdf", "category": "Sueño y descanso", "version": 1},
        # {"path": "docs/1/Estrategias_destete_nocturno_(12–36meses).pdf", "name": "Estrategias_destete_nocturno_(12–36meses).pdf", "category": "Sueño y descanso", "version": 1},
        # {"path": "docs/1/Rutina_del_bebé.pdf", "name": "Rutina_del_bebé.pdf", "category": "Rutinas y cuidados", "version": 1},
        # {"path": "docs/1/Siestas.pdf", "name": "Siestas.pdf", "category": "Sueño y descanso", "version": 1},
        # {"path": "docs/1/Sueño_infantil_temperatura.pdf", "name": "Sueño_infantil_temperatura.pdf", "category": "Sueño y descanso", "version": 1},
        # {"path": "docs/1/Sueño_infantil.pdf", "name": "Sueño_infantil.pdf", "category": "Sueño y descanso", "version": 1},
        # {"path": "docs/1/Temperamento_y_sueño.pdf", "name": "Temperamento_y_sueño.pdf", "category": "Sueño y descanso", "version": 1},
        
        # {"path": "docs/2/AE.pdf", "name": "AE.pdf", "category": "Cuidados diarios", "version": 2},
        # {"path": "docs/2/Respeto_y_cuidados_RP.pdf", "name": "Respeto_y_cuidados_RP.pdf", "category": "Cuidados diarios", "version": 1},
        # {"path": "docs/2/Lactancia_Lumi.pdf", "name": "Lactancia_Lumi.pdf", "category": "Cuidados diarios", "version": 1},
        
        # Documentos de referencias del área 2 con etiqueta ref: true
        # {"path": "docs/2/referencias/ae_ref.pdf", "name": "ae_ref.pdf", "category": "Cuidados diarios", "version": 1, "ref": True},
        # {"path": "docs/2/referencias/child_of_mine_feeding_ref.pdf", "name": "child_of_mine_feeding_ref.pdf", "category": "Alimentación", "version": 1, "ref": True},
        # {"path": "docs/2/referencias/cuidado_dental_ref.pdf", "name": "cuidado_dental_ref.pdf", "category": "Cuidados diarios", "version": 1, "ref": True},
        # {"path": "docs/2/referencias/cuidados_corporales_ref.pdf", "name": "cuidados_corporales_ref.pdf", "category": "Cuidados diarios", "version": 1, "ref": True},
        # {"path": "docs/2/referencias/lactancia_lumi_ref.pdf", "name": "lactancia_lumi_ref.pdf", "category": "Alimentación", "version": 1, "ref": True},
        # {"path": "docs/2/referencias/lavado_nasal_ref.pdf", "name": "lavado_nasal_ref.pdf", "category": "Cuidados diarios", "version": 1, "ref": True},
        # {"path": "docs/2/referencias/mi_niño_no_me_come_ref.pdf", "name": "mi_niño_no_me_come_ref.pdf", "category": "Alimentación", "version": 1, "ref": True},
        # {"path": "docs/2/referencias/nebulizador_ref.pdf", "name": "nebulizador_ref.pdf", "category": "Cuidados diarios", "version": 1, "ref": True},
        # {"path": "docs/2/referencias/respeto_y_cuidados_ref.pdf", "name": "respeto_y_cuidados_ref.pdf", "category": "Cuidados diarios", "version": 1, "ref": True},
        # {"path": "docs/2/referencias/toxic_twenty_ref.pdf", "name": "toxic_twenty_ref.pdf", "category": "Cuidados diarios", "version": 1, "ref": True},
        

        # {"path": "docs/3/Juego_y_autonomia_RP.pdf", "name": "Juego_y_autonomia_RP.pdf", "category": "Autonomía y desarrollo integral", "version": 1},
        # {"path": "docs/3/Movimiento_libre_RP.pdf", "name": "Movimiento_libre_RP.pdf", "category": "Autonomía y desarrollo integral", "version": 1},
        
        # Documentos de referencias del área 3 con etiqueta ref: true
        {"path": "docs/3/referencias/juego_y_autonomia_ref.pdf", "name": "juego_y_autonomia_ref.pdf", "category": "Autonomía y desarrollo integral", "version": 1, "ref": True},
        {"path": "docs/3/referencias/libertad_ref.pdf", "name": "libertad_ref.pdf", "category": "Autonomía y desarrollo integral", "version": 1, "ref": True},
        {"path": "docs/3/referencias/movimiento_libre_rp_ref.pdf", "name": "movimiento_libre_rp_ref.pdf", "category": "Autonomía y desarrollo integral", "version": 1, "ref": True},
        
        # {"path": "docs/4/disciplina_sin_lagrimas.pdf", "name": "disciplina_sin_lagrimas.pdf", "category": "Emociones, vínculos y crianza respetuosa", "version": 2},
        # {"path": "docs/4/el_cerebro_del_niño.pdf", "name": "el_cerebro_del_niño.pdf", "category": "Emociones, vínculos y crianza respetuosa", "version": 2},
        # {"path": "docs/4/el_poder_de_la_presencia.pdf", "name": "el_poder_de_la_presencia.pdf", "category": "Emociones, vínculos y crianza respetuosa", "version": 2},
        # {"path": "docs/4/Emociones_y_limites_RP.pdf", "name": "Emociones_y_limites_RP.pdf", "category": "Emociones, vínculos y crianza respetuosa", "version": 1},
        # {"path": "docs/4/simplicity_parenting.pdf", "name": "simplicity_parenting.pdf", "category": "Emociones, vínculos y crianza respetuosa", "version": 2},
        
        # Documentos de referencias del área 4 con etiqueta ref: true
        # {"path": "docs/4/referencias/disciplina_sin_lagrimas_ref.pdf", "name": "disciplina_sin_lagrimas_ref.pdf", "category": "Emociones, vínculos y crianza respetuosa", "version": 1, "ref": True},
        # {"path": "docs/4/referencias/el_cerebro_del_nino_ref.pdf", "name": "el_cerebro_del_nino_ref.pdf", "category": "Emociones, vínculos y crianza respetuosa", "version": 1, "ref": True},
        # {"path": "docs/4/referencias/el_poder_de_la_presencia_ref.pdf", "name": "el_poder_de_la_presencia_ref.pdf", "category": "Emociones, vínculos y crianza respetuosa", "version": 1, "ref": True},
        {"path": "docs/4/referencias/emociones_y_limites_ref.pdf", "name": "emociones_y_limites_ref.pdf", "category": "Emociones, vínculos y crianza respetuosa", "version": 1, "ref": True},
        {"path": "docs/4/referencias/emociones_ref.pdf", "name": "emociones_ref.pdf", "category": "Emociones, vínculos y crianza respetuosa", "version": 1, "ref": True},
        {"path": "docs/4/referencias/limites_ref.pdf", "name": "limites_ref.pdf", "category": "Emociones, vínculos y crianza respetuosa", "version": 1, "ref": True},
        {"path": "docs/4/referencias/simplicity_parenting_ref.pdf", "name": "simplicity_parenting_ref.pdf", "category": "Emociones, vínculos y crianza respetuosa", "version": 1, "ref": True},
        
        # {"path": "docs/5/Tips_viajes_R.pdf", "name": "Tips_viajes_R.pdf", "category": "Viajes con niños", "version": 1},
        # {"path": "docs/5/Viajes_con_niños_MC.pdf", "name": "Viajes_con_niños_MC.pdf", "category": "Viajes con niños", "version": 1},

        # Documentos de referencias del área 5 con etiqueta ref: true
        {"path": "docs/5/referencias/tips_viajes_r_ref.pdf", "name": "tips_viajes_r_ref.pdf", "category": "Viajes con niños", "version": 1, "ref": True},
        {"path": "docs/5/referencias/viajes_con_niños_mc_ref.pdf", "name": "viajes_con_niños_mc_ref.pdf", "category": "Viajes con niños", "version": 1, "ref": True}
    ]

    for doc in DOCUMENTS_TO_INGEST:
        ingest_pdf(
            doc["path"],
            doc["name"],
            category=doc["category"],
            version=doc.get("version"),
            ref=doc.get("ref", False),
        )
