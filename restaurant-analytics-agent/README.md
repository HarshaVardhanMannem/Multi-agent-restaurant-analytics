# Restaurant Analytics Agent

A Natural Language to SQL agent system for restaurant analytics. Converts natural language queries into SQL, executes them on Supabase, and generates visualizations.

## Features

- **Natural Language Understanding**: Converts plain English queries into SQL
- **Multi-Agent Architecture**: Uses LangGraph for orchestrated agent workflow designed to minimize hallucinations
- **Smart Schema Awareness**: Knows about tables, columns, and optimization strategies
- **SQL Validation**: Validates queries for safety and correctness with deterministic rule-based checks
- **Auto-Retry**: Automatically fixes common SQL generation errors with feedback loops
- **Result Verification**: Ensures SQL results actually answer the user's question
- **Visualization Planning**: Suggests appropriate chart types based on data
- **Chart.js Integration**: Generates Chart.js compatible configurations

> 📐 **Architecture Details**: See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for comprehensive documentation on the multi-agent system, design decisions, and hallucination mitigation strategies.

> ⚠️ **Data Note:** The current database contains data from **January 1-4, 2025** only.

## Tech Stack

- **Backend**: FastAPI + Python 3.11
- **Agent Framework**: LangGraph + LangChain
- **Database**: Supabase (PostgreSQL with SSL)
- **LLM**: NVIDIA Nemotron (via NVIDIA API)
- **Visualization**: Chart.js compatible configs

## Installation & Setup Guide

This guide provides complete step-by-step instructions for setting up the Restaurant Analytics Agent on both **macOS** and **Windows**.

### Prerequisites

