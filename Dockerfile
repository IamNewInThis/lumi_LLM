FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# define el directorio de trabajo dentro del contenedor
WORKDIR /src

# dependencias del sistema
RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*

# primero dependencias para cache
COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# copia el resto del código
COPY . .

# usuario no-root
RUN useradd -m appuser && chown -R appuser /src
USER appuser

# Para desarrollo local usamos puerto 8000, para producción usar variable PORT
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
