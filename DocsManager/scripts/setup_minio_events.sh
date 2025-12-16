#!/bin/bash
# Script para configurar eventos de MinIO hacia RabbitMQ
# Este script configura MinIO para que publique eventos cuando se crean archivos
# en el bucket goland-bucket dentro de la carpeta especificada en MINIO_FOLDER

set -e  # Salir si hay algún error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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
    print_info "Cargando variables de entorno desde .env"
    export $(grep -v '^#' .env | xargs)
fi

# Configuración por defecto (pueden ser sobrescritas por variables de entorno)
MINIO_ENDPOINT_RAW="${MINIO_ENDPOINT:-localhost:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-${MINIO_ROOT_USER:-minioadmin}}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-${MINIO_ROOT_PASSWORD:-minioadmin}}"
MINIO_BUCKET="${MINIO_BUCKET:-goland-bucket}"
MINIO_FOLDER="${MINIO_FOLDER:-rag-docs}"
MINIO_USE_SSL="${MINIO_USE_SSL:-false}"

# Configuración de RabbitMQ
RABBITMQ_USER="${RABBITMQ_USER:-guest}"
RABBITMQ_PASSWORD="${RABBITMQ_PASSWORD:-guest}"
RABBITMQ_HOST="${RABBITMQ_HOST:-rabbitmq}"
RABBITMQ_PORT="${RABBITMQ_PORT:-5672}"
RABBITMQ_QUEUE_NAME="${RABBITMQ_QUEUE_NAME:-document.process}"
RABBITMQ_EXCHANGE_NAME="${RABBITMQ_EXCHANGE_NAME:-minio-events}"

# Parsear MINIO_ENDPOINT - puede venir en formato URL (http://host:port o https://host:port) o solo host:port
if [[ "$MINIO_ENDPOINT_RAW" =~ ^https?:// ]]; then
    # El endpoint ya tiene protocolo, extraerlo
    MINIO_URL="$MINIO_ENDPOINT_RAW"
    # Extraer el protocolo
    if [[ "$MINIO_ENDPOINT_RAW" =~ ^https:// ]]; then
        MINIO_PROTOCOL="https"
        # Extraer host:port removiendo https://
        MINIO_ENDPOINT="${MINIO_ENDPOINT_RAW#https://}"
    else
        MINIO_PROTOCOL="http"
        # Extraer host:port removiendo http://
        MINIO_ENDPOINT="${MINIO_ENDPOINT_RAW#http://}"
    fi
else
    # El endpoint no tiene protocolo, usar MINIO_USE_SSL para determinarlo
    MINIO_ENDPOINT="$MINIO_ENDPOINT_RAW"
    if [ "$MINIO_USE_SSL" = "true" ] || [ "$MINIO_USE_SSL" = "True" ] || [ "$MINIO_USE_SSL" = "1" ]; then
        MINIO_PROTOCOL="https"
    else
        MINIO_PROTOCOL="http"
    fi
    MINIO_URL="${MINIO_PROTOCOL}://${MINIO_ENDPOINT}"
fi

ALIAS_NAME="myminio"

print_info "Configuración:"
echo "  MinIO Endpoint: ${MINIO_URL}"
echo "  MinIO Bucket: ${MINIO_BUCKET}"
echo "  MinIO Folder: ${MINIO_FOLDER}"
echo "  RabbitMQ: ${RABBITMQ_USER}@${RABBITMQ_HOST}:${RABBITMQ_PORT}"
echo "  Queue: ${RABBITMQ_QUEUE_NAME}"
echo ""

# Configurar alias de MinIO
print_info "Configurando alias de MinIO..."
if mc alias list | grep -q "${ALIAS_NAME}"; then
    print_warning "El alias '${ALIAS_NAME}' ya existe. Eliminándolo..."
    mc alias remove "${ALIAS_NAME}" 2>/dev/null || true
fi

mc alias set "${ALIAS_NAME}" "${MINIO_URL}" "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}"

# Verificar conexión
if ! mc admin info "${ALIAS_NAME}" &> /dev/null; then
    print_error "No se pudo conectar a MinIO en ${MINIO_URL}"
    print_error "Verifica que MinIO esté corriendo y las credenciales sean correctas"
    exit 1
fi

print_info "✅ Conexión a MinIO exitosa"

# Verificar que el bucket existe
print_info "Verificando que el bucket '${MINIO_BUCKET}' existe..."
if ! mc ls "${ALIAS_NAME}/${MINIO_BUCKET}" &> /dev/null; then
    print_warning "El bucket '${MINIO_BUCKET}' no existe. Creándolo..."
    mc mb "${ALIAS_NAME}/${MINIO_BUCKET}"
    print_info "✅ Bucket '${MINIO_BUCKET}' creado"
else
    print_info "✅ Bucket '${MINIO_BUCKET}' existe"
fi

# Configurar notificación AMQP para RabbitMQ
print_info "Configurando notificación AMQP hacia RabbitMQ..."

# Construir URL de AMQP
AMQP_URL="amqp://${RABBITMQ_USER}:${RABBITMQ_PASSWORD}@${RABBITMQ_HOST}:${RABBITMQ_PORT}"

# Configurar el endpoint de notificación AMQP
mc admin config set "${ALIAS_NAME}" notify_amqp:1 \
    enable=on \
    url="${AMQP_URL}" \
    exchange="${RABBITMQ_EXCHANGE_NAME}" \
    exchange_type="direct" \
    routing_key="${RABBITMQ_QUEUE_NAME}" \
    durable="on" \
    delivery_mode=2

if [ $? -eq 0 ]; then
    print_info "✅ Configuración AMQP aplicada"
else
    print_error "❌ Error al configurar AMQP"
    exit 1
fi

# Reiniciar MinIO para aplicar cambios
print_info "Reiniciando MinIO para aplicar cambios..."
mc admin service restart "${ALIAS_NAME}"

# Esperar un poco para que MinIO se reinicie
print_info "Esperando 5 segundos para que MinIO se reinicie..."
sleep 5

# Verificar que MinIO está disponible
if ! mc admin info "${ALIAS_NAME}" &> /dev/null; then
    print_error "MinIO no está disponible después del reinicio"
    exit 1
fi

print_info "✅ MinIO reiniciado y disponible"

# Configurar eventos para el bucket
print_info "Configurando eventos para el bucket '${MINIO_BUCKET}' en la carpeta '${MINIO_FOLDER}/'..."

# Agregar evento para archivos creados en la carpeta especificada
mc event add "${ALIAS_NAME}/${MINIO_BUCKET}" \
    arn:minio:sqs::1:amqp \
    --event put \
    --prefix "${MINIO_FOLDER}/"

if [ $? -eq 0 ]; then
    print_info "✅ Evento configurado para archivos en '${MINIO_FOLDER}/'"
else
    print_error "❌ Error al configurar eventos"
    exit 1
fi

# Verificar la configuración
print_info "Verificando configuración de eventos..."
mc event list "${ALIAS_NAME}/${MINIO_BUCKET}"

echo ""
print_info "🎉 Configuración completada exitosamente!"
echo ""
echo "Resumen:"
echo "  - MinIO está configurado para publicar eventos a RabbitMQ"
echo "  - Los eventos se activarán cuando se creen archivos en: ${MINIO_BUCKET}/${MINIO_FOLDER}/"
echo "  - Los mensajes se publicarán en la cola: ${RABBITMQ_QUEUE_NAME}"
echo ""
echo "Para probar, sube un archivo a ${MINIO_BUCKET}/${MINIO_FOLDER}/ y verifica que llegue un mensaje a RabbitMQ"

