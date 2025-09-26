# src/utils/knowledge_cache.py
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class KnowledgeConfirmationCache:
    """
    Cache temporal para mantener conocimiento pendiente de confirmación por usuario
    """
    
    def __init__(self):
        # Estructura: {user_id: {"knowledge": [...], "timestamp": datetime, "message_context": str}}
        self._cache: Dict[str, Dict] = {}
        
    def set_pending_confirmation(self, user_id: str, detected_knowledge: List[Dict], original_message: str):
        """
        Guarda conocimiento pendiente de confirmación para un usuario
        """
        self._cache[user_id] = {
            "knowledge": detected_knowledge,
            "timestamp": datetime.now(),
            "message_context": original_message
        }
        print(f"💾 Guardado conocimiento pendiente para usuario {user_id}: {len(detected_knowledge)} items")
    
    def get_pending_confirmation(self, user_id: str) -> Optional[Dict]:
        """
        Recupera conocimiento pendiente de confirmación para un usuario
        """
        if user_id not in self._cache:
            return None
            
        # Verificar que no haya expirado (30 minutos)
        cached_data = self._cache[user_id]
        if datetime.now() - cached_data["timestamp"] > timedelta(minutes=30):
            print(f"⏰ Conocimiento pendiente expirado para usuario {user_id}")
            del self._cache[user_id]
            return None
            
        return cached_data
    
    def clear_pending_confirmation(self, user_id: str):
        """
        Limpia conocimiento pendiente para un usuario
        """
        if user_id in self._cache:
            print(f"🗑️ Limpiando conocimiento pendiente para usuario {user_id}")
            del self._cache[user_id]
    
    def has_pending_confirmation(self, user_id: str) -> bool:
        """
        Verifica si un usuario tiene conocimiento pendiente de confirmación
        """
        return self.get_pending_confirmation(user_id) is not None

    @staticmethod
    def is_confirmation_response(message: str) -> Optional[bool]:
        """
        Detecta si un mensaje es una respuesta de confirmación
        Retorna: True = confirmar, False = rechazar, None = no es respuesta de confirmación
        """
        message_lower = message.lower().strip()
        
        # Respuestas positivas
        positive_responses = [
            "si", "sí", "yes", "ok", "okay", "vale", "claro", "perfecto",
            "confirmo", "acepto", "por favor", "dale", "sip", "sep",
            "está bien", "esta bien", "bueno", "correcto", "exacto",
            "👍", "✅", "✓"
        ]
        
        # Respuestas negativas  
        negative_responses = [
            "no", "nah", "nope", "nunca", "jamas", "jamás", "para nada",
            "no gracias", "no quiero", "mejor no", "descarta", "cancelar",
            "👎", "❌", "✗"
        ]
        
        # Verificar respuestas exactas
        if message_lower in positive_responses:
            return True
        elif message_lower in negative_responses:
            return False
            
        # Verificar frases más largas que contienen confirmación clara
        if len(message_lower) <= 20:  # Solo mensajes cortos para evitar falsos positivos
            for pos in positive_responses:
                if message_lower == pos or message_lower.startswith(pos + " ") or message_lower.endswith(" " + pos):
                    return True
            for neg in negative_responses:
                if message_lower == neg or message_lower.startswith(neg + " ") or message_lower.endswith(" " + neg):
                    return False
        
        return None  # No es una respuesta de confirmación

# Instancia global del cache
confirmation_cache = KnowledgeConfirmationCache()