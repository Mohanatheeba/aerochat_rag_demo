-- =============================================================
-- Run this in Supabase SQL Editor AFTER running supabase_setup.sql
-- This creates the PGVector cosine similarity search function
-- =============================================================

-- Cosine similarity search function
-- Called by retrieval_service.py → supabase.rpc("match_document_chunks", ...)
CREATE OR REPLACE FUNCTION match_document_chunks(
    query_embedding vector(384),
    match_tenant_id uuid,
    match_count int DEFAULT 4,
    similarity_threshold float DEFAULT 0.3
)
RETURNS TABLE (
    id uuid,
    document_id uuid,
    chunk_index int,
    chunk_text text,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.document_id,
        dc.chunk_index,
        dc.chunk_text,
        dc.metadata,
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM document_chunks dc
    WHERE
        dc.tenant_id = match_tenant_id
        AND 1 - (dc.embedding <=> query_embedding) > similarity_threshold
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Usage tracking upsert function
CREATE OR REPLACE FUNCTION upsert_usage(
    p_tenant_id uuid,
    p_month text,
    p_doc_count int DEFAULT 0,
    p_storage_bytes bigint DEFAULT 0
)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO usage_logs (tenant_id, month, document_count, storage_bytes)
    VALUES (p_tenant_id, p_month, p_doc_count, p_storage_bytes)
    ON CONFLICT (tenant_id, month)
    DO UPDATE SET
        document_count = usage_logs.document_count + EXCLUDED.document_count,
        storage_bytes = usage_logs.storage_bytes + EXCLUDED.storage_bytes,
        updated_at = NOW();
END;
$$;

-- Grant execute to service role
GRANT EXECUTE ON FUNCTION match_document_chunks TO service_role;
GRANT EXECUTE ON FUNCTION upsert_usage TO service_role;

-- =============================================================
-- Verify setup
-- =============================================================
SELECT 'Setup complete! Tables created: ' || 
    (SELECT count(*)::text FROM information_schema.tables 
     WHERE table_schema = 'public') || ' tables' AS status;
