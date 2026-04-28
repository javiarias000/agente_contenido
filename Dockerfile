FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY api/ api/
COPY assemble_video.py .
COPY fix_audio_and_assemble.py .
COPY skills/ skills/

# Crear directorios necesarios
RUN mkdir -p /app/outputs /app/brands /app/logs

# Exponer puertos
EXPOSE 8000

# Comando por defecto: ejecutar FastAPI
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
