# src/utils/source_cache.py
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import threading

class SourceCache:
    """
    Cache para almacenar los documentos fuente utilizados en las respuestas más recientes.
    Permite responder preguntas de seguimiento sobre referencias basándose en la última consulta.
    """
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._expiry_minutes = 30  # Cache expira en 30 minutos
    
    def store_sources(self, user_id: str, sources: List[str], query: str, search_id: str = "main") -> None:
        """
        Almacena los documentos fuente utilizados en una respuesta.
        
        Args:
            user_id: ID del usuario
            sources: Lista de documentos consultados (ej: ['child_of_mine_feeding.pdf'])
            query: La consulta original del usuario
            search_id: Identificador del tipo de búsqueda
        """
        with self._lock:
            # Check if overwriting existing cache
            if user_id in self._cache:
                existing_data = self._cache[user_id]
                print(f"⚠️ [SOURCE-CACHE] SOBRESCRIBIENDO cache existente para usuario {user_id[:8]}...")
                print(f"⚠️ [SOURCE-CACHE] Cache anterior: {existing_data['sources']}")
                print(f"⚠️ [SOURCE-CACHE] Consulta anterior: '{existing_data['original_query']}'")
                print(f"⚠️ [SOURCE-CACHE] Cache nuevo: {sources}")
                print(f"⚠️ [SOURCE-CACHE] Consulta nueva: '{query}'")
            
            self._cache[user_id] = {
                "sources": sources,
                "original_query": query,
                "search_id": search_id,
                "timestamp": datetime.now(),
                "processed_sources": self._process_sources_for_references(sources)
            }
            
        print(f"💾 [SOURCE-CACHE] Guardados {len(sources)} documentos para usuario {user_id[:8]}...")
        print(f"💾 [SOURCE-CACHE] Documentos: {sources}")
        print(f"💾 [SOURCE-CACHE] Consulta: '{query[:50]}{'...' if len(query) > 50 else ''}')")
    
    def get_sources(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene los documentos fuente de la última consulta del usuario.
        
        Returns:
            Dict con sources, original_query, timestamp, etc. o None si no existe/expiró
        """
        with self._lock:
            if user_id not in self._cache:
                return None
            
            cached_data = self._cache[user_id]
            
            # Verificar si el cache expiró
            if datetime.now() - cached_data["timestamp"] > timedelta(minutes=self._expiry_minutes):
                del self._cache[user_id]
                print(f"⏰ [SOURCE-CACHE] Cache expirado para usuario {user_id[:8]}...")
                return None
            
            return cached_data
    
    def _process_sources_for_references(self, sources: List[str]) -> Dict[str, str]:
        """
        Procesa los nombres de archivos para crear mejores queries de búsqueda de referencias.
        
        Args:
            sources: Lista de archivos fuente
            
        Returns:
            Dict con mapping de archivo_referencia -> query de referencia optimizada
        """
        processed = {}
        
        for source in sources:
            # Crear el nombre del archivo de referencias
            if source.endswith('.pdf'):
                # Si el archivo ya es un archivo de referencias, usarlo tal como está
                if source.endswith('_ref.pdf'):
                    ref_file = source
                else:
                    # Mapear archivo de contenido a archivo de referencias
                    base_name = source.replace('.pdf', '')
                    ref_file = f"{base_name}_ref.pdf"
            else:
                ref_file = f"{source}_ref.pdf"
            
            # Crear query de búsqueda basada en el nombre del archivo original
            base_name = source.replace('.pdf', '').replace('_ref', '').replace('_', ' ').lower()
            
            # Mapeo específico para mejorar búsquedas de referencias
            reference_mapping = {
                'ae': 'alimentación complementaria introducción sólidos referencias estudios',
                'child of mine feeding': 'alimentación complementaria lactancia referencias estudios',
                'el cerebro del nino': 'neurociencia desarrollo cerebral infantil investigaciones',
                'el cerebro del niño': 'neurociencia desarrollo cerebral infantil investigaciones',
                'disciplina sin lagrimas': 'disciplina positiva límites referencias estudios',
                'simplicity parenting': 'simplicidad crianza sobrestimulación referencias',
                'emociones': 'desarrollo emocional autorregulación estudios',
                'libertad': 'movimiento libre autonomía pikler referencias',
                'rutina del bebe': 'rutinas horarios estructura referencias',
                'rutina del bebé': 'rutinas horarios estructura referencias',
                'acompanar despertares': 'sueño infantil despertares nocturnos referencias',
                'acompañar despertares': 'sueño infantil despertares nocturnos referencias',
                'destete nocturno': 'destete nocturno lactancia referencias',
                'destete lumi': 'destete lactancia referencias estudios',
                'viajes con niños': 'viajes familia niños referencias',
                'toxic twenty': 'químicos tóxicos bebés referencias estudios'
            }
            
            # Usar mapeo específico o crear query genérica
            if base_name in reference_mapping:
                processed[ref_file] = reference_mapping[base_name]
            else:
                # Query genérica basada en el nombre del archivo
                processed[ref_file] = f"{base_name} referencias estudios investigaciones"
            
            print(f"🗂️ [SOURCE-MAPPING] {source} → {ref_file} (query: '{processed[ref_file]}')")
        
        return processed
    
    def clear_cache(self, user_id: str) -> None:
        """Limpia el cache para un usuario específico."""
        with self._lock:
            if user_id in self._cache:
                del self._cache[user_id]
                print(f"🗑️ [SOURCE-CACHE] Cache limpiado para usuario {user_id[:8]}...")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del cache para debugging."""
        with self._lock:
            active_entries = len(self._cache)
            total_sources = sum(len(data["sources"]) for data in self._cache.values())
            
            return {
                "active_entries": active_entries,
                "total_sources": total_sources,
                "cache_size": len(self._cache)
            }

# Instancia global del cache
source_cache = SourceCache()