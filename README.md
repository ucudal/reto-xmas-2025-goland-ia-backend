# Reto Goland IA Backend

Este proyecto contiene los servicios de backend para el Reto Goland IA.

## Estructura del Proyecto

```text
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
- **Usuario:** Configurado en `.env` (por defecto: `postgres`)
- **Contraseña:** Configurado en `.env` (por defecto: `postgres`)
- **Base de datos:** Configurado en `.env` (por defecto: `vectordb`)
- **Extensiones:** vector, uuid-ossp

### 2. RabbitMQ

- **Puerto AMQP:** 5672
- **Puerto Management UI:** 15672
- **Usuario:** Configurado en `.env` (por defecto: `guest`)
- **Contraseña:** Configurado en `.env` (por defecto: `guest`)
- **Management UI:** <http://localhost:15672>

### 3. MinIO (S3 Compatible)

- **Puerto API:** 9000
- **Puerto Web Console:** 9001
- **Usuario:** Configurado en `.env` (por defecto: `minioadmin`)
- **Contraseña:** Configurado en `.env` (por defecto: `minioadmin`)
- **Console:** <http://localhost:9001>

## Configuración Inicial

### Variables de Entorno

El proyecto utiliza archivos `.env` en dos niveles:

1. **`.env` en el directorio raíz**: Para configurar los servicios de infraestructura (Docker Compose)
2. **`.env` en cada servicio Python** (`DocsManager/.env`, `RAGManager/.env`): Para configurar las aplicaciones

#### Configuración paso a paso:

**1. Copia el archivo de ejemplo del directorio raíz:**
```bash
cp .env.example .env
```

**2. Copia la configuración para cada servicio Python:**
```bash
# Para DocsManager
cp DocsManager/.env.example DocsManager/.env

# Para RAGManager
cp RAGManager/.env.example RAGManager/.env
```

**3. Personaliza las credenciales según tu entorno:**

**Para desarrollo local:**
- Puedes usar los valores por defecto
- Asegúrate de que en los archivos `.env` de las aplicaciones:
  - `MINIO_ENDPOINT=localhost:9000`
  - `MINIO_USE_SSL=false`
  - `RABBITMQ_HOST=localhost`
- Agrega tu clave de OpenAI: `OPENAI_API_KEY=tu-clave-aquí`

**Para producción/entornos no locales:**
- **DEBES** cambiar todas las contraseñas por valores seguros
- Configura endpoints externos (ej: `MINIO_ENDPOINT=https://minio.tudominio.com`)
- Habilita SSL: `MINIO_USE_SSL=true`
- Usa las credenciales correctas de producción

### Variables de Entorno Disponibles

El archivo `.env.example` contiene:

**Configuración de Docker Compose (servicios de infraestructura):**

**PostgreSQL:**
- `POSTGRES_USER`: Usuario de PostgreSQL (por defecto: `postgres`)
- `POSTGRES_PASSWORD`: Contraseña de PostgreSQL (por defecto: `postgres`)
- `POSTGRES_DB`: Nombre de la base de datos (por defecto: `vectordb`)
- `POSTGRES_PORT`: Puerto de PostgreSQL (por defecto: `5432`)

**RabbitMQ:**
- `RABBITMQ_USER`: Usuario de RabbitMQ (por defecto: `guest`)
- `RABBITMQ_PASSWORD`: Contraseña de RabbitMQ (por defecto: `guest`)
- `RABBITMQ_HOST`: Host de RabbitMQ (por defecto: `rabbitmq`)
- `RABBITMQ_PORT`: Puerto AMQP (por defecto: `5672`)
- `RABBITMQ_MANAGEMENT_PORT`: Puerto Management UI (por defecto: `15672`)

**MinIO (servicios Docker):**
- `MINIO_ROOT_USER`: Usuario root de MinIO (por defecto: `minioadmin`)
- `MINIO_ROOT_PASSWORD`: Contraseña root de MinIO (por defecto: `minioadmin`)

**Configuración de Aplicaciones (DocsManager/RAGManager):**

**MinIO (acceso desde aplicaciones):**
- `MINIO_ENDPOINT`: Endpoint de MinIO (por defecto: `localhost:9000`)
- `MINIO_ACCESS_KEY`: Clave de acceso (por defecto: `minioadmin`)
- `MINIO_SECRET_KEY`: Clave secreta (por defecto: `minioadmin`)
- `MINIO_BUCKET`: Nombre del bucket (por defecto: `goland-bucket`)
- `MINIO_USE_SSL`: Usar SSL (por defecto: `false` para local)

**OpenAI:**
- `OPENAI_API_KEY`: Tu clave de API de OpenAI

**Chunking:**
- `CHUNK_SIZE`: Tamaño de los chunks (por defecto: `1000`)
- `CHUNK_OVERLAP`: Solapamiento entre chunks (por defecto: `200`)

⚠️ **Importante:** 
- Los archivos `.env` NO deben ser incluidos en el control de versiones (ya están en `.gitignore`)
- Las credenciales por defecto son SOLO para desarrollo local
- En producción, usa contraseñas seguras y aleatorias

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

Cada servicio Python (DocsManager, RAGManager) tiene su propio archivo `.env.example` con las variables necesarias.

### Configuración rápida

```bash
# Para DocsManager
cp DocsManager/.env.example DocsManager/.env

# Para RAGManager
cp RAGManager/.env.example RAGManager/.env
```

Luego edita cada archivo `.env` para:
1. Agregar tu clave de OpenAI: `OPENAI_API_KEY=tu-clave-aquí`
2. Ajustar endpoints si usas servicios externos
3. Cambiar contraseñas si no usas las del desarrollo local

### Configuración manual

Si prefieres configurar manualmente, estos son los valores necesarios:

#### DocsManager/.env

```env
# PostgreSQL Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=vectordb
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# RabbitMQ Configuration
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672

# MinIO Configuration
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=goland-bucket
MINIO_USE_SSL=false

# OpenAI Configuration
OPENAI_API_KEY=tu-clave-de-openai

# Chunking Configuration
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

#### RAGManager/.env

```env
# PostgreSQL Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=vectordb
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# RabbitMQ Configuration
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672

# OpenAI Configuration (si es necesario)
OPENAI_API_KEY=tu-clave-de-openai
```

**Nota importante sobre hosts:**
- Si las aplicaciones Python corren **fuera de Docker** (desarrollo local), usa `localhost` para `RABBITMQ_HOST` y `POSTGRES_HOST`
- Si las aplicaciones Python corren **dentro de Docker**, usa los nombres de servicio: `rabbitmq`, `postgres`, `minio`

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

