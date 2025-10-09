"""
Servicio integrado de Base de Conocimiento para Lumi
Combina el retriever estructurado con el RAG existente
"""

import os
from typing import List, Dict, Any, Optional
from .retriever import KnowledgeRetriever, crear_contexto_para_prompt, ConsultaContexto


class LumiKnowledgeService:
    """Servicio principal que combina fichas estructuradas con RAG tradicional"""
    
    def __init__(self, knowledge_base_path: str, style_manifest_path: str):
        self.retriever = KnowledgeRetriever(knowledge_base_path)
        self.style_manifest = self._cargar_style_manifest(style_manifest_path)
        
        # Mapeo de temas para categorización automática
        self.tema_keywords = {
            'sueño_descanso': ['sueño', 'dormir', 'siesta', 'despertar', 'vigilia', 'rutina nocturna'],
            'alimentacion_lactancia': ['comer', 'lactancia', 'destete', 'pecho', 'biberon', 'alimentación'],
            'desarrollo_emocional': ['berrinche', 'llanto', 'emociones', 'límites', 'comportamiento'],
            'rutinas_estructura': ['rutina', 'horario', 'estructura', 'organización'],
            'cuidados_diarios': ['higiene', 'baño', 'dental', 'cuidado', 'salud'],
            'autonomia_desarrollo': ['autonomía', 'independencia', 'desarrollo', 'habilidades']
        }
    
    def _cargar_style_manifest(self, path: str) -> str:
        """Carga el manifiesto de estilo"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return "Tono empático y profesional"
    
    def detectar_tema_principal(self, consulta: str) -> Optional[str]:
        """Detecta el tema principal de la consulta"""
        consulta_lower = consulta.lower()
        
        for tema, keywords in self.tema_keywords.items():
            for keyword in keywords:
                if keyword in consulta_lower:
                    return tema
        
        return None
    
    def obtener_conocimiento_contextual(self, consulta: str, edad_meses: Optional[int] = None) -> str:
        """Obtiene conocimiento contextual específico para la consulta"""
        
        # Detectar tema si no se especifica
        tema_detectado = self.detectar_tema_principal(consulta)
        
        # Crear contexto de consulta
        contexto = ConsultaContexto(
            edad_meses=edad_meses or self.retriever.detectar_edad(consulta),
            tema_principal=tema_detectado,
            keywords_detectadas=self.retriever.detectar_keywords(consulta),
            situacion_descrita=consulta
        )
        
        # Recuperar puntos relevantes
        puntos_extraidos = []
        fichas_relevantes = self.retriever.recuperar_fichas_relevantes(contexto, max_fichas=2)
        
        for ficha in fichas_relevantes:
            puntos = self.retriever.extraer_puntos_relevantes(ficha, contexto)
            puntos_extraidos.append(puntos)
        
        # Crear contexto para prompt
        if puntos_extraidos:
            return crear_contexto_para_prompt(puntos_extraidos, self.style_manifest)
        
        return ""
    
    def enriquecer_respuesta(self, consulta: str, respuesta_base: str, edad_meses: Optional[int] = None) -> str:
        """Enriquece una respuesta base con conocimiento contextual específico"""
        
        conocimiento_contextual = self.obtener_conocimiento_contextual(consulta, edad_meses)
        
        if conocimiento_contextual:
            return f"""
{conocimiento_contextual}

### Respuesta Base:
{respuesta_base}

**Instrucción Final:** Integra el conocimiento específico con la respuesta base, manteniendo el tono empático y validando emociones primero.
"""
        
        return respuesta_base
    
    def obtener_frases_contextuales(self, consulta: str, edad_meses: Optional[int] = None) -> List[str]:
        """Obtiene frases específicas para el contexto de la consulta"""
        
        tema_detectado = self.detectar_tema_principal(consulta)
        contexto = ConsultaContexto(
            edad_meses=edad_meses or self.retriever.detectar_edad(consulta),
            tema_principal=tema_detectado,
            keywords_detectadas=self.retriever.detectar_keywords(consulta),
            situacion_descrita=consulta
        )
        
        fichas_relevantes = self.retriever.recuperar_fichas_relevantes(contexto, max_fichas=1)
        
        frases = []
        for ficha in fichas_relevantes:
            frases.extend(ficha.get('frases_sugeridas', []))
        
        return frases[:3]  # Limitar a 3 frases más relevantes
    
    def validar_edad_aplicable(self, edad_meses: int, ficha_id: str) -> bool:
        """Valida si una edad específica es aplicable para una ficha"""
        if ficha_id in self.retriever.fichas:
            ficha = self.retriever.fichas[ficha_id]
            return self.retriever.edad_en_rango(edad_meses, ficha['edad_rango'])
        return False
    
    def listar_temas_disponibles(self) -> List[str]:
        """Lista todos los temas disponibles en la base de conocimiento"""
        return list(self.tema_keywords.keys())
    
    def obtener_fichas_por_tema(self, tema: str) -> List[Dict]:
        """Obtiene todas las fichas de un tema específico"""
        if tema in self.retriever.indice_temas:
            fichas = []
            for ficha_id in self.retriever.indice_temas[tema]:
                fichas.append(self.retriever.fichas[ficha_id])
            return fichas
        return []


# Instancia global del servicio (se inicializa en main.py)
knowledge_service: Optional[LumiKnowledgeService] = None


def get_knowledge_service() -> LumiKnowledgeService:
    """Obtiene la instancia global del servicio de conocimiento"""
    global knowledge_service
    if knowledge_service is None:
        raise RuntimeError("KnowledgeService no ha sido inicializado")
    return knowledge_service


def initialize_knowledge_service(knowledge_base_path: str, style_manifest_path: str):
    """Inicializa el servicio global de conocimiento"""
    global knowledge_service
    knowledge_service = LumiKnowledgeService(knowledge_base_path, style_manifest_path)