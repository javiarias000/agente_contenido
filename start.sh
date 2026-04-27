#!/bin/bash

set -e

echo "🚀 Iniciando Motor de Contenido Agéntico..."
echo ""

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Trap para limpiar procesos al salir
cleanup() {
    echo ""
    echo -e "${YELLOW}⏹️  Deteniendo servidores...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    echo -e "${RED}✓ Servidores detenidos${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Verificar que exista el virtual env
if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ Virtual environment no encontrado${NC}"
    echo "Ejecuta primero: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Verificar que exista node_modules en dashboard
if [ ! -d "dashboard/node_modules" ]; then
    echo -e "${RED}❌ Dependencias de Node no encontradas${NC}"
    echo "Ejecuta primero: cd dashboard && npm install && cd .."
    exit 1
fi

# Iniciar Backend (FastAPI)
echo -e "${BLUE}📡 Iniciando Backend (FastAPI)...${NC}"
.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend iniciado (PID: $BACKEND_PID)${NC}"
echo "   URL: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo ""

# Esperar a que backend esté listo
echo -e "${YELLOW}⏳ Esperando a que Backend esté listo...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend listo${NC}"
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

# Iniciar Frontend (Next.js)
echo -e "${BLUE}🎨 Iniciando Frontend (Next.js)...${NC}"
cd dashboard
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo -e "${GREEN}✓ Frontend iniciado (PID: $FRONTEND_PID)${NC}"
echo "   URL: http://localhost:3000"
echo ""

echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Sistema listo${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo -e "Backend:  ${BLUE}http://localhost:8000${NC}"
echo -e "Frontend: ${BLUE}http://localhost:3000${NC}"
echo -e "Logs:     ${BLUE}./logs/backend.log${NC} y ${BLUE}./logs/frontend.log${NC}"
echo ""
echo -e "${YELLOW}Presiona Ctrl+C para detener${NC}"
echo ""

# Mantener el script activo
wait
