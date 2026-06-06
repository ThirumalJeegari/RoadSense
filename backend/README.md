# Smart City Backend

FastAPI backend for traffic routing, India smart parking, weather context, and road damage analysis.

## Render Deploy

Create a Render Web Service with:

```text
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /api/health
```

Environment variables:

```text
TOMTOM_API_KEY=your_tomtom_key
REQUEST_TIMEOUT_SECONDS=15
BACKEND_CORS_ORIGINS=https://your-frontend-url.onrender.com,http://localhost:8501,http://127.0.0.1:8501
```

## Local Run

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

