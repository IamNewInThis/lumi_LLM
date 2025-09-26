from typing import Dict, List, Optional
from ..rag.retriever import supabase

class BabyKnowledgeService:
    """
    Servicio para gestionar el conocimiento específico sobre cada bebé
    """
    
    @staticmethod
    async def save_knowledge(user_id: str, baby_id: str, knowledge_data: Dict) -> Dict:
        """
        Guarda un elemento de conocimiento sobre un bebé
        
        Args:
            user_id: ID del usuario
            baby_id: ID del bebé
            knowledge_data: Diccionario con:
                - category: str
                - subcategory: str (opcional)
                - title: str
                - description: str
                - importance_level: int (1-5)
        """
        try:
            # Verificar que el bebé pertenece al usuario
            baby_check = supabase.table("babies")\
                .select("id")\
                .eq("id", baby_id)\
                .eq("user_id", user_id)\
                .execute()
            
            if not baby_check.data:
                raise ValueError("El bebé no pertenece al usuario")
            
            # Preparar datos para inserción
            insert_data = {
                "user_id": user_id,
                "baby_id": baby_id,
                "category": knowledge_data["category"],
                "subcategory": knowledge_data.get("subcategory"),
                "title": knowledge_data["title"],
                "description": knowledge_data["description"],
                "importance_level": knowledge_data.get("importance_level", 1)
            }
            
            result = supabase.table("baby_knowledge").insert(insert_data).execute()
            
            if result.data:
                return result.data[0]
            else:
                raise Exception("No se pudo guardar el conocimiento")
                
        except Exception as e:
            print(f"Error guardando conocimiento: {e}")
            raise e

    @staticmethod
    async def get_baby_knowledge(user_id: str, baby_id: str, category: str = None) -> List[Dict]:
        """
        Recupera conocimiento sobre un bebé específico
        
        Args:
            user_id: ID del usuario
            baby_id: ID del bebé
            category: Categoría específica (opcional)
        """
        try:
            query = supabase.table("baby_knowledge")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("baby_id", baby_id)\
                .eq("is_active", True)\
                .order("importance_level", desc=True)\
                .order("created_at", desc=True)
            
            if category:
                query = query.eq("category", category)
            
            result = query.execute()
            return result.data or []
            
        except Exception as e:
            print(f"Error recuperando conocimiento: {e}")
            return []

    @staticmethod
    async def get_all_user_knowledge(user_id: str) -> Dict[str, List[Dict]]:
        """
        Recupera todo el conocimiento de todos los bebés de un usuario
        organizado por baby_id
        """
        try:
            result = supabase.table("baby_knowledge")\
                .select("*, babies!inner(name)")\
                .eq("user_id", user_id)\
                .eq("is_active", True)\
                .order("importance_level", desc=True)\
                .execute()
            
            knowledge_by_baby = {}
            for item in result.data or []:
                baby_id = item["baby_id"]
                if baby_id not in knowledge_by_baby:
                    knowledge_by_baby[baby_id] = {
                        "baby_name": item["babies"]["name"],
                        "knowledge": []
                    }
                knowledge_by_baby[baby_id]["knowledge"].append(item)
            
            return knowledge_by_baby
            
        except Exception as e:
            print(f"Error recuperando conocimiento del usuario: {e}")
            return {}

    @staticmethod
    async def update_knowledge(user_id: str, knowledge_id: str, updates: Dict) -> Dict:
        """
        Actualiza un elemento de conocimiento existente
        """
        try:
            # Verificar propiedad
            check = supabase.table("baby_knowledge")\
                .select("id")\
                .eq("id", knowledge_id)\
                .eq("user_id", user_id)\
                .execute()
            
            if not check.data:
                raise ValueError("El conocimiento no existe o no pertenece al usuario")
            
            result = supabase.table("baby_knowledge")\
                .update(updates)\
                .eq("id", knowledge_id)\
                .eq("user_id", user_id)\
                .execute()
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            print(f"Error actualizando conocimiento: {e}")
            raise e

    @staticmethod
    async def deactivate_knowledge(user_id: str, knowledge_id: str) -> bool:
        """
        Desactiva un elemento de conocimiento (borrado lógico)
        """
        try:
            result = supabase.table("baby_knowledge")\
                .update({"is_active": False})\
                .eq("id", knowledge_id)\
                .eq("user_id", user_id)\
                .execute()
            
            return bool(result.data)
            
        except Exception as e:
            print(f"Error desactivando conocimiento: {e}")
            return False

    @staticmethod
    def format_knowledge_for_context(knowledge_by_baby: Dict[str, List[Dict]]) -> str:
        """
        Formatea el conocimiento para incluir en el contexto del sistema
        """
        if not knowledge_by_baby:
            return ""
        
        context_parts = []
        
        for baby_id, baby_info in knowledge_by_baby.items():
            baby_name = baby_info["baby_name"]
            knowledge_items = baby_info["knowledge"]
            
            if not knowledge_items:
                continue
                
            baby_context = [f"\n🧠 CONOCIMIENTO ESPECÍFICO DE {baby_name.upper()}:"]
            
            # Agrupar por categoría
            by_category = {}
            for item in knowledge_items:
                category = item["category"]
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(item)
            
            # Formatear por categoría con iconos
            category_icons = {
                "alergias": "🚨",
                "alimentacion": "🍽️", 
                "juguetes": "🧸",
                "comportamiento": "😊",
                "salud": "🏥",
                "rutinas": "⏰",
                "desarrollo": "📈"
            }
            
            for category, items in by_category.items():
                icon = category_icons.get(category, "📝")
                baby_context.append(f"{icon} {category.upper()}:")
                
                for item in items:
                    importance = "⭐" * item["importance_level"]
                    baby_context.append(f"   • {item['title']} {importance}")
                    if item["description"] != item["title"]:
                        baby_context.append(f"     └─ {item['description']}")
            
            context_parts.append("\n".join(baby_context))
        
        return "\n".join(context_parts)

    @staticmethod
    async def find_baby_by_name(user_id: str, baby_name: str) -> Optional[str]:
        """
        Busca el ID de un bebé por su nombre (para asociar conocimiento detectado)
        """
        try:
            result = supabase.table("babies")\
                .select("id")\
                .eq("user_id", user_id)\
                .ilike("name", f"%{baby_name}%")\
                .execute()
            
            if result.data:
                return result.data[0]["id"]
            
            # Si no encuentra por nombre exacto, buscar el primero (caso "el bebé")
            if baby_name.lower() in ["el bebé", "el bebe", "mi bebé", "mi bebe", "el niño", "la niña"]:
                all_babies = supabase.table("babies")\
                    .select("id")\
                    .eq("user_id", user_id)\
                    .limit(1)\
                    .execute()
                
                if all_babies.data:
                    return all_babies.data[0]["id"]
            
            return None
            
        except Exception as e:
            print(f"Error buscando bebé: {e}")
            return None