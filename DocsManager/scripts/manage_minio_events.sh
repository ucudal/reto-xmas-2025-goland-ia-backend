#!/bin/bash
# Script para gestionar eventos de MinIO (listar, eliminar, limpiar)

set -e  # Salir si hay algún error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_info() {
    echo -e "${GREEN}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Verificar que mc esté instalado
if ! command -v mc &> /dev/null; then
    print_error "MinIO Client (mc) no está instalado."
    echo "Por favor instala mc:"
    echo "  macOS: brew install minio/stable/mc"
    echo "  Linux: wget https://dl.min.io/client/mc/release/linux-amd64/mc && chmod +x mc && sudo mv mc /usr/local/bin/"
    exit 1
fi

# Cargar variables de entorno desde .env si existe
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Configuración por defecto
MINIO_ENDPOINT="${MINIO_ENDPOINT:-localhost:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-${MINIO_ROOT_USER:-minioadmin}}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-${MINIO_ROOT_PASSWORD:-minioadmin}}"
MINIO_BUCKET="${MINIO_BUCKET:-goland-bucket}"
MINIO_USE_SSL="${MINIO_USE_SSL:-false}"

# Determinar el protocolo para MinIO
if [ "$MINIO_USE_SSL" = "true" ] || [ "$MINIO_USE_SSL" = "True" ] || [ "$MINIO_USE_SSL" = "1" ]; then
    MINIO_PROTOCOL="https"
else
    MINIO_PROTOCOL="http"
fi

MINIO_URL="${MINIO_PROTOCOL}://${MINIO_ENDPOINT}"
ALIAS_NAME="myminio"

# Función para listar eventos
list_events() {
    print_header "Eventos Configurados en ${MINIO_BUCKET}"
    
    if mc event list "${ALIAS_NAME}/${MINIO_BUCKET}" 2>/dev/null; then
        echo ""
        print_success "Eventos listados correctamente"
    else
        print_warning "No se encontraron eventos o hubo un error al listarlos"
    fi
}

# Función para eliminar un evento específico
remove_event() {
    local arn="${1:-arn:minio:sqs::1:amqp}"
    
    print_header "Eliminando Evento: ${arn}"
    
    # Usar --force para eliminar todos los eventos del bucket
    print_info "Eliminando todos los eventos del bucket con --force..."
    if mc event rm "${ALIAS_NAME}/${MINIO_BUCKET}" --force 2>/dev/null; then
        print_success "Todos los eventos eliminados"
        return 0
    fi
    
    print_warning "No se pudieron eliminar los eventos con --force"
    return 1
}

# Función para limpiar todos los eventos
clean_all_events() {
    print_header "Limpiando Todos los Eventos"
    
    # Primero listar eventos
    print_info "Eventos actuales:"
    mc event list "${ALIAS_NAME}/${MINIO_BUCKET}" 2>/dev/null || true
    echo ""
    
    # Intentar eliminar todos los eventos con --force
    print_info "Eliminando todos los eventos..."
    if mc event rm "${ALIAS_NAME}/${MINIO_BUCKET}" --force 2>/dev/null; then
        print_success "Todos los eventos eliminados"
        return 0
    fi
    
    print_warning "No se pudieron eliminar los eventos con --force"
    return 1
}

# Función para deshabilitar AMQP completamente
disable_amqp() {
    print_header "Deshabilitando Configuración AMQP"
    
    print_info "Deshabilitando notify_amqp:1..."
    if mc admin config set "${ALIAS_NAME}" notify_amqp:1 enable=off 2>/dev/null; then
        print_success "Configuración AMQP deshabilitada"
        
        print_info "Reiniciando MinIO para aplicar cambios..."
        if mc admin service restart "${ALIAS_NAME}" 2>/dev/null; then
            print_success "MinIO reiniciado"
            
            print_info "Esperando 5 segundos para que MinIO se reinicie..."
            sleep 5
            
            # Verificar que MinIO está disponible
            if mc admin info "${ALIAS_NAME}" &> /dev/null; then
                print_success "MinIO está disponible después del reinicio"
                
                # Verificar eventos
                print_info "Verificando eventos después del reinicio..."
                if ! mc event list "${ALIAS_NAME}/${MINIO_BUCKET}" 2>/dev/null | grep -q "arn:"; then
                    print_success "Todos los eventos fueron eliminados"
                    return 0
                else
                    print_warning "Aún hay eventos configurados"
                    return 1
                fi
            else
                print_error "MinIO no está disponible después del reinicio"
                return 1
            fi
        else
            print_error "No se pudo reiniciar MinIO"
            return 1
        fi
    else
        print_error "No se pudo deshabilitar la configuración AMQP"
        return 1
    fi
}

# Función para mostrar la configuración AMQP
show_amqp_config() {
    print_header "Configuración AMQP Actual"
    
    print_info "Configuración notify_amqp:1:"
    mc admin config get "${ALIAS_NAME}" notify_amqp:1 2>/dev/null || print_warning "No se pudo obtener la configuración"
    echo ""
}

# Función principal
main() {
    local command="${1:-list}"
    
    # Configurar alias si no existe
    if ! mc alias list | grep -q "${ALIAS_NAME}"; then
        print_info "Configurando alias de MinIO..."
        mc alias set "${ALIAS_NAME}" "${MINIO_URL}" "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}" 2>/dev/null || {
            print_error "No se pudo configurar el alias. Verifica las credenciales."
            exit 1
        }
    fi
    
    case "$command" in
        list)
            list_events
            ;;
        remove)
            local arn="${2:-arn:minio:sqs::1:amqp}"
            if remove_event "$arn"; then
                print_success "Evento eliminado exitosamente"
            else
                print_warning "No se pudo eliminar el evento. Intentando deshabilitar AMQP..."
                disable_amqp
            fi
            ;;
        clean)
            if clean_all_events; then
                print_success "Todos los eventos eliminados"
            else
                print_warning "No se pudieron eliminar los eventos. Intentando deshabilitar AMQP..."
                disable_amqp
            fi
            ;;
        disable)
            disable_amqp
            ;;
        config)
            show_amqp_config
            list_events
            ;;
        *)
            echo "Uso: $0 {list|remove [arn]|clean|disable|config}"
            echo ""
            echo "Comandos:"
            echo "  list      - Listar eventos configurados"
            echo "  remove    - Eliminar un evento específico (por defecto: arn:minio:sqs::1:amqp)"
            echo "  clean     - Eliminar todos los eventos del bucket"
            echo "  disable   - Deshabilitar completamente AMQP y reiniciar MinIO"
            echo "  config    - Mostrar configuración AMQP y eventos"
            echo ""
            echo "Ejemplos:"
            echo "  $0 list"
            echo "  $0 remove"
            echo "  $0 remove 'arn:minio:sqs::1:amqp'"
            echo "  $0 clean"
            echo "  $0 disable"
            exit 1
            ;;
    esac
}

# Ejecutar función principal
main "$@"

