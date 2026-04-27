# Scripts de Inicio

Scripts para correr el sistema completo (Backend + Frontend) de forma sencilla.

## 📋 Requisitos previos

```bash
# Crear virtual environment (solo primera vez)
python3 -m venv .venv

# Instalar dependencias Python
.venv/bin/pip install -r requirements.txt

# Instalar dependencias Node (solo primera vez)
cd dashboard && npm install && cd ..

# Copiar variables de entorno
cp .env.example .env
# Editar .env con tus claves API
```

---

## 🚀 Opción 1: `start.sh` (Producción)

Script completo con logs separados, validaciones y limpieza automática.

```bash
./start.sh
```

**Características:**
- ✅ Verifica virtual env y node_modules
- ✅ Guarda logs en `logs/backend.log` y `logs/frontend.log`
- ✅ Espera a que Backend esté listo antes de iniciar Frontend
- ✅ Limpia procesos automáticamente con Ctrl+C
- ✅ Output formateado con colores

**URLs:**
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- Docs API: http://localhost:8000/docs

---

## 🏃 Opción 2: `dev.sh` (Desarrollo)

Script simple que muestra todo en la terminal. Ideal para debugging.

```bash
./dev.sh
```

**Características:**
- ✅ Más simple y rápido
- ✅ Todo el output en tu terminal
- ✅ Perfecto para ver errores en tiempo real

---

## 🛠️ Comandos manuales (si prefieres)

**Terminal 1 - Backend:**
```bash
.venv/bin/uvicorn api.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd dashboard && npm run dev
```

---

## 📝 Logs

Los logs se guardan en:
- `logs/backend.log` — Salida del servidor FastAPI
- `logs/frontend.log` — Salida del servidor Next.js

Úsalos para debugging cuando uses `start.sh`.

---

## 🐛 Troubleshooting

**"Virtual environment no encontrado"**
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

**"Dependencias de Node no encontradas"**
```bash
cd dashboard && npm install && cd ..
```

**"Puerto ya está en uso"**
```bash
# Cambiar puerto en el script o:
lsof -i :8000  # Ver qué usa el puerto
kill -9 <PID>  # Matar el proceso
```

**Backend no responde**
```bash
curl http://localhost:8000/api/health
```

---

## 📊 Estructura de carpetas

```
agente_contenido/
├── .venv/                 # Virtual env (generado)
├── api/                   # Backend FastAPI
├── dashboard/             # Frontend Next.js
├── pipelines/             # Pipelines de contenido
├── skills/                # Skills/tareas atómicas
├── start.sh              # Script de producción
├── dev.sh                # Script de desarrollo
└── logs/                 # Logs (generado por start.sh)
```

---

## 🎯 Flujo típico de desarrollo

1. Editar código (backend/frontend)
2. Los servidores recargan automáticamente (`--reload` en FastAPI, hot-reload en Next.js)
3. Ver cambios en http://localhost:3000
4. Los errores aparecen en terminal o logs/

---

## ⚠️ Notas importantes

- **Backend debe estar listo** antes de que Frontend intente conectar
- Ambos servidores usan `--reload`, así que los cambios en código se aplican automáticamente
- Si cambias `.env`, necesitas reiniciar los servidores
- Asegúrate de tener `OPENAI_API_KEY`, `ELEVENLABS_API_KEY` configuradas en `.env`
