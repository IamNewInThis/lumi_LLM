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

def chunk(text):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200, chunk_overlap=150, separators=["\n\n", "\n", " ", ""]
    )
    return splitter.split_text(text)

def ingest_pdf(path, source_name):
    raw = pdf_to_text(path)
    chunks = chunk(raw)
    metas = [{"source": source_name, "type": "pdf", "chunk": i} for i,_ in enumerate(chunks)]
    vectorstore.add_texts(texts=chunks, metadatas=metas)
    print(f"✅ Ingestado {len(chunks)} chunks de {source_name}")

if __name__ == "__main__":
    ingest_pdf("docs/el_cerebro_del_niño.pdf", "el_cerebro_del_niño.pdf")
