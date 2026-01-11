# Quick Start Guide

## Prerequisites

- **Python 3.11+** (for backend and ETL)
- **Node.js 18+** (for frontend)
- **Supabase Account** (free tier works)
- **NVIDIA API Key** (free at [build.nvidia.com](https://build.nvidia.com/))

## Setup & Installation

### 1. Supabase Database Setup

**Step 1: Create a Supabase Account**
1. Go to [supabase.com](https://supabase.com)
2. Sign up for a free account (GitHub, Google, or email)

**Step 2: Create a New Project**
1. Click "New Project"
2. Choose an organization (or create one)
3. Fill in project details:
   - **Name**: `restaurant-analytics` (or your preferred name)
   - **Database Password**: Create a strong password (save this!)
   - **Region**: Choose closest to you
   - **Pricing Plan**: Free tier is sufficient

**Step 3: Get Your Database Connection String**
1. In your Supabase project dashboard, go to **Settings** → **Database**
2. Scroll to **Connection String** section
3. Under "Connection pooling", select **Transaction** mode
4. Copy the connection string. It looks like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```
5. Replace `[YOUR-PASSWORD]` with your database password

**Step 4: Run the ETL Pipeline**
1. Navigate to the ETL directory:
   ```bash
   cd etl
   ```
2. Create `.env` file in project root (`clave-take-home/.env`):
   ```env
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres
   ```
3. Follow the ETL setup guide: `etl/README.md`

### 2. Backend Setup

**Step 1: Install Dependencies**
```bash
cd restaurant-analytics-agent
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Step 2: Configure Environment Variables**
Create `.env` file in `restaurant-analytics-agent/` directory:
```env
# Supabase Database (use connection string from Step 1.3)
SUPABASE_DB_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres

# NVIDIA API (get from https://build.nvidia.com/)
NVIDIA_API_KEY=your-nvidia-api-key-here
NVIDIA_MODEL=ai-nemotron-3-nano-30b-a3b

# Server Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

**Step 3: Run the Backend**
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### 3. Frontend Setup

**Step 1: Install Dependencies**
```bash
cd frontend
npm install
```

**Step 2: Configure Environment Variables**
Create `.env.local` file in `frontend/` directory:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Step 3: Run the Frontend**
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Environment Files Summary

You need to create **3 environment files**:

1. **`clave-take-home/.env`** - For ETL pipeline
   ```env
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres
   ```

2. **`clave-take-home/restaurant-analytics-agent/.env`** - For backend API
   ```env
   SUPABASE_DB_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres
   NVIDIA_API_KEY=your-nvidia-api-key-here
   NVIDIA_MODEL=ai-nemotron-3-nano-30b-a3b
   API_PORT=8000
   ```

3. **`clave-take-home/frontend/.env.local`** - For frontend
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

> **Note:** All `.env` files are gitignored and won't be committed to the repository.

## Detailed Setup Guides

For more detailed, platform-specific setup instructions:
- **Backend**: See `restaurant-analytics-agent/README.md` (includes Mac & Windows guides)
- **Frontend**: See `frontend/README.md`
- **ETL Pipeline**: See `etl/README.md`


