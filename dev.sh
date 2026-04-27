#!/bin/bash
# Script simple para desarrollo - muestra output en terminal

set -e

echo "🚀 Iniciando Motor de Contenido Agéntico..."
echo ""

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Cleanup al salir
cleanup() {
    echo ""
    echo -e "${YELLOW}⏹️  Deteniendo servidores...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Backend
echo -e "${BLUE}📡 Backend (puerto 8000)${NC}"
.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Frontend
echo -e "${BLUE}🎨 Frontend (puerto 3000)${NC}"
sleep 2 && cd dashboard && npm run dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}✓ Backend: http://localhost:8000${NC}"
echo -e "${GREEN}✓ Frontend: http://localhost:3000${NC}"
echo ""
echo -e "${YELLOW}Ctrl+C para detener${NC}"
echo ""

wait
