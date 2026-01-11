# Restaurant Analytics Dashboard - Frontend

Next.js frontend for the Restaurant Analytics Agent API. Provides a natural language interface to query restaurant data with dynamic visualizations.

## Features

- 🎯 **Natural Language Queries** - Type questions in plain English
- 📊 **Dynamic Visualizations** - Automatically generates appropriate charts (bar, line, pie, tables)
- 📦 **Widget-Based Dashboard** - Add multiple queries as widgets
- 🔄 **Real-time Query Processing** - Fast API integration
- 💡 **Example Queries** - Quick-start suggestions
- 🎨 **Modern UI** - Clean, responsive design with Tailwind CSS

## Tech Stack

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Charts**: Chart.js + react-chartjs-2
- **HTTP Client**: Axios
- **Icons**: Lucide React

## Getting Started

### Prerequisites

- **Node.js 20+** and npm/yarn
- **Backend API** running on `http://localhost:8000` (see `restaurant-analytics-agent` directory)

#### Installing Node.js

**Windows:**
1. Download Node.js from [nodejs.org](https://nodejs.org/)
2. Run the installer (`.msi` file)
3. Verify installation:
   ```powershell
   node --version
   npm --version
   ```

**Mac:**
1. Using Homebrew (recommended):
   ```bash
   brew install node@20
   ```
2. Or download from [nodejs.org](https://nodejs.org/)
3. Verify installation:
   ```bash
   node --version
   npm --version
   ```

### Installation

**Step 1: Navigate to the frontend directory**

**Windows (PowerShell/Command Prompt):**
```powershell
cd clave-take-home\frontend
```

**Mac/Linux:**
```bash
cd clave-take-home/frontend
```

**Step 2: Install dependencies**

```bash
npm install
```

**Step 3: Set up environment variables**

**Windows (PowerShell):**
```powershell
# Copy environment example
Copy-Item .env.local.example .env.local

# Edit .env.local if backend runs on different port
notepad .env.local
```

**Windows (Command Prompt):**
```cmd
copy .env.local.example .env.local
notepad .env.local
```

**Mac/Linux:**
```bash
# Copy environment example
cp .env.local.example .env.local

# Edit .env.local if backend runs on different port
nano .env.local
# or
code .env.local  # if using VS Code
```

**Step 4: Configure environment variables**

Edit `.env.local` and set:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

(Only change this if your backend runs on a different port)

### Development

**Step 1: Start the backend API** (in a separate terminal)

Navigate to the backend directory:

**Windows:**
```powershell
cd ..\restaurant-analytics-agent
python run.py
```

**Mac/Linux:**
```bash
cd ../restaurant-analytics-agent
python run.py
```

**Step 2: Start the frontend development server**

In a new terminal, navigate to the frontend directory:

**Windows:**
```powershell
cd clave-take-home\frontend
npm run dev
```

**Mac/Linux:**
```bash
cd clave-take-home/frontend
npm run dev
```

**Step 3: Open your browser**

Open [http://localhost:3000](http://localhost:3000) in your browser.

You should see the Restaurant Analytics Dashboard.

### Build for Production

**Windows:**
```powershell
# Build the application
npm run build

# Start production server
npm start
```

**Mac/Linux:**
```bash
# Build the application
npm run build

# Start production server
npm start
```

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx          # Root layout
│   ├── page.tsx            # Main dashboard page
│   └── globals.css         # Global styles
├── components/
│   ├── QueryInput.tsx      # Query input component
│   ├── ChartWidget.tsx     # Chart/widget display
│   ├── ClarificationDialog.tsx  # Clarification UI
│   └── ErrorAlert.tsx      # Error display
├── lib/
│   └── api.ts              # API client
├── types/
│   └── api.ts              # TypeScript types
└── package.json
```

## Usage Guide

### Complete Setup Steps (Windows)

1. **Open Terminal 1 - Start Backend:**
   ```powershell
   cd clave-take-home\restaurant-analytics-agent
   python run.py
   ```
   Wait for: `INFO:     Uvicorn running on http://127.0.0.1:8000`

2. **Open Terminal 2 - Start Frontend:**
   ```powershell
   cd clave-take-home\frontend
   npm run dev
   ```
   Wait for: `Ready - started server on 0.0.0.0:3000`

3. **Open Browser:**
   - Navigate to: `http://localhost:3000`
   - You should see the login/register page

4. **Create an Account:**
   - Click "Sign up for free"
   - Enter email and password (min 8 characters)
   - Click "Create Account"

5. **Start Querying:**
   - Type questions in the search box, for example:
     - "Show me sales comparison between Downtown and Airport locations"
     - "What were my top 5 selling products?"
     - "Compare delivery vs dine-in revenue"
     - "Graph hourly sales for Friday vs Saturday"
   - Press Enter or click the Send button

6. **View Results:**
   - Results appear as widgets with:
     - Natural language answer
     - Interactive charts (bar, line, pie, etc.)
     - Data tables
     - SQL query (click database icon to view)

7. **Add More Widgets:**
   - Ask additional questions to create more widgets
   - Each widget can be removed individually

### Complete Setup Steps (Mac/Linux)

1. **Open Terminal 1 - Start Backend:**
   ```bash
   cd clave-take-home/restaurant-analytics-agent
   python run.py
   ```
   Wait for: `INFO:     Uvicorn running on http://127.0.0.1:8000`

2. **Open Terminal 2 - Start Frontend:**
   ```bash
   cd clave-take-home/frontend
   npm run dev
   ```
   Wait for: `Ready - started server on 0.0.0.0:3000`

3. **Open Browser:**
   - Navigate to: `http://localhost:3000`
   - You should see the login/register page

4. **Create an Account:**
   - Click "Sign up for free"
   - Enter email and password (min 8 characters)
   - Click "Create Account"

5. **Start Querying:**
   - Type questions in the search box, for example:
     - "Show me sales comparison between Downtown and Airport locations"
     - "What were my top 5 selling products?"
     - "Compare delivery vs dine-in revenue"
     - "Graph hourly sales for Friday vs Saturday"
   - Press Enter or click the Send button

6. **View Results:**
   - Results appear as widgets with:
     - Natural language answer
     - Interactive charts (bar, line, pie, etc.)
     - Data tables
     - SQL query (click database icon to view)

7. **Add More Widgets:**
   - Ask additional questions to create more widgets
   - Each widget can be removed individually

## Environment Variables

- `NEXT_PUBLIC_API_URL` - Backend API URL (default: `http://localhost:8000`)

## Features in Detail

### Query Input
- Text area for natural language queries
- Keyboard shortcut: Enter to submit
- Example query suggestions
- Loading state during processing

### Chart Widgets
- Supports multiple chart types (bar, line, pie, table)
- Shows query, explanation, and metadata
- Copy SQL query
- Remove widgets
- Responsive layout

### Error Handling
- Network errors
- API errors with suggestions
- Clarification requests with suggestions

## Deployment

### Vercel (Recommended)

1. Push code to GitHub
2. Import project in Vercel
3. Set environment variable `NEXT_PUBLIC_API_URL` to your backend URL
4. Deploy

### Other Platforms

Build the application and deploy the `.next` folder:

```bash
npm run build
```

The output will be in the `.next` directory.

## Notes

- Make sure the backend API is running and accessible from the frontend
- The backend should have CORS enabled (already configured)
- Data is from January 1-4, 2025 only (as per backend configuration)
- Next.js 15 requires Node.js 20+

## Troubleshooting

### Common Issues

#### Import Errors / Module Not Found

**Windows (PowerShell):**
```powershell
# Delete node_modules and package-lock.json
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json

# Clear Next.js cache
Remove-Item -Recurse -Force .next

# Reinstall dependencies
npm install
```

**Windows (Command Prompt):**
```cmd
rmdir /s /q node_modules
del package-lock.json
rmdir /s /q .next
npm install
```

**Mac/Linux:**
```bash
# Delete node_modules and package-lock.json
rm -rf node_modules package-lock.json

# Clear Next.js cache
rm -rf .next

# Reinstall dependencies
npm install
```

#### Port Already in Use

If port 3000 is already in use:

**Windows:**
```powershell
# Find process using port 3000
netstat -ano | findstr :3000

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

**Mac/Linux:**
```bash
# Find process using port 3000
lsof -ti:3000

# Kill the process
kill -9 $(lsof -ti:3000)
```

Or change the port:
```bash
npm run dev -- -p 3001
```

#### Backend Connection Errors

1. **Check if backend is running:**
   - Visit `http://localhost:8000/api/health` in your browser
   - Should return: `{"status":"healthy","database_connected":true}`

2. **Check environment variable:**
   - Verify `.env.local` has: `NEXT_PUBLIC_API_URL=http://localhost:8000`
   - Restart the dev server after changing `.env.local`

3. **CORS errors:**
   - Ensure backend CORS is configured (should be already)
   - Check backend logs for CORS-related errors

#### Node Version Issues

**Check your Node.js version:**
```bash
node --version
```

**Should be 20.x or higher.** If not:

**Windows:**
- Download latest from [nodejs.org](https://nodejs.org/)
- Run installer

**Mac (Homebrew):**
```bash
brew upgrade node
```

#### Build Errors

**Clear all caches and rebuild:**

**Windows:**
```powershell
Remove-Item -Recurse -Force .next
Remove-Item -Recurse -Force node_modules
npm install
npm run build
```

**Mac/Linux:**
```bash
rm -rf .next node_modules
npm install
npm run build
```

### Getting Help

- Check backend logs in the terminal running `python run.py`
- Check frontend logs in the terminal running `npm run dev`
- Open browser DevTools (F12) and check Console tab for errors
- Verify both backend and frontend are running on correct ports