#### For macOS:
- **Python 3.11+** (check with `python3 --version`)
  - Install via Homebrew: `brew install python@3.11`
  - Or download from [python.org](https://www.python.org/downloads/)
- **pip** (usually comes with Python)
- **Git** (check with `git --version`)
- Terminal application (Terminal.app or iTerm2)

#### For Windows:
- **Python 3.11+** (check with `python --version`)
  - Download from [python.org](https://www.python.org/downloads/)
  - **Important:** Check "Add Python to PATH" during installation
- **pip** (usually comes with Python)
- **Git for Windows** - Download from [git-scm.com](https://git-scm.com/download/win)
- PowerShell or Command Prompt
- Optional: Windows Terminal for better experience

### Step-by-Step Installation

#### Step 1: Clone or Navigate to the Project

**macOS/Linux:**
```bash
cd restaurant-analytics-agent
```

**Windows (PowerShell):**
```powershell
cd restaurant-analytics-agent
```

**Windows (Command Prompt):**
```cmd
cd restaurant-analytics-agent
```

#### Step 2: Create a Virtual Environment

A virtual environment isolates your project dependencies from other Python projects.

**macOS/Linux:**
```bash
python3 -m venv venv
```

**Windows (PowerShell):**
```powershell
python -m venv venv
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
```

> **Note:** If you get an error like `python: command not found` on macOS, use `python3` instead of `python`.

#### Step 3: Activate the Virtual Environment

**macOS/Linux:**
```bash
source venv/bin/activate
```

When activated, you'll see `(venv)` at the start of your terminal prompt.

**Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

If you get an execution policy error, run this first:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Windows (Command Prompt):**
```cmd
venv\Scripts\activate.bat
```

#### Step 4: Upgrade pip (Recommended)

**macOS/Linux:**
```bash
pip install --upgrade pip
```

**Windows:**
```powershell
# PowerShell or Command Prompt
pip install --upgrade pip
```

#### Step 5: Install Project Dependencies

**macOS/Linux:**
```bash
pip install -r requirements.txt
```

**Windows:**
```powershell
# PowerShell or Command Prompt
pip install -r requirements.txt
```

> **Note:** This may take a few minutes as it installs all required packages including FastAPI, LangChain, LangGraph, and other dependencies.

#### Step 6: Configure Environment Variables

**All configuration values must be set in a `.env` file** in the `restaurant-analytics-agent` directory (same level as `requirements.txt`).

**Quick Setup (Recommended):**

Copy the example file and edit it with your values:

**macOS/Linux:**
```bash
cp .env.example .env
nano .env
# or
code .env  # if using VS Code
```

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
notepad .env
```

**Windows (Command Prompt):**
```cmd
copy .env.example .env
notepad .env
```

**Manual Setup:**

If you prefer to create the file manually:

**macOS/Linux:**
```bash
touch .env
nano .env
```

**Windows (PowerShell):**
```powershell
New-Item -Path .env -ItemType File
notepad .env
```

**Windows (Command Prompt):**
```cmd
type nul > .env
notepad .env
```

**Required Environment Variables:**

Your `.env` file must include the following **required** variables:

```env
# Database Configuration (REQUIRED - choose one option)
# Option 1: Full connection string (recommended)
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres

# Option 2: Alternative format
# SUPABASE_DB_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres

# Option 3: Separate URL and password
# SUPABASE_URL=https://YOUR_PROJECT.supabase.co
# SUPABASE_PASSWORD=YOUR_PASSWORD

# NVIDIA API Configuration (REQUIRED)
NVIDIA_API_KEY=your-nvidia-api-key-here
NVIDIA_MODEL=ai-nemotron-3-nano-30b-a3b
LLM_PROVIDER=nvidia

# Server Configuration (Optional - defaults shown)
API_HOST=0.0.0.0
API_PORT=8000

# Optional: Supabase API Key (for Supabase API calls)
SUPABASE_KEY=your-supabase-anon-key-here
```

> **Important:** 
> - **All values must be in `.env` file** - the application reads configuration from this file
> - Replace `YOUR_PASSWORD` with your actual Supabase database password
> - Replace `YOUR_PROJECT` with your Supabase project reference ID (e.g., `frwxepthvyqeeyftroab`)
> - Get your NVIDIA API key from [NVIDIA Build](https://build.nvidia.com/)
> - See `.env.example` for a complete template with all available options

#### Step 7: Verify Installation

Before running the server, verify that all dependencies are installed correctly:

**macOS/Linux/Windows:**
```bash
python -c "import fastapi, uvicorn, langchain, langgraph; print('All dependencies installed successfully!')"
```

If you see the success message, you're ready to proceed!

#### Step 8: Run the Server

Make sure your virtual environment is still activated (you should see `(venv)` in your prompt).

**macOS/Linux:**
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Windows:**
```powershell
# PowerShell or Command Prompt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

You should see output similar to:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

#### Step 9: Test the API

Open a **new terminal window** (keep the server running in the first one) and test the API:

**macOS/Linux:**
```bash
# Health check
curl http://localhost:8000/api/health

# Test query
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What were total sales yesterday?"}'
```

**Windows (PowerShell):**
```powershell
# Health check
Invoke-WebRequest -Uri http://localhost:8000/api/health -Method GET

# Test query
Invoke-WebRequest -Uri http://localhost:8000/api/query `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"query": "What were total sales yesterday?"}'
```

**Windows (Command Prompt):**
You can use PowerShell commands or install `curl` for Windows, or use a tool like [Postman](https://www.postman.com/downloads/) to test the API.

Alternatively, open your browser and navigate to:
- API Documentation: http://localhost:8000/docs (Swagger UI)
- Alternative Docs: http://localhost:8000/redoc (ReDoc)

### Troubleshooting

#### Common Issues

**1. "python: command not found" (macOS)**
- Use `python3` instead of `python`
- Or create an alias: `alias python=python3`

**2. "pip: command not found"**
- On macOS: `python3 -m ensurepip --upgrade`
- On Windows: Reinstall Python and ensure "Add Python to PATH" is checked

**3. Virtual environment activation fails (Windows PowerShell)**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**4. Port 8000 already in use**
- Change the port in `.env`: `API_PORT=8001`
- Or find and stop the process using port 8000:
  - macOS/Linux: `lsof -ti:8000 | xargs kill`
  - Windows: `netstat -ano | findstr :8000` then `taskkill /PID <PID> /F`

**5. Module not found errors**
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`

**6. Database connection errors**
- Verify your `SUPABASE_DB_URL` is correct in `.env`
- Check that your Supabase project is active
- Ensure your IP is whitelisted in Supabase (if required)

**7. NVIDIA API errors**
- Verify your `NVIDIA_API_KEY` is correct
- Check API key permissions on NVIDIA Build
- Ensure you have credits/quota available

### Deactivating the Virtual Environment

When you're done working, you can deactivate the virtual environment:

**macOS/Linux/Windows:**
```bash
deactivate
```

This will remove the `(venv)` prefix from your terminal prompt.

### Next Steps

- 📚 **Read the complete [API Documentation](docs/API_DOCUMENTATION.md)** - Comprehensive guide with examples for all endpoints
- Explore the [API Endpoints](#api-endpoints) section below
- Try the [Example Queries](#example-queries)
- Check out the [Agent Workflow](#agent-workflow) documentation
- Review the [Project Structure](#project-structure)

## API Endpoints

> 📖 **For detailed API documentation with examples, see [API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md)**

### Main Query Endpoint

**POST** `/api/query`

Process a natural language query.

```json
{
  "query": "Show me the top 10 selling products last month",
  "include_chart": true,
  "max_results": 100
}
```

Response:
```json
{
  "success": true,
  "query_id": "uuid",
  "intent": "product_analysis",
  "sql": "SELECT product_name, total_quantity_sold...",
  "explanation": "This query retrieves the top 10 products...",
  "results": [...],
  "result_count": 10,
  "columns": ["product_name", "total_quantity_sold", "total_revenue"],
  "visualization": {
    "type": "bar_chart",
    "config": {...},
    "chart_js_config": {...}
  },
  "execution_time_ms": 45.2
}
```

### Other Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/schema` | GET | Get database schema info |
| `/api/examples` | GET | Get example queries |
| `/api/explain` | POST | Explain query without executing |
| `/api/validate-sql` | POST | Validate SQL query |
| `/api/stats` | GET | Get API statistics |

## Agent Workflow

```
User Query
     ↓
┌─────────────────┐
│ Intent Classifier│ → Extract intent, entities, time range
└────────┬────────┘
         ↓
    Need Clarification? ──YES──→ Return clarification question
         │ NO
         ↓
┌─────────────────┐
│ Schema Analyzer  │ → Identify tables, columns, joins
└────────┬────────┘
         ↓
┌─────────────────┐
│ SQL Generator    │ → Generate PostgreSQL query
└────────┬────────┘
         ↓
┌─────────────────┐
│ SQL Validator    │ → Validate safety & correctness
└────────┬────────┘
         ↓
    Validation Passed? ──NO──→ Retry (max 2 times)
         │ YES
         ↓
    Execute on Supabase
         ↓
┌─────────────────┐
│ Viz Planner     │ → Select chart type
└────────┬────────┘
         ↓
    Return Results + Visualization
```

## Query Intent Types

| Intent | Description | Example Query |
|--------|-------------|---------------|
| `sales_analysis` | Revenue, totals, sales | "Total sales yesterday" |
| `product_analysis` | Product performance, rankings | "Top 10 products" |
| `location_comparison` | Compare stores | "Revenue by location" |
| `time_series` | Trends, patterns | "Daily sales last month" |
| `payment_analysis` | Payment methods, tips | "Credit vs cash breakdown" |
| `order_type_analysis` | Dine-in/delivery/takeout | "Compare order types" |
| `source_comparison` | Toast/DoorDash/Square | "Revenue by source" |
| `category_analysis` | Category performance | "Sales by category" |

## Visualization Types

| Type | When Used |
|------|-----------|
| `bar_chart` | Categorical comparison, rankings |
| `line_chart` | Time series, trends |
| `pie_chart` | Part-to-whole (≤8 categories) |
| `table` | Detailed data, many columns |
| `stacked_bar` | Composition within categories |
| `heatmap` | Two-dimensional patterns |

## Schema Knowledge

The agent understands these tables:

### Base Tables
- `unified_orders` - Main order data (money in cents)
- `unified_order_items` - Line items (money in cents)
- `unified_products` - Product catalog
- `unified_locations` - Restaurant locations
- `unified_payments` - Payment transactions (money in cents)

### Optimized Views (Pre-aggregated, Faster)
- `v_daily_sales_summary` - Daily metrics (money in dollars)
- `v_product_sales_summary` - Product metrics (money in dollars)
- `v_hourly_sales_pattern` - Hourly patterns (money in dollars)

### Critical Rules
1. Base tables: Divide `*_cents` by 100.0 for dollars
2. Views: Already in dollars, don't divide
3. Always filter `voided = FALSE` on `unified_orders`
4. Prefer views for aggregations (faster)

## Running Tests

```bash
# Unit tests (no external dependencies)
pytest tests/test_agents.py -v

# Integration tests (requires .env)
pytest tests/test_integration.py -v --timeout=60
```

## Project Structure

```
restaurant-analytics-agent/
├── backend/
│   ├── main.py                    # FastAPI app
│   ├── agent_framework.py         # LangGraph workflow
│   ├── database.py                # Supabase connection
│   ├── visualization.py           # Chart generator
│   ├── agents/
│   │   ├── intent_classifier.py   # Query understanding
│   │   ├── schema_analyzer.py     # Table selection
│   │   ├── sql_generator.py       # SQL generation
│   │   ├── sql_validator.py       # Safety validation
│   │   └── viz_planner.py         # Visualization selection
│   ├── models/
│   │   ├── state.py               # AgentState TypedDict
│   │   ├── requests.py            # API request models
│   │   └── responses.py           # API response models
│   ├── config/
│   │   ├── settings.py            # Environment config
│   │   └── schema_knowledge.py    # Schema metadata
│   └── utils/
│       ├── validators.py          # SQL validation
│       └── formatters.py          # Data formatting
├── tests/
│   ├── test_agents.py             # Unit tests
│   ├── test_integration.py        # Integration tests
│   └── fixtures/
│       └── sample_queries.json    # Test data
├── requirements.txt
└── README.md
```

## Example Queries

> **Note:** The database currently contains data from **January 1-4, 2025** only.

```
"What were total sales on January 2nd?"
"Show me the top 10 selling products"
"Compare revenue across all locations"
"What are our busiest hours?"
"Payment method breakdown"
"Daily revenue trend from Jan 1-4, 2025"
"Compare dine-in vs delivery vs takeout"
"Which categories generate the most revenue?"
"Average order value by location"
"Toast vs DoorDash revenue comparison"
"Total orders by source system"
"Sales breakdown by order type"
```

## Error Handling

The API returns structured error responses:

```json
{
  "success": false,
  "error_code": "SQL_GENERATION_FAILED",
  "error_message": "Failed to generate valid SQL",
  "details": {
    "errors": ["Missing voided filter"],
    "retries": 2
  },
  "suggestions": [
    "Try rephrasing your question",
    "Be more specific about what data you want"
  ]
}
```

## License

MIT License

