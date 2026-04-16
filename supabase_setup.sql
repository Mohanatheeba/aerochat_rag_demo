-- =============================================================
-- AeroChat Staging - Supabase Setup SQL
-- Run this in Supabase SQL Editor AFTER enabling pgvector extension
-- Extensions → Search "vector" → Enable it
-- =============================================================

-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================
-- TENANTS / ACCOUNTS (Multi-tenant, Super Admin manages this)
-- =============================================================
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    plan TEXT DEFAULT 'free',
    whatsapp_enabled BOOLEAN DEFAULT FALSE,
    shopify_enabled BOOLEAN DEFAULT FALSE,
    shopify_domain TEXT,
    shopify_access_token TEXT,
    whatsapp_phone_number_id TEXT,
    whatsapp_verify_token TEXT,
    message_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- USERS (Tenant admins who log into dashboard)
-- =============================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    role TEXT DEFAULT 'admin',  -- 'admin', 'super_admin'
    supabase_auth_id UUID,      -- links to Supabase Auth
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- BOT CONFIGURATIONS
-- =============================================================
CREATE TABLE IF NOT EXISTS bot_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    bot_name TEXT DEFAULT 'AeroChat Bot',
    system_prompt TEXT DEFAULT 'You are a helpful customer service assistant.',
    temperature FLOAT DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 500,
    language TEXT DEFAULT 'en',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- KNOWLEDGE BASE DOCUMENTS (S3 equivalent metadata)
-- =============================================================
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,        -- Supabase Storage path
    file_size INTEGER,
    mime_type TEXT,
    status TEXT DEFAULT 'pending',  -- pending, processing, indexed, failed
    chunk_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- VECTOR EMBEDDINGS (PGVector - AI long-term memory)
-- =============================================================
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(384),          -- sentence-transformers all-MiniLM-L6-v2 = 384 dims
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cosine similarity index for fast vector search
CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx 
ON document_chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Index by tenant for multi-tenant isolation
CREATE INDEX IF NOT EXISTS document_chunks_tenant_idx ON document_chunks(tenant_id);

-- =============================================================
-- CONVERSATIONS / CHAT HISTORY (MySQL equivalent)
-- =============================================================
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,       -- links to Redis session
    channel TEXT DEFAULT 'widget',  -- 'widget', 'whatsapp'
    customer_identifier TEXT,       -- phone number or browser fingerprint
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    message_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    role TEXT NOT NULL,             -- 'user', 'assistant'
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]',     -- which chunks were retrieved
    latency_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS messages_conversation_idx ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS messages_tenant_idx ON messages(tenant_id);
CREATE INDEX IF NOT EXISTS conversations_tenant_idx ON conversations(tenant_id);

-- =============================================================
-- SUPPORT TICKETS (Supabase support component)
-- =============================================================
CREATE TABLE IF NOT EXISTS support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'open',     -- open, in_progress, resolved, closed
    priority TEXT DEFAULT 'medium', -- low, medium, high, critical
    created_by_email TEXT,
    assigned_to TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- BILLING / USAGE TRACKING (Super Admin auditing)
-- =============================================================
CREATE TABLE IF NOT EXISTS usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    month TEXT NOT NULL,            -- '2024-01'
    message_count INTEGER DEFAULT 0,
    document_count INTEGER DEFAULT 0,
    storage_bytes BIGINT DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, month)
);

-- =============================================================
-- ROW LEVEL SECURITY (Tenant isolation)
-- =============================================================
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;

-- Super admin bypass policy (service role key bypasses RLS automatically)
-- Regular tenant policies
CREATE POLICY "Tenants see own data" ON documents
    FOR ALL USING (tenant_id = (
        SELECT tenant_id FROM users 
        WHERE supabase_auth_id = auth.uid()
    ));

CREATE POLICY "Tenants see own chunks" ON document_chunks
    FOR ALL USING (tenant_id = (
        SELECT tenant_id FROM users 
        WHERE supabase_auth_id = auth.uid()
    ));

-- =============================================================
-- SEED: Insert a default super admin tenant
-- =============================================================
INSERT INTO tenants (id, name, email, plan) 
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'AeroChat Internal',
    'superadmin@aerochat.ai',
    'super_admin'
) ON CONFLICT DO NOTHING;

INSERT INTO users (tenant_id, email, name, role)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'superadmin@aerochat.ai',
    'Super Admin',
    'super_admin'
) ON CONFLICT DO NOTHING;
