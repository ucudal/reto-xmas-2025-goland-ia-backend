# Sistema RAG con LangGraph - Goland IA

Sistema de Retrieval-Augmented Generation (RAG) con procesamiento avanzado de documentos y chat inteligente usando LangGraph.

## 🚀 Características

- **Upload de PDFs**: Carga documentos y procesamiento automático
- **Vector Search**: Búsqueda semántica en documentos usando pgvector
- **Chat Inteligente**: Conversación con agente LangGraph que usa RAG
- **Guardrails**: Validaciones de seguridad pre y post generación
- **Procesamiento Asíncrono**: Worker para PDFs con RabbitMQ
- **Historial de Chat**: Contexto de conversación persistente

## 📋 Tabla de Contenidos

- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso](#uso)
- [API Endpoints](#api-endpoints)
- [Desarrollo](#desarrollo)
- [Testing](#testing)

## 🏗️ Arquitectura

El sistema está dividido en dos microservicios:

### DocsManager (Puerto 8000)
- Manejo de uploads de documentos
- Gestión de MinIO
- Publicación a RabbitMQ

### RAGManager (Puerto 8001)
- **Chat completo**: Recibe mensajes, ejecuta agente, guarda respuestas
- Procesamiento RAG con LangGraph
- Vector store con pgvector
- Worker de procesamiento de PDFs
- Guardrails y validaciones

Ver [ARCHITECTURE.md](./ARCHITECTURE.md) para más detalles.

## 📦 Requisitos

- Python 3.12+
- PostgreSQL 14+ con pgvector
- MinIO
- RabbitMQ
- OpenAI API Key
- Guardrails AI API Key

## 🔧 Instalación

### 1. Clonar el repositorio

```bash
git clone <repository-url>
cd reto-xmas-2025-goland-ia-backend
```

### 2. Instalar dependencias

#### Usando uv (recomendado)

```bash
# DocsManager
cd DocsManager
uv sync

# RAGManager
cd ../RAGManager
uv sync
```

#### Usando pip

```bash
# DocsManager
cd DocsManager
pip install -r requirements.txt

# RAGManager
cd ../RAGManager
pip install -r requirements.txt
```

### 3. Iniciar infraestructura

```bash
# En el directorio raíz
docker-compose up -d postgres rabbitmq minio
```

### 4. Inicializar base de datos

```bash
# Ejecutar script SQL de inicialización
psql -U postgres -h localhost -d goland_ia_db -f db-init/01-initial-setup.sql
```

## ⚙️ Configuración

### DocsManager

Crear `.env` en `DocsManager/`:

```bash
# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=goland_ia_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# RabbitMQ
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=documents
MINIO_FOLDER=rag-docs
MINIO_USE_SSL=false
```

### RAGManager

Crear `.env` en `RAGManager/`:

```bash
# PostgreSQL
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/goland_ia_db

# OpenAI
OPENAI_API_KEY=sk-your-openai-api-key-here

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=documents
MINIO_USE_SSL=false

# RabbitMQ
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_QUEUE_NAME=document.process

# Guardrails
GUARDRAILS_API_KEY=your-guardrails-key-here
GUARDRAILS_JAILBREAK_THRESHOLD=0.9
GUARDRAILS_DEVICE=cpu

# Configuración
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
```

## 🎯 Uso

### Iniciar los servicios

```bash
# Terminal 1 - DocsManager
cd DocsManager
uvicorn main:app --reload --port 8000

# Terminal 2 - RAGManager
cd RAGManager
uvicorn main:app --reload --port 8001

# Terminal 3 - Worker de PDFs
cd RAGManager
python -m app.workers.pdf_processor_consumer
```

### Acceder a las APIs

- **DocsManager**: http://localhost:8000/docs
- **RAGManager**: http://localhost:8001/docs

## 📡 API Endpoints

### RAGManager - Chat Principal

#### POST /chat/messages

Enviar un mensaje y recibir respuesta del agente RAG.

**Request:**
```json
{
  "message": "¿Cuáles son los beneficios del aguacate?",
  "session_id": null
}
```

**Response:**
```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "message": "El aguacate es una fruta rica en grasas saludables..."
}
```

**Proceso interno:**
1. Guarda mensaje del usuario
2. Ejecuta grafo LangGraph:
   - `agent_host`: Prepara estado e historial
   - `guard_inicial`: Valida contenido malicioso
   - `parafraseo`: Parafrasea el mensaje
   - `retriever`: Busca en vector DB
   - `context_builder`: Genera respuesta con GPT-4
   - `guard_final`: Valida respuesta
3. Guarda respuesta del asistente
4. Retorna respuesta

#### GET /chat/history/{session_id}

Obtener historial de una conversación.

**Response:**
```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "messages": [
    {
      "id": 1,
      "sender": "user",
      "message": "¿Cuáles son los beneficios del aguacate?",
      "created_at": "2025-12-18T10:00:00"
    },
    {
      "id": 2,
      "sender": "assistant",
      "message": "El aguacate es rico en...",
      "created_at": "2025-12-18T10:00:05"
    }
  ],
  "count": 2
}
```

### DocsManager - Gestión de Documentos

#### POST /documents/upload

Subir un PDF para procesamiento.

**Request:**
```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@documento.pdf"
```

**Response:**
```json
{
  "filename": "documento.pdf",
  "path": "rag-docs/documento.pdf",
  "status": "uploaded"
}
```

#### GET /documents

Listar todos los documentos.

**Response:**
```json
{
  "documents": [
    {
      "id": 1,
      "name": "documento.pdf",
      "upload_date": "2025-12-18T10:00:00",
      "status": "processed"
    }
  ]
}
```

## 🛠️ Desarrollo

### Estructura del Proyecto

```
reto-xmas-2025-goland-ia-backend/
├── DocsManager/              # Servicio de gestión de documentos
│   ├── app/
│   │   ├── api/             # Endpoints FastAPI
│   │   ├── core/            # Configuración y DB
│   │   ├── models/          # Modelos SQLAlchemy
│   │   ├── schemas/         # Schemas Pydantic
│   │   └── services/        # Lógica de negocio
│   ├── main.py
│   └── pyproject.toml
│
├── RAGManager/              # Servicio RAG con LangGraph
│   ├── app/
│   │   ├── agents/          # Grafo LangGraph
│   │   │   ├── nodes/       # Nodos del grafo
│   │   │   ├── graph.py     # Definición del grafo
│   │   │   ├── routing.py   # Routing condicional
│   │   │   └── state.py     # Estado del agente
│   │   ├── api/             # Endpoints FastAPI
│   │   ├── core/            # Configuración y DB
│   │   ├── models/          # Modelos SQLAlchemy
│   │   ├── schemas/         # Schemas Pydantic
│   │   ├── services/        # Lógica de negocio
│   │   └── workers/         # Worker RabbitMQ
│   ├── main.py
│   └── pyproject.toml
│
├── docker-compose.yml       # Infraestructura
├── ARCHITECTURE.md          # Documentación de arquitectura
└── README.md               # Este archivo
```

### Grafo LangGraph

El agente RAG implementa el siguiente flujo:

```
START → agent_host → guard_inicial → parafraseo → retriever → 
context_builder → guard_final → END
```

Con validaciones y fallbacks en cada paso.

### Linting y Formato

```bash
# Usando ruff
cd DocsManager
ruff check .
ruff format .

cd RAGManager
ruff check .
ruff format .
```

## 🧪 Testing

### Test Manual con cURL

#### 1. Subir un PDF

```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test.pdf"
```

#### 2. Enviar mensaje al chat

```bash
curl -X POST "http://localhost:8001/chat/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "¿Qué información tienes sobre nutrición?",
    "session_id": null
  }'
```

#### 3. Obtener historial

```bash
curl -X GET "http://localhost:8001/chat/history/{session_id}" \
  -H "accept: application/json"
```

### Tests Automatizados (TODO)

```bash
# DocsManager
cd DocsManager
pytest

# RAGManager
cd RAGManager
pytest
```

## 🐳 Docker

### Desarrollo

```bash
docker-compose up -d postgres rabbitmq minio
```

### Producción (TODO)

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 📊 Monitoreo

### Logs

```bash
# DocsManager
tail -f DocsManager/logs/app.log

# RAGManager
tail -f RAGManager/logs/app.log
```

### RabbitMQ Management

- URL: http://localhost:15672
- Usuario: guest
- Password: guest

### MinIO Console

- URL: http://localhost:9001
- Usuario: minioadmin
- Password: minioadmin

## 🔐 Seguridad

### Guardrails Implementados

1. **Guard Inicial**: Detecta jailbreak y contenido malicioso
2. **Guard Final**: Detecta PII y contenido sensible

### Validaciones

- Tipos de archivo permitidos
- Tamaño máximo de archivos
- Sanitización de inputs
- Rate limiting (por implementar)

## 🤝 Contribuir

1. Fork el proyecto
2. Crear branch (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📝 Licencia

Este proyecto es privado y confidencial.

## 👥 Equipo

Desarrollado por el equipo de Goland IA.

## 📧 Contacto

Para preguntas o soporte, contactar al equipo de desarrollo.

## 🗺️ Roadmap

### v1.0 (Actual)
- ✅ Upload de PDFs
- ✅ Chat con RAG
- ✅ Guardrails
- ✅ Historial de conversación

### v1.1 (Próximo)
- ⏳ Streaming de respuestas
- ⏳ Cache con Redis
- ⏳ Autenticación JWT
- ⏳ Rate limiting

### v2.0 (Futuro)
- 📋 WebSockets para chat
- 📋 Multi-idioma
- 📋 Tests automatizados
- 📋 CI/CD pipeline
- 📋 Métricas y monitoreo

## 🙏 Agradecimientos

- LangChain & LangGraph
- FastAPI
- OpenAI
- Guardrails AI
