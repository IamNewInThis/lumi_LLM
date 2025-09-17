# src/rag/retriever.py
import os
from supabase import create_client
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from dotenv import load_dotenv
from pathlib import Path

def get_supabase_config():
    load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / '.env')
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en .env")
    
    return supabase_url, supabase_key

SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY = get_supabase_config()  
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
emb = OpenAIEmbeddings(model="text-embedding-3-small")

vs = SupabaseVectorStore(
    client=supabase,
    table_name="documents",
    query_name="match_documents",
    embedding=emb,
)

retriever = vs.as_retriever(search_kwargs={"k": 8})   


