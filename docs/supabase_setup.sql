-- AeroChat RAG - Supabase Setup Script
-- Implements AWS Layer (MySQL + PGVector + S3) equivalents

-- 1. Enable PGVector Extension
create extension if not exists vector;

-- 2. Tenants Table (Replaces MySQL Management)
create table if not exists tenants (
    id uuid default gen_random_uuid() primary key,
    name text not null,
    domain text unique,
    shopify_enabled boolean default false,
    shopify_domain text,
    shopify_access_token text,
    message_count int default 0,
    created_at timestamp with time zone default now()
);

-- 3. Bot Configurations
create table if not exists bot_configs (
    tenant_id uuid references tenants(id) on delete cascade primary key,
    bot_name text default 'AeroChat Assistant',
    system_prompt text,
    temperature float default 0.7,
    max_tokens int default 512,
    updated_at timestamp with time zone default now()
);

-- 4. Documents Table (Metadata)
create table if not exists documents (
    id uuid default gen_random_uuid() primary key,
    tenant_id uuid references tenants(id) on delete cascade,
    file_name text not null,
    file_path text not null, -- Path in Supabase Storage
    file_size int,
    mime_type text,
    status text default 'processing', -- processing, indexed, failed
    chunk_count int default 0,
    created_at timestamp with time zone default now()
);

-- 5. Document Chunks Table (Vector Store)
create table if not exists document_chunks (
    id uuid default gen_random_uuid() primary key,
    tenant_id uuid references tenants(id) on delete cascade,
    document_id uuid references documents(id) on delete cascade,
    chunk_index int,
    chunk_text text,
    embedding vector(384), -- Dimension for all-MiniLM-L6-v2
    metadata jsonb default '{}'::jsonb,
    created_at timestamp with time zone default now()
);

-- 6. Conversations Table
create table if not exists conversations (
    id uuid default gen_random_uuid() primary key,
    tenant_id uuid references tenants(id) on delete cascade,
    session_id text not null,
    channel text default 'widget',
    customer_identifier text,
    message_count int default 0,
    last_message_at timestamp with time zone default now(),
    created_at timestamp with time zone default now()
);

-- 7. Messages Table (Logs)
create table if not exists messages (
    id uuid default gen_random_uuid() primary key,
    conversation_id uuid references conversations(id) on delete cascade,
    tenant_id uuid references tenants(id) on delete cascade,
    role text check (role in ('user', 'assistant')),
    content text not null,
    sources jsonb default '[]'::jsonb,
    latency_ms int,
    created_at timestamp with time zone default now()
);

-- 8. Usage Records
create table if not exists usage_logs (
    id uuid default gen_random_uuid() primary key,
    tenant_id uuid references tenants(id) on delete cascade,
    month text, -- YYYY-MM
    doc_count int default 0,
    storage_bytes bigint default 0,
    updated_at timestamp with time zone default now(),
    unique(tenant_id, month)
);

-- 9. Search Function (match_documents)
create or replace function match_documents (
  query_embedding vector(384),
  match_threshold float,
  match_count int,
  p_tenant_id uuid
)
returns table (
  id uuid,
  document_id uuid,
  chunk_text text,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    document_chunks.id,
    document_chunks.document_id,
    document_chunks.chunk_text,
    1 - (document_chunks.embedding <=> query_embedding) as similarity
  from document_chunks
  where document_chunks.tenant_id = p_tenant_id
  and 1 - (document_chunks.embedding <=> query_embedding) > match_threshold
  order by document_chunks.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- 10. Usage Upsert Function
create or replace function upsert_usage(
  p_tenant_id uuid,
  p_month text,
  p_doc_count int,
  p_storage_bytes bigint
)
returns void as $$
begin
  insert into usage_logs (tenant_id, month, doc_count, storage_bytes)
  values (p_tenant_id, p_month, p_doc_count, p_storage_bytes)
  on conflict (tenant_id, month)
  do update set
    doc_count = usage_logs.doc_count + p_doc_count,
    storage_bytes = usage_logs.storage_bytes + p_storage_bytes,
    updated_at = now();
end;
$$ language plpgsql;
