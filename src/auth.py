# src/auth.py
import os
import httpx
from fastapi import Request, HTTPException, Depends
from dotenv import load_dotenv

def get_supabase_config():
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en .env")
    
    return supabase_url, supabase_key

# Initialize variables that will be used by the functions
SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY = get_supabase_config()

async def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autorizado")

    token = auth_header.split(" ")[1]

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
            },
        )

    if res.status_code != 200:
        raise HTTPException(status_code=401, detail="Token inválido")

    return res.json()  # devuelve info del usuario
