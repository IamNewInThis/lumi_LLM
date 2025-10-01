#src/services/routine_service.py
from typing import List, Dict, Any, Optional
from ..rag.retriever import supabase

class RoutineService:
    
    @staticmethod
    async def save_routine(user_id: str, baby_id: str, routine_data: Dict) -> Dict:
        """
        Guarda una nueva rutina en la estructura normalizada: baby_routines + routine_activities
        """
        try:
            # 1. PREPARAR datos de la rutina principal
            routine_insert = {
                "user_id": user_id,
                "baby_id": baby_id,
                "name": routine_data.get("routine_name", "Rutina"),
                "description": routine_data.get("context_summary", ""),
                "category": routine_data.get("routine_type", "daily"),
                "confidence_score": routine_data.get("confidence", 0.7),
                "detected_from_message": routine_data.get("detected_from_message", ""),
                "approved_at": "NOW()"  # Se aprueba inmediatamente al guardar
            }
            
            # 2. INSERTAR rutina principal en baby_routines
            routine_result = supabase.table("baby_routines").insert(routine_insert).execute()
            
            if not routine_result.data:
                raise Exception("Error insertando rutina principal")
                
            routine_id = routine_result.data[0]["id"]
            print(f"✅ Rutina principal creada con ID: {routine_id}")
            
            # 3. INSERTAR actividades en routine_activities
            activities = routine_data.get("activities", [])
            if not activities:
                raise Exception("No hay actividades para guardar")
                
            activities_insert = []
            for i, activity in enumerate(activities):
                activities_insert.append({
                    "routine_id": routine_id,
                    "time_start": activity["time_start"],
                    "time_end": activity.get("time_end"),
                    "activity": activity["activity"],
                    "details": activity.get("details", ""),
                    "activity_type": activity.get("activity_type", "care"),
                    "order_index": activity.get("order_index", i + 1),
                    "importance_level": 1
                })
            
            # Insertar todas las actividades
            activities_result = supabase.table("routine_activities").insert(activities_insert).execute()
            
            if not activities_result.data:
                # Si falla insertar actividades, eliminar la rutina
                supabase.table("baby_routines").delete().eq("id", routine_id).execute()
                raise Exception("Error insertando actividades de rutina")
            
            print(f"✅ Guardadas {len(activities_result.data)} actividades de rutina")
            
            return {
                "success": True,
                "routine_id": routine_id,
                "activities_count": len(activities_result.data),
                "routine_name": routine_insert["name"],
                "activities": activities_result.data
            }
            
        except Exception as e:
            print(f"❌ Error en save_routine: {e}")
            raise e
    
    @staticmethod
    async def get_user_routines(user_id: str, baby_id: str = None) -> List[Dict]:
        """
        Obtiene rutinas de un usuario desde baby_routines
        """
        try:
            query = supabase.table("baby_routines").select("""
                id, user_id, baby_id, name, description, category, 
                confidence_score, detected_from_message, created_at, is_active
            """).eq("user_id", user_id).eq("is_active", True)
            
            if baby_id:
                query = query.eq("baby_id", baby_id)
            
            result = query.order("created_at", desc=True).execute()
            return result.data or []
            
        except Exception as e:
            print(f"Error obteniendo rutinas: {e}")
            return []
    
    @staticmethod
    async def get_routine_with_activities(routine_id: str) -> Optional[Dict]:
        """
        Obtiene una rutina completa con todas sus actividades
        """
        try:
            # Obtener rutina principal desde baby_routines
            routine_result = supabase.table("baby_routines").select("*").eq("id", routine_id).execute()
            
            if not routine_result.data:
                return None
                
            routine = routine_result.data[0]
            
            # Obtener actividades desde routine_activities
            activities_result = supabase.table("routine_activities").select(
                "*"
            ).eq("routine_id", routine_id).order("order_index").execute()
            
            routine["activities"] = activities_result.data or []
            return routine
            
        except Exception as e:
            print(f"Error obteniendo rutina con actividades: {e}")
            return None
    
    @staticmethod
    async def find_baby_by_name(user_id: str, baby_name: str) -> Optional[str]:
        """
        Busca el ID de un bebé por su nombre
        """
        try:
            result = supabase.table("babies").select("id").eq(
                "user_id", user_id
            ).ilike("name", f"%{baby_name}%").execute()
            
            if result.data:
                return result.data[0]["id"]
            return None
            
        except Exception as e:
            print(f"Error buscando bebé: {e}")
            return None
    
    @staticmethod
    def format_routines_for_context(routines_by_baby: Dict) -> str:
        """
        Formatea rutinas para incluir en el contexto de conversación
        Estructura: {baby_name: [routine_objects]}
        """
        if not routines_by_baby:
            return ""
            
        context = "📅 RUTINAS GUARDADAS:\n\n"
        
        for baby_name, routines in routines_by_baby.items():
            if not routines:
                continue
                
            context += f"👶 {baby_name}:\n"
            
            for routine in routines:
                routine_name = routine.get("name", "Rutina")
                category = routine.get("category", "daily")
                description = routine.get("description", "")
                
                context += f"  • {routine_name} ({category})"
                if description:
                    context += f" - {description}"
                context += "\n"
            
            context += "\n"
        
        context += "Nota: Cuando el usuario pregunte sobre rutinas, puedes referenciar estas rutinas guardadas.\n"
        return context
    
    @staticmethod
    async def get_all_user_routines(user_id: str) -> Dict[str, List[Dict]]:
        """
        Obtiene todas las rutinas organizadas por bebé desde baby_routines
        """
        try:
            # Obtener rutinas con información del bebé
            result = supabase.table("baby_routines").select("""
                id, name, category, description, is_active, created_at,
                babies!baby_id (name)
            """).eq("user_id", user_id).eq("is_active", True).execute()
            
            routines_by_baby = {}
            
            for routine in result.data or []:
                baby_name = routine.get("babies", {}).get("name", "Bebé")
                
                if baby_name not in routines_by_baby:
                    routines_by_baby[baby_name] = []
                    
                routines_by_baby[baby_name].append({
                    "id": routine["id"],
                    "name": routine["name"],
                    "category": routine["category"],
                    "description": routine.get("description", ""),
                    "created_at": routine["created_at"]
                })
            
            return routines_by_baby
            
        except Exception as e:
            print(f"Error obteniendo rutinas por bebé: {e}")
            return {}
    
    @staticmethod
    async def format_routine_as_markdown_table(routine_id: str) -> str:
        """
        Formatea una rutina como tabla markdown para mostrar al usuario
        """
        try:
            routine = await RoutineService.get_routine_with_activities(routine_id)
            
            if not routine or not routine.get("activities"):
                return ""
                
            routine_name = routine["name"]
            activities = routine["activities"]
            
            # Crear tabla markdown
            markdown = f"## {routine_name}\n\n"
            markdown += "| Hora | Actividad | Detalles |\n"
            markdown += "|------|-----------|----------|\n"
            
            for activity in activities:
                time_str = activity["time_start"]
                if activity.get("time_end"):
                    time_str += f"–{activity['time_end']}"
                    
                markdown += f"| {time_str} | {activity['activity']} | {activity.get('details', '')} |\n"
            
            return markdown
            
        except Exception as e:
            print(f"Error formateando rutina como tabla: {e}")
            return ""