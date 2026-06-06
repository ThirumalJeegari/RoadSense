# Smart City Frontend

Streamlit dashboard for the Smart Cities project.

## Render Deploy

Create a Render Web Service with:

```text
Root Directory: frontend
Build Command: pip install -r requirements.txt
Start Command: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

Environment variable:

```text
BACKEND_URL=https://your-backend-service.onrender.com
```

## Local Run

```powershell
cd frontend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

