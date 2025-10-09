# Sistema de Base de Conocimiento Estructurada - Lumi

## Estructura de Fichas JSON

Cada ficha contiene información específica organizada para recuperación eficiente y adaptación contextual.

### Esquema de Ficha:

```json
{
  "id": "string_unico",
  "tema": "categoria_principal",
  "subtema": "especializacion",
  "edad_rango": {
    "min_meses": 0,
    "max_meses": 24,
    "descripcion": "0-2 años"
  },
  "keywords": ["palabra1", "palabra2", "palabra3"],
  "señales": [
    "Señal observable 1",
    "Señal observable 2"
  ],
  "acciones": [
    {
      "accion": "Descripción de la acción",
      "cuando": "Momento específico para aplicarla",
      "duracion": "Tiempo estimado"
    }
  ],
  "frases_sugeridas": [
    "Frase empática para validar emoción",
    "Frase para explicar la situación",
    "Frase para proponer acción"
  ],
  "validaciones": [
    "Qué verificar antes de aplicar",
    "Señales de que está funcionando"
  ],
  "referencias": ["documento1.pdf", "documento2.pdf"],
  "tags_semanticos": ["desarrollo", "sueño", "emocional"]
}
```

## Categorías Principales:

1. **sueño_descanso**
2. **alimentacion_lactancia** 
3. **desarrollo_emocional**
4. **rutinas_estructura**
5. **cuidados_diarios**
6. **autonomia_desarrollo**

## Uso del Sistema:

1. **Recuperación por contexto**: El sistema identifica edad, tema y situación específica
2. **Inyección selectiva**: Solo se incluyen los puntos relevantes al contexto actual
3. **Adaptación tonal**: Las frases se adaptan al tono definido en style_manifest
4. **Validación automática**: Se incluyen checkpoints para verificar aplicabilidad

## Ventajas:

- Respuestas más precisas y contextualizadas
- Menor carga en el prompt principal
- Fácil mantenimiento y actualización
- Escalabilidad para nuevos temas
- Consistencia en el tono y enfoque