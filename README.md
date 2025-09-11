# Lumi LLM - API de Chat con OpenAI y Perplexity

Una API REST construida con FastAPI que proporciona endpoints para interactuar con modelos de IA de OpenAI, especializada en consultas de crianza.

## 🚀 Características

- **OpenAI Integration**: Endpoint `/api/chat` para consultas con GPT-4o
- **CORS habilitado** para desarrollo
- **Dockerizado** para fácil despliegue
- **Variables de entorno** configurables

## 📋 Requisitos Previos

- Docker y Docker Compose instalados
- Cuenta de OpenAI con API key

## 🛠️ Configuración

### 1. Clonar el repositorio
```bash
git clone https://github.com/IamNewInThis/lumi_LLM.git
cd lumi_LLM
```

### 2. Configurar variables de entorno
Crea un archivo `.env` en la raíz del proyecto:

```env
# Puerto del servidor (por defecto: 8000)
PORT=8000

# OpenAI Configuration
OPENAI_API_KEY=tu_openai_api_key_aqui
OPENAI_MODEL=gpt-4o

SUPABASE_URL=supabase_url
SUPABASE_SERVICE_ROLE_KEY=supabase_service_role_key
```

**⚠️ Importante**: Reemplaza `tu_openai_api_key_aqui` con tu clave real de OpenAI.

## 🐳 Uso con Docker

### Opción 1: Docker Compose (Recomendado)

```bash
# Construir y ejecutar
docker-compose up --build

# Ejecutar en segundo plano
docker-compose up --build -d

# Ver logs
docker-compose logs -f

# Detener
docker-compose down
```

### Opción 2: Docker directamente

```bash
# Construir la imagen
sudo docker build -t lumi-llm .

# Ejecutar el contenedor
sudo docker run -t lumi-llm
docker compose up

# Reiniciar el contenedor
sudo docker restart -t lumi-llm 

# Detener el contenedor
sudo docker stop lumi-api
docker rm lumi-api

# Ver contenedores en ejecución
sudo docker ps
```

## 🌐 Uso de la API

Una vez que el contenedor esté ejecutándose, la API estará disponible en `http://localhost:8000`.

### Documentación automática
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Endpoints disponibles

#### 1. Chat con OpenAI
```bash
POST /api/chat
Content-Type: application/json

{
  "message": "¿Cómo puedo ayudar a mi hijo de 3 años a dormir mejor?",
  "profile": {
    "edad_hijo": "3 años",
    "problema": "dificultad para dormir"
  }
}
```

### Ejemplo con cURL

```bash
# OpenAI
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Mi hijo tiene rabietas constantes, ¿qué puedo hacer?",
    "profile": {"edad": "4 años"}
  }'

# Perplexity
curl -X POST "http://localhost:8000/api/chat/pplx" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "¿Es normal que un bebé de 6 meses se despierte cada 2 horas?",
    "profile": {"edad": "6 meses"}
  }'
```

## 🔧 Desarrollo

### Ejecutar localmente (sin Docker)

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servidor
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### Estructura del proyecto

```
lumi_LLM/
├── src/
│   ├── auth.py
│   ├── main.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── chat.py
│   └── routes/
│       ├── __init__.py
│       └── chat.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── README.md
└── .env  # (crear)
```

## 🚨 Solución de Problemas

### Error: "Invalid value for '--port': '${PORT}' is not a valid integer"
- **Solución**: Asegúrate de que el archivo `.env` existe y contiene `PORT=8000`

### Error: "Falta OPENAI_API_KEY en variables de entorno"
- **Solución**: Agrega tu clave de OpenAI al archivo `.env`

### El contenedor no inicia
- **Solución**: Verifica que el puerto 8000 no esté siendo usado por otra aplicación
- **Alternativa**: Cambia el puerto en `.env` y en `docker-compose.yml`

### Error de permisos en Docker
- **Solución**: En Linux/Mac, ejecuta con `sudo` si es necesario

## 📝 Notas de Producción

- Cambia `allow_origins=["*"]` en `main.py` por tu dominio específico
- Usa un proxy reverso (nginx) para SSL/TLS
- Configura variables de entorno de forma segura
- Considera usar Docker secrets para claves sensibles

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.
