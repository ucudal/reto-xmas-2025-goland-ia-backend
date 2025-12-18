# Arquitectura del Sistema RAG

## Visión General

El sistema está compuesto por dos servicios principales:

1. **DocsManager** (Puerto 8000) - Gestión de documentos y MinIO
2. **RAGManager** (Puerto 8001) - Procesamiento RAG y Chat con LangGraph

```
┌─────────────────────────────────────────────────────────────────┐
│                         ARQUITECTURA                             │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐                              ┌──────────────┐
│   Cliente    │                              │   Cliente    │
│   Web/App    │                              │   Web/App    │
└──────┬───────┘                              └──────┬───────┘
       │                                             │
       │ POST /documents/upload                      │ POST /chat/messages
       │ (subir PDFs)                                │ (enviar mensajes)
       │                                             │
       ▼                                             ▼
┌──────────────────┐                        ┌──────────────────┐
│   DocsManager    │                        │   RAGManager     │
│   Puerto 8000    │                        │   Puerto 8001    │
└────────┬─────────┘                        └────────┬─────────┘
         │                                           │
         │ 1. Guarda en MinIO                        │ 1. Guarda mensaje usuario
         │ 2. Publica a RabbitMQ                     │ 2. Ejecuta LangGraph
         │                                           │ 3. Guarda respuesta
         │                                           │
         ▼                                           ▼
┌─────────────────┐                        ┌─────────────────┐
│     MinIO       │                        │   PostgreSQL    │
│  (Documentos)   │                        │  (Chat + Docs)  │
└─────────────────┘                        └────────┬────────┘
         │                                           │
         │ Evento: nuevo PDF                         │ Vector Store
         ▼                                           │
┌─────────────────┐                                 │
│   RabbitMQ      │                                 │
│ (Cola: docs)    │                                 │
└────────┬────────┘                                 │
         │                                           │
         │ Worker consume                            │
         ▼                                           │
┌──────────────────┐                                │
│   RAGManager     │                                │
│   Worker PDF     │───────────────────────────────►│
│                  │  Chunking + Embeddings         │
└──────────────────┘  Guarda en Vector DB           │
```

## Flujo de Documentos

### Subida de PDFs

```
Usuario → DocsManager → MinIO → RabbitMQ → RAGManager Worker
                                              ↓
                                         PostgreSQL
                                        (Vector Store)
```

1. **Usuario sube PDF** → `POST /documents/upload` a DocsManager
2. **DocsManager** guarda el archivo en MinIO
3. **MinIO** genera un evento y lo publica a RabbitMQ
4. **RAGManager Worker** consume el mensaje de RabbitMQ
5. **RAGManager Worker**:
   - Descarga el PDF de MinIO
   - Extrae el texto
   - Hace chunking (divide en pedazos)
   - Genera embeddings (vectores)
   - Guarda chunks y vectores en PostgreSQL
6. **RAGManager** retorna el document_id

## Flujo de Chat

### Envío de Mensajes

```
Usuario → RAGManager → LangGraph Agent → PostgreSQL
                            ↓
                      OpenAI GPT-4
```

1. **Usuario envía mensaje** → `POST /chat/messages` a RAGManager
2. **RAGManager**:
   - Crea o recupera sesión de chat
   - Guarda mensaje del usuario en PostgreSQL
3. **RAGManager** ejecuta el **grafo de LangGraph**:

```
START
  │
  ▼
┌─────────────────┐
│  agent_host     │ (Nodo 1)
│  - Prepara      │
│  - Historial    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ guard_inicial   │ (Nodo 2)
│ - Detecta       │
│   contenido     │
│   malicioso     │
└────┬────────────┘
     │
     ├──[malicious]──> fallback_inicial ──> END
     │
     └──[continue]──>
                     ┌─────────────────┐
                     │  parafraseo     │ (Nodo 4)
                     │  - Parafrasea   │
                     │  - 3 variantes  │
                     └────────┬────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │   retriever     │ (Nodo 5)
                     │  - Busca chunks │
                     │    relevantes   │
                     │  - Vector DB    │
                     └────────┬────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │ context_builder │ (Nodo 6)
                     │  - Construye    │
                     │    query        │
                     │  - Llama GPT-4  │
                     └────────┬────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │  guard_final    │ (Nodo 8)
                     │  - Valida PII   │
                     │  - Detecta info │
                     │    sensible     │
                     └────┬────────────┘
                          │
                          ├──[risky]──> fallback_final ──> END
                          │
                          └──[continue]──> END (éxito)
```

4. **RAGManager** guarda la respuesta del asistente en PostgreSQL
5. **RAGManager** retorna la respuesta al usuario

## Base de Datos

### PostgreSQL (Compartida por ambos servicios)

#### Tablas de Chat (usadas SOLO por RAGManager)

```sql
-- Sesiones de chat
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

-- Mensajes de chat
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    sender sender_type NOT NULL,  -- 'user', 'assistant', 'system'
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### Tablas de Documentos (usadas por ambos servicios)

```sql
-- Documentos
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    upload_date TIMESTAMP DEFAULT NOW(),
    file_size INTEGER,
    status TEXT
);

-- Chunks de documentos con vectores
CREATE TABLE document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    embedding vector(1536),  -- Dimensión de text-embedding-3-small
    metadata JSONB
);
```

## Endpoints

### DocsManager (Puerto 8000)

#### Gestión de Documentos

```http
POST /documents/upload
Content-Type: multipart/form-data

Sube un PDF a MinIO y lo encola para procesamiento
```

```http
GET /documents
Content-Type: application/json

Lista todos los documentos
```

### RAGManager (Puerto 8001)

#### Chat Principal

```http
POST /chat/messages
Content-Type: application/json

{
  "message": "¿Cuáles son los beneficios del aguacate?",
  "session_id": "uuid-optional"
}

Response:
{
  "session_id": "uuid",
  "message": "El aguacate es rico en grasas saludables..."
}
```

```http
GET /chat/history/{session_id}
Content-Type: application/json

Response:
{
  "session_id": "uuid",
  "messages": [
    {
      "id": 1,
      "sender": "user",
      "message": "...",
      "created_at": "2025-12-18T..."
    },
    {
      "id": 2,
      "sender": "assistant",
      "message": "...",
      "created_at": "2025-12-18T..."
    }
  ],
  "count": 2
}
```

#### Gestión de Documentos

```http
GET /documents
Content-Type: application/json

Lista todos los documentos procesados
```

```http
DELETE /documents/{document_id}
Content-Type: application/json

Elimina un documento y sus chunks
```

## Componentes del Sistema

### 1. DocsManager

**Responsabilidades:**
- Recibir uploads de PDFs
- Guardar archivos en MinIO
- Gestionar eventos de MinIO
- Publicar trabajos a RabbitMQ

**Tecnologías:**
- FastAPI
- MinIO SDK
- Pika (RabbitMQ)
- PostgreSQL (SQLAlchemy)

### 2. RAGManager

**Responsabilidades:**
- Procesar PDFs (chunking, embeddings)
- Gestionar vector store (pgvector)
- Ejecutar grafo de LangGraph
- Manejar chat completo (guardar mensajes, procesar, responder)
- Aplicar guardrails (validaciones)

**Tecnologías:**
- FastAPI
- LangChain + LangGraph
- OpenAI (embeddings + GPT-4)
- Guardrails AI
- PostgreSQL + pgvector
- Pika (RabbitMQ consumer)

### 3. Infraestructura

**PostgreSQL + pgvector:**
- Base de datos compartida
- Extensión pgvector para búsqueda vectorial
- Almacena chat, documentos y embeddings

**MinIO:**
- Almacenamiento de objetos (PDFs)
- Compatible con S3
- Genera eventos para procesamiento

**RabbitMQ:**
- Cola de mensajes
- Desacopla upload de procesamiento
- Worker asíncrono para PDFs

## Configuración

### Variables de Entorno

#### DocsManager (.env)

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

#### RAGManager (.env)

```bash
# PostgreSQL
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/goland_ia_db

# OpenAI
OPENAI_API_KEY=sk-your-key-here

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
GUARDRAILS_API_KEY=your-key-here
GUARDRAILS_JAILBREAK_THRESHOLD=0.9
GUARDRAILS_DEVICE=cpu

# Chunking
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Embeddings
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
```

## Ejecución

### Desarrollo Local

```bash
# Terminal 1 - Infraestructura (Docker)
docker-compose up postgres rabbitmq minio

# Terminal 2 - DocsManager
cd DocsManager
uv sync
uvicorn main:app --reload --port 8000

# Terminal 3 - RAGManager
cd RAGManager
uv sync
uvicorn main:app --reload --port 8001

# Terminal 4 - RAGManager Worker (PDF Processing)
cd RAGManager
python -m app.workers.pdf_processor_consumer
```

### Docker Compose

```bash
docker-compose up
```

## Ventajas de la Arquitectura

### Separación de Responsabilidades

✅ **DocsManager**: Maneja solo documentos y MinIO
✅ **RAGManager**: Maneja RAG, LangGraph y chat completo
✅ Cada servicio tiene su propio dominio claro

### Escalabilidad

✅ Servicios independientes pueden escalar por separado
✅ Worker de PDFs puede tener múltiples instancias
✅ RAGManager puede tener más recursos (GPU, RAM)

### Mantenibilidad

✅ Código del agente aislado en RAGManager
✅ Cambios en LangGraph no afectan DocsManager
✅ Tests independientes por servicio

### Performance

✅ Procesamiento de PDFs asíncrono (no bloquea)
✅ Chat sincrónico (respuesta inmediata)
✅ Vector search optimizado con pgvector

### Confiabilidad

✅ RabbitMQ garantiza procesamiento de PDFs
✅ Fallbacks en caso de errores del agente
✅ Guardrails previenen respuestas problemáticas

## Seguridad

### Guardrails Implementados

1. **Guard Inicial** (Pre-procesamiento):
   - Detecta intentos de jailbreak
   - Previene contenido malicioso
   - Bloquea prompts peligrosos

2. **Guard Final** (Post-procesamiento):
   - Detecta PII en respuestas
   - Filtra información sensible
   - Valida que no haya datos confidenciales

### Validaciones

- Tipos de archivo (solo PDFs)
- Tamaño de mensajes
- Rate limiting (puede implementarse)
- Autenticación (puede implementarse)

## Próximos Pasos

### Mejoras Sugeridas

1. **Streaming**: Respuestas en tiempo real (SSE)
2. **Cache**: Redis para respuestas frecuentes
3. **Métricas**: Prometheus + Grafana
4. **Autenticación**: JWT tokens
5. **Rate Limiting**: Limitar requests por usuario
6. **WebSockets**: Chat en tiempo real
7. **Multi-idioma**: Soporte para varios idiomas
8. **Tests**: Unitarios e integración
9. **CI/CD**: GitHub Actions
10. **Monitoreo**: Sentry para errores

### Optimizaciones

- **Caché de embeddings**: No re-calcular
- **Batch processing**: Procesar múltiples PDFs
- **Connection pooling**: PostgreSQL
- **CDN**: Para archivos estáticos
- **Load balancer**: Para múltiples instancias

