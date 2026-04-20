# AeroChat RAG - Staging Environment (100% Free Stack)

## Architecture (Free Tier Equivalent)

```
[Railway Layer - FREE]
├── Frontend: React (Vite) → Railway free tier
├── Backend: FastAPI → Railway free tier  
├── Redis: Upstash Redis → Free tier (10k req/day)
└── Shopify: Placeholder webhook handler

[AWS Layer - REPLACED WITH FREE]
├── S3 Bucket → Supabase Storage (1GB free)
├── MySQL RDS → Supabase PostgreSQL (free)
└── PGVector → Supabase pgvector extension (free)

[Other Components - FREE]
├── Supabase → Auth + Support tickets
├── Super Admin → Built-in React panel
├── LLM → Groq API (free tier, llama3-70b)
└── Embeddings → sentence-transformers (local / HuggingFace free)
```

## Free Services Required (All Free Tier)

1. **Supabase** → https://supabase.com (Database + Storage + Auth + PGVector)
2. **Groq** → https://console.groq.com (LLM - 14,400 req/day free)
3. **Upstash** → https://upstash.com (Redis - 10,000 req/day free)
4. **Railway** → https://railway.app (Hosting - $5 free credit/month)

## Setup Instructions

### 1. Supabase Setup
1. Create project at supabase.com
2. Go to SQL Editor → Run the SQL in `docs/supabase_setup.sql`
3. Enable pgvector: Extensions → enable `vector`
4. Create storage bucket named `aerochat-media` (public: false)
5. Copy your `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`

### 2. Groq Setup
1. Sign up at console.groq.com
2. Create API key → copy as `GROQ_API_KEY`

### 3. Upstash Redis Setup
1. Sign up at upstash.com → Create Redis database
2. Copy `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`

### 4. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # Fill in your keys
uvicorn app.main:app --reload --port 8000
```

### 5. Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env      # Set VITE_API_URL=http://localhost:8000
npm run dev
```

## Real-Time Flow (Matches AeroChat Architecture)

```
Customer Message (WhatsApp/Widget)
    ↓
FastAPI Backend (webhook handler)
    ↓
Redis (session context lookup - Upstash)
    ↓
PGVector Cosine Similarity Search (Supabase)
    ↓
[If order query] → Shopify API Live Data
    ↓
Groq LLM (llama3-70b) → Natural response
    ↓
Response to Customer
    ↓ (simultaneously)
MySQL Log → Supabase PostgreSQL
Redis Update → Upstash
```
