# Reto Goland IA Backend

Este proyecto contiene los servicios de backend para el Reto Goland IA.

## Estructura del Proyecto

```
reto-xmas-2025-goland-ia-backend/
├── docker-compose.yml          # Configuración de servicios (PostgreSQL, RabbitMQ, MinIO)
├── Dockerfile.pgvector         # Dockerfile para PostgreSQL con pgvector
├── init.sql                    # Script de inicialización de la base de datos
├── DocsManager/                # Servicio de gestión de documentos
└── RAGManager/                 # Servicio de RAG (Retrieval-Augmented Generation)
```

## Servicios Disponibles

### 1. PostgreSQL con pgvector
- **Puerto:** 5432
- **Usuario:** postgres
- **Contraseña:** postgres
- **Base de datos:** vectordb
- **Extensiones:** vector, uuid-ossp

### 2. RabbitMQ
- **Puerto AMQP:** 5672
- **Puerto Management UI:** 15672
- **Usuario:** guest
- **Contraseña:** guest
- **Management UI:** http://localhost:15672

### 3. MinIO (S3 Compatible)
- **Puerto API:** 9000
- **Puerto Web Console:** 9001
- **Usuario:** minioadmin
- **Contraseña:** minioadmin
- **Console:** http://localhost:9001

## Inicio Rápido

### Levantar todos los servicios

```bash
docker-compose up -d
```

### Ver logs de los servicios

```bash
# Todos los servicios
docker-compose logs -f

# Servicio específico
docker-compose logs -f postgres
docker-compose logs -f rabbitmq
docker-compose logs -f minio
```

### Verificar el estado de los servicios

```bash
docker-compose ps
```

### Detener los servicios

```bash
docker-compose down
```

### Detener y eliminar volúmenes (⚠️ esto borrará todos los datos)

```bash
docker-compose down -v
```

## Configuración de los Servicios de Python

### DocsManager

Asegúrate de actualizar las variables de entorno en `DocsManager/app/core/config.py`:

```python
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/vectordb"
MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
RABBITMQ_URL = "amqp://guest:guest@localhost:5672/"
```

### RAGManager

Asegúrate de actualizar las variables de entorno en `RAGManager/app/core/config.py`:

```python
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/vectordb"
RABBITMQ_URL = "amqp://guest:guest@localhost:5672/"
```

## Base de Datos

El script `init.sql` crea automáticamente las siguientes tablas:

### Tablas de RAG/Vector Store:
- `documents`: Metadatos de documentos subidos
- `document_chunks`: Chunks de documentos con embeddings

### Tablas de Chat:
- `chat_sessions`: Sesiones de conversación
- `chat_messages`: Mensajes del chat

## Troubleshooting

### Puerto ya en uso

Si algún puerto está en uso, puedes modificar los puertos en `docker-compose.yml`:

```yaml
ports:
  - "PUERTO_HOST:PUERTO_CONTENEDOR"
```

### Recrear contenedores desde cero

```bash
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Verificar salud de los servicios

```bash
docker-compose ps
```

Los servicios deberían mostrar "healthy" en la columna Status.

