#src/utils/routine_cache.py
import time
from typing import Dict, Optional

class RoutineConfirmationCache:
    """
    Maneja confirmaciones pendientes de rutinas detectadas, para que una vez que el usuario confirme, 
    se guarden en la base de datos.
    """
    
    def __init__(self):
        self._pending_confirmations: Dict[str, Dict] = {}
        self._expiration_time = 300  # Despues de 5 minutos expira la confirmación
    
    def set_pending_confirmation(self, user_id: str, routine_data: Dict, original_message: str):
        """
        Guarda una rutina pendiente de confirmación
        """
        self._pending_confirmations[user_id] = {
            "routine": routine_data,
            "original_message": original_message,
            "timestamp": time.time()
        }
        print(f"💾 Rutina guardada en caché para confirmación: {user_id}")
    
    def get_pending_confirmation(self, user_id: str) -> Optional[Dict]:
        """
        Obtiene una confirmación pendiente si existe y no ha expirado
        """
        if user_id not in self._pending_confirmations:
            return None
        
        pending = self._pending_confirmations[user_id]
        
        # Verificar expiración
        if time.time() - pending["timestamp"] > self._expiration_time:
            del self._pending_confirmations[user_id]
            print(f"⏰ Confirmación de rutina expirada para usuario: {user_id}")
            return None
        
        return pending
    
    def has_pending_confirmation(self, user_id: str) -> bool:
        """
        Verifica si hay una confirmación pendiente válida
        """
        return self.get_pending_confirmation(user_id) is not None
    
    def clear_pending_confirmation(self, user_id: str):
        """
        Elimina una confirmación pendiente
        """
        if user_id in self._pending_confirmations:
            del self._pending_confirmations[user_id]
            print(f"🗑️ Confirmación de rutina eliminada para usuario: {user_id}")
    
    # TODO Agregar confirmaciones en portuges/ingles 
    def is_confirmation_response(self, message: str) -> Optional[bool]:
        """
        Detecta si un mensaje es una respuesta de confirmación
        Retorna True (sí), False (no), o None (no es una respuesta de confirmación)
        """
        message_lower = message.lower().strip()
        
        # Respuestas afirmativas
        positive_responses = [
            "sí", "si", "yes", "ok", "vale", "perfecto", "correcto",
            "está bien", "esta bien", "acepto", "confirmo", "claro",
            "por supuesto", "guardalo", "guárdalo", "guardala", "guárdala",
            "👍", "✅", "dale", "bueno",
            "claro que sí", "hazlo", "hazlo por favor", "por favor"
        ]
        
        # Respuestas negativas
        negative_responses = [
            "no", "nope", "cancel", "cancelar", "no gracias",
            "no está bien", "no esta bien", "incorrecto", "no me parece",
            "👎", "❌", "rechazar", "no quiero", "mejor no"
        ]
        
        # Verificar respuestas exactas
        if message_lower in positive_responses:
            return True
        if message_lower in negative_responses:
            return False
        
        # Verificar frases más largas que contienen confirmación clara
        if len(message_lower) <= 25:  # Mensajes cortos para evitar falsos positivos
            for pos in positive_responses:
                # Más flexible con separadores (espacio, coma, punto)
                if (message_lower == pos or 
                    message_lower.startswith(pos + " ") or 
                    message_lower.startswith(pos + ",") or
                    message_lower.startswith(pos + ".") or
                    message_lower.endswith(" " + pos) or
                    message_lower.endswith("," + pos) or
                    message_lower.endswith("." + pos)):
                    return True
            for neg in negative_responses:
                if (message_lower == neg or 
                    message_lower.startswith(neg + " ") or 
                    message_lower.startswith(neg + ",") or
                    message_lower.endswith(" " + neg)):
                    return False
        
        # No es una respuesta de confirmación clara
        return None

# Instancia global del cache
routine_confirmation_cache = RoutineConfirmationCache()