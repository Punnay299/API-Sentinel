# ZombieGuard API Sentinel

ZombieGuard is a next-generation API intelligence and active-remediation platform built for hackathons. It passively observes your API landscape to discover undocumented (Shadow) and dormant (Zombie) endpoints, leveraging a custom Machine Learning scoring engine to assess critical risks.

## Architecture
- **Frontend**: React 18 + Vite, TypeScript, React Query, Vanilla CSS (Dark-mode Glassmorphism)
- **Backend**: FastAPI, SQLite (async via aiosqlite), SQLAlchemy ORM
- **Machine Learning Engine**: Scikit-Learn (Random Forest, Isolation Forest, Custom Heuristics)
- **Real-Time Communication**: Server-Sent Events (SSE) for scans, WebSockets for live monitoring

## Prerequisites
Before you begin, ensure you have the following installed on your system:
- **Node.js** (v18 or higher) & **npm**
- **Python** (v3.10 or higher)
- **Git** (optional, for cloning)

---

## 🚀 Setting Up the Project (First Time Execution)

Follow these step-by-step instructions to get the project running on your local machine from scratch.

### Step 1: Clone the Repository
Open your terminal and clone the project to your local machine (if you haven't already):
```bash
git clone <your-repo-url>
cd API_Sentinel
```
*(Skip this step if you already have the files locally).*

### Step 2: Set Up the Python Virtual Environment (Backend)
It is highly recommended to isolate the Python dependencies using a virtual environment.
Run these commands in the **root** directory of the project:

```bash
# 1. Create a virtual environment named 'venv'
python -m venv venv

# 2. Activate the virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# 3. Install the required backend dependencies
pip install -r requirements.txt
```

⚠️ **Note on Database & ML Initialization**: You do not need to manually run any SQL scripts or train models. The FastAPI application handles this automatically on its first boot! It will build `schema.sql`, seed initial data from `api_inventory.json`, and train the Scikit-Learn classifiers.

### Step 3: Start the FastAPI Backend Server
With your virtual environment still activated, start the backend server:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Leave this terminal window open and running. The backend API is now alive at `http://localhost:8000`. You can view the interactive Swagger documentation at `http://localhost:8000/docs`.

### Step 4: Set Up the React UI (Frontend)
Open a **new, separate terminal window** and navigate to the `frontend` folder inside the project.

```bash
# 1. Navigate to the frontend directory
cd frontend

# 2. Install the Node.js dependencies
npm install
```

### Step 5: Start the Frontend Development Server
After `npm install` finishes, start the Vite development server:

```bash
npm run dev
```

The terminal will provide a local URL. The React UI is now deployed locally! Open your browser and navigate to:
👉 **`http://localhost:5173/`**

---

## 🔄 Running the Application (Subsequent Times)

Once you have completed the first-time setup (installed `pip` and `npm` packages), you only need to start the two servers to run the app in the future.

**Terminal 1 (Backend):**
```bash
cd API_Sentinel
source venv/bin/activate   # (or venv\Scripts\activate on Windows)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 (Frontend):**
```bash
cd API_Sentinel/frontend
npm run dev
```

---

## 🧠 Machine Learning & Data Generation

While the FastAPI backend will automatically train a baseline model on boot if one is missing, you can manually generate fresh synthetic log data and forcefully train the ML engine.

### Generating Synthetic Traffic (API Logs)
To generate the raw hackathon mock data representing API Gateway logs:
```bash
# Ensure your virtual environment is active
python generate_inventory.py
```
*This produces `api_inventory.json` containing realistically shaped traffic for active, zombie, shadow, and orphaned endpoints.*

### Manual ML Training & Retraining
If you tweak the ML architecture in `ml/engine.py` or want to process a new `api_inventory.json` file, you can trigger a forceful retrain.

The simplest way is via the REST API once the backend is running:
```bash
curl -X POST http://localhost:8000/ml/retrain
```
*This forces the `ZombieAPIMLEngine` to re-read the inventory, extract features, train the Random Forest pipelines, and save new `.joblib` model artifacts to the disk.*

---

## Key Features

- **Dashboard**: High-level statistical aggregates on API posture.
- **Agentic ML Engine**: Random Forest classifications grading endpoints as `active`, `deprecated`, `shadow`, or `zombie`.
- **Discovery Scans**: Click "START GLOBAL SCAN" to pipe a simulated network scan over Server-Sent Events (SSE) direct to the UI.
- **Decommission Workflows**: Trigger a live 7-step remediation workflow for any API endpoint via WebSocket traces.
