#!/bin/bash

# Script para gestionar los servicios de Docker

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para mostrar ayuda
show_help() {
    echo "Uso: ./manage.sh [comando]"
    echo ""
    echo "Comandos disponibles:"
    echo "  start       - Inicia todos los servicios"
    echo "  stop        - Detiene todos los servicios"
    echo "  restart     - Reinicia todos los servicios"
    echo "  logs        - Muestra logs de todos los servicios"
    echo "  status      - Muestra el estado de los servicios"
    echo "  clean       - Detiene y elimina todos los contenedores y volúmenes"
    echo "  rebuild     - Reconstruye las imágenes desde cero"
    echo "  help        - Muestra esta ayuda"
    echo ""
}

# Función para verificar si Docker está corriendo
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}Error: Docker no está corriendo${NC}"
        exit 1
    fi
}

# Función para iniciar servicios
start_services() {
    echo -e "${GREEN}Iniciando servicios...${NC}"
    docker-compose up -d
    echo -e "${GREEN}✓ Servicios iniciados${NC}"
    echo ""
    echo "Servicios disponibles:"
    echo "  - PostgreSQL: localhost:5432"
    echo "  - RabbitMQ AMQP: localhost:5672"
    echo "  - RabbitMQ Management: http://localhost:15672"
    echo "  - MinIO API: localhost:9000"
    echo "  - MinIO Console: http://localhost:9001"
}

# Función para detener servicios
stop_services() {
    echo -e "${YELLOW}Deteniendo servicios...${NC}"
    docker-compose down
    echo -e "${GREEN}✓ Servicios detenidos${NC}"
}

# Función para reiniciar servicios
restart_services() {
    stop_services
    start_services
}

# Función para mostrar logs
show_logs() {
    docker-compose logs -f
}

# Función para mostrar estado
show_status() {
    docker-compose ps
}

# Función para limpiar todo
clean_all() {
    echo -e "${RED}⚠️  ADVERTENCIA: Esto eliminará todos los datos de los contenedores${NC}"
    read -p "¿Estás seguro? (yes/no): " confirm
    if [ "$confirm" == "yes" ]; then
        echo -e "${YELLOW}Limpiando...${NC}"
        docker-compose down -v
        echo -e "${GREEN}✓ Limpieza completada${NC}"
    else
        echo "Operación cancelada"
    fi
}

# Función para reconstruir
rebuild() {
    echo -e "${YELLOW}Reconstruyendo imágenes...${NC}"
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d
    echo -e "${GREEN}✓ Reconstrucción completada${NC}"
}

# Main
check_docker

case "${1}" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    clean)
        clean_all
        ;;
    rebuild)
        rebuild
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Comando no reconocido: ${1}${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac

