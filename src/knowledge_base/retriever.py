"""
Sistema de Recuperación de Base de Conocimiento Estructurada
Permite recuperar fichas específicas basadas en contexto, edad y keywords
"""

import json
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re


@dataclass
class ConsultaContexto:
    """Contexto de la consulta del usuario"""
    edad_meses: Optional[int] = None
    tema_principal: Optional[str] = None
    keywords_detectadas: List[str] = None
    situacion_descrita: str = ""
    

class KnowledgeRetriever:
    """Retriever inteligente para fichas de conocimiento"""
    
    def __init__(self, knowledge_base_path: str):
        self.knowledge_base_path = knowledge_base_path
        self.fichas = self._cargar_fichas()
        self.indice_keywords = self._construir_indice_keywords()
        self.indice_temas = self._construir_indice_temas()
        
    def _cargar_fichas(self) -> Dict[str, Dict]:
        """Carga todas las fichas JSON del directorio"""
        fichas = {}
        
        if not os.path.exists(self.knowledge_base_path):
            return fichas
            
        for filename in os.listdir(self.knowledge_base_path):
            if filename.endswith('.json'):
                filepath = os.path.join(self.knowledge_base_path, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        ficha = json.load(f)
                        fichas[ficha['id']] = ficha
                except Exception as e:
                    print(f"Error cargando {filename}: {e}")
                    
        return fichas
    
    def _construir_indice_keywords(self) -> Dict[str, List[str]]:
        """Construye índice invertido de keywords -> fichas"""
        indice = {}
        
        for ficha_id, ficha in self.fichas.items():
            # Keywords explícitas
            for keyword in ficha.get('keywords', []):
                if keyword not in indice:
                    indice[keyword] = []
                indice[keyword].append(ficha_id)
                
            # Tags semánticos
            for tag in ficha.get('tags_semanticos', []):
                if tag not in indice:
                    indice[tag] = []
                indice[tag].append(ficha_id)
                
        return indice
    
    def _construir_indice_temas(self) -> Dict[str, List[str]]:
        """Construye índice de temas -> fichas"""
        indice = {}
        
        for ficha_id, ficha in self.fichas.items():
            tema = ficha.get('tema')
            if tema:
                if tema not in indice:
                    indice[tema] = []
                indice[tema].append(ficha_id)
                
        return indice
    
    def detectar_keywords(self, texto: str) -> List[str]:
        """Detecta keywords relevantes en el texto de consulta"""
        texto_lower = texto.lower()
        keywords_encontradas = []
        
        # Buscar keywords en todos los índices
        for keyword in self.indice_keywords.keys():
            if keyword.lower() in texto_lower:
                keywords_encontradas.append(keyword)
                
        return keywords_encontradas
    
    def detectar_edad(self, texto: str) -> Optional[int]:
        """Detecta edad en meses del texto"""
        # Patrones para detectar edad
        patrones = [
            r'(\d+)\s*meses?',
            r'(\d+)\s*años?\s*y\s*(\d+)\s*meses?',
            r'(\d+)\s*años?',
        ]
        
        for patron in patrones:
            match = re.search(patron, texto.lower())
            if match:
                if 'años' in patron and 'meses' in patron:
                    # "X años y Y meses"
                    años = int(match.group(1))
                    meses = int(match.group(2))
                    return años * 12 + meses
                elif 'años' in patron:
                    # "X años"
                    return int(match.group(1)) * 12
                else:
                    # "X meses"
                    return int(match.group(1))
                    
        return None
    
    def edad_en_rango(self, edad_meses: int, rango_edad: Dict) -> bool:
        """Verifica si la edad está en el rango de la ficha"""
        return rango_edad['min_meses'] <= edad_meses <= rango_edad['max_meses']
    
    def recuperar_fichas_relevantes(self, contexto: ConsultaContexto, max_fichas: int = 3) -> List[Dict]:
        """Recupera las fichas más relevantes para el contexto dado"""
        candidatos = {}
        
        # Buscar por keywords
        for keyword in contexto.keywords_detectadas or []:
            if keyword in self.indice_keywords:
                for ficha_id in self.indice_keywords[keyword]:
                    if ficha_id not in candidatos:
                        candidatos[ficha_id] = 0
                    candidatos[ficha_id] += 2  # Peso mayor para keywords exactas
        
        # Buscar por tema principal
        if contexto.tema_principal and contexto.tema_principal in self.indice_temas:
            for ficha_id in self.indice_temas[contexto.tema_principal]:
                if ficha_id not in candidatos:
                    candidatos[ficha_id] = 0
                candidatos[ficha_id] += 3  # Peso alto para tema principal
        
        # Filtrar por edad si está disponible
        fichas_filtradas = []
        for ficha_id, score in candidatos.items():
            ficha = self.fichas[ficha_id]
            
            # Aplicar filtro de edad
            if contexto.edad_meses:
                if not self.edad_en_rango(contexto.edad_meses, ficha['edad_rango']):
                    continue
                    
            fichas_filtradas.append((ficha, score))
        
        # Ordenar por score y retornar top N
        fichas_filtradas.sort(key=lambda x: x[1], reverse=True)
        return [ficha for ficha, _ in fichas_filtradas[:max_fichas]]
    
    def extraer_puntos_relevantes(self, ficha: Dict, contexto: ConsultaContexto) -> Dict:
        """Extrae solo los puntos relevantes de una ficha para el contexto específico"""
        puntos_relevantes = {
            'id': ficha['id'],
            'tema': ficha['tema'],
            'edad_aplicable': ficha['edad_rango']['descripcion']
        }
        
        # Siempre incluir frases sugeridas (adaptadas al tono)
        puntos_relevantes['frases_sugeridas'] = ficha.get('frases_sugeridas', [])
        
        # Incluir señales si hay keywords relacionadas con observación/síntomas
        keywords_observacion = ['señales', 'síntomas', 'comportamiento', 'observar']
        if any(kw in ' '.join(contexto.keywords_detectadas or []) for kw in keywords_observacion):
            puntos_relevantes['señales'] = ficha.get('señales', [])
        
        # Incluir acciones si se pregunta sobre qué hacer
        keywords_accion = ['qué hacer', 'cómo', 'ayuda', 'estrategia', 'método']
        if any(kw in contexto.situacion_descrita.lower() for kw in keywords_accion):
            puntos_relevantes['acciones'] = ficha.get('acciones', [])
        
        # Incluir validaciones si es una consulta sobre rutinas o cambios
        if 'rutina' in contexto.situacion_descrita.lower() or 'cambio' in contexto.situacion_descrita.lower():
            puntos_relevantes['validaciones'] = ficha.get('validaciones', [])
            
        return puntos_relevantes
    
    def consultar(self, texto_consulta: str, tema_sugerido: str = None) -> List[Dict]:
        """Método principal para consultar la base de conocimiento"""
        # Analizar contexto
        contexto = ConsultaContexto(
            edad_meses=self.detectar_edad(texto_consulta),
            tema_principal=tema_sugerido,
            keywords_detectadas=self.detectar_keywords(texto_consulta),
            situacion_descrita=texto_consulta
        )
        
        # Recuperar fichas relevantes
        fichas_relevantes = self.recuperar_fichas_relevantes(contexto)
        
        # Extraer solo puntos relevantes de cada ficha
        puntos_extraidos = []
        for ficha in fichas_relevantes:
            puntos = self.extraer_puntos_relevantes(ficha, contexto)
            puntos_extraidos.append(puntos)
            
        return puntos_extraidos


def crear_contexto_para_prompt(puntos_extraidos: List[Dict], style_manifest: str) -> str:
    """Crea el contexto estructurado para inyectar en el prompt principal"""
    if not puntos_extraidos:
        return ""
    
    contexto = "### Conocimiento Específico Aplicable:\n\n"
    
    for i, puntos in enumerate(puntos_extraidos, 1):
        contexto += f"**Ficha {i} - {puntos['tema']} ({puntos['edad_aplicable']})**\n\n"
        
        if 'frases_sugeridas' in puntos:
            contexto += "**Frases sugeridas:**\n"
            for frase in puntos['frases_sugeridas']:
                contexto += f"- {frase}\n"
            contexto += "\n"
        
        if 'señales' in puntos:
            contexto += "**Señales a observar:**\n"
            for señal in puntos['señales']:
                contexto += f"- {señal}\n"
            contexto += "\n"
            
        if 'acciones' in puntos:
            contexto += "**Acciones recomendadas:**\n"
            for accion in puntos['acciones']:
                contexto += f"- {accion['accion']} ({accion['cuando']})\n"
            contexto += "\n"
            
        if 'validaciones' in puntos:
            contexto += "**Validaciones importantes:**\n"
            for validacion in puntos['validaciones']:
                contexto += f"- {validacion}\n"
            contexto += "\n"
        
        contexto += "---\n\n"
    
    contexto += f"**Instrucción:** Adapta estos puntos al tono definido: {style_manifest}\n"
    
    return contexto