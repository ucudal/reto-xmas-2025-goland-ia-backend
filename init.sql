-- Habilitar la extensión pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Habilitar extensión para UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- A. TABLAS DE RAG (Vector Store)
-- ============================================

-- 1. Tabla documents: Guarda los PDFs o documentos que sube el usuario (solo metadatos)
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    minio_path TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- B. TABLAS DE CHAT
-- ============================================

-- 1. Tabla chat_sessions: Cada conversación del usuario tiene un ID único
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Índice para búsquedas por metadata (opcional, útil si buscas por user_id)
CREATE INDEX IF NOT EXISTS chat_sessions_metadata_idx 
ON chat_sessions USING GIN (metadata);

-- 2. Tabla chat_messages: Guarda el historial de conversación del usuario
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sender_type') THEN
        CREATE TYPE sender_type AS ENUM ('user', 'assistant', 'system');
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    sender sender_type NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índice para búsquedas por sesión
CREATE INDEX IF NOT EXISTS chat_messages_session_id_idx 
ON chat_messages(session_id);



