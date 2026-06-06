# RoadSense

RoadSense is a smart road and city mobility platform for Indian locations. It helps users monitor traffic routes, find nearby parking availability, and view damaged road areas from one professional dashboard.

The project is built for a hackathon and includes login/signup, protected dashboard access, real map-based location search, smart parking points, road damage route reporting, and Razorpay Prime subscription support.

## Project Highlights

- Traffic Management with route map
- Smart Parking with available and occupied slots
- Road Damage Detection on route map
- India map search for cities, villages, localities, roads, and gullies
- Login, signup, logout, and profile page
- Protected dashboard access
- Razorpay Prime subscription flow
- Prime demo activation for hackathon presentation
- Render-ready backend and frontend deployment

## Problem Statement

Indian roads face three common operational problems:

- Traffic congestion between important locations
- Lack of parking visibility in busy areas
- Damaged roads that need inspection and repair priority

RoadSense combines these problems into one dashboard so a user can enter a starting location, destination, and parking area, then view traffic, parking, and road damage insights on a map.

## Main Features

### 1. Traffic Management

Users can enter:

```txt
Starting location
Destination location
```

The system searches real Indian map locations and displays a route on the map.

Traffic route sections are colored as:

```txt
Blue   = Normal traffic
Yellow = Moderate traffic
Red    = Heavy traffic
```

Traffic data behavior:

- Uses OpenStreetMap/Nominatim for Indian location search
- Uses OSRM for route geometry
- Supports TomTom API for traffic-aware data when a key is added
- Falls back to demo traffic coloring if TomTom is not configured

### 2. Smart Parking

Users can search parking near:

```txt
City
Village
Road
Gully
Locality
```

The system uses OpenStreetMap parking objects and displays parking points on the map.

Parking markers:

```txt
Green = Available
Red   = Full
```

Parking panel shows:

- Parking location
- Parking points
- Vacant slots
- Occupied slots
- Availability percentage
- Parking type
- Access type

### 3. Road Damage Detection

Road damage detection is map-based in the frontend. It works on the selected route and generates road damage points with operational details.

It shows:

- Starting location
- Destination
- Damage points
- Severity
- Affected area
- Road segment
- Maintenance priority
- Suggested action

The current frontend does not require photo or video upload. It focuses on map-based road damage reporting.

### 4. India Location Search

RoadSense supports real location search using OpenStreetMap/Nominatim.

Users can search:

- Cities
- Towns
- Villages
- Districts
- Localities
- Roads
- Streets
- Gullies or lanes if available in OpenStreetMap

Important note: a gully or small road will appear only if it exists in OpenStreetMap data.

### 5. Authentication

The app includes:

- Signup
- Login
- Logout
- Profile details
- Protected dashboard

Dashboard access requires login. If a user opens the dashboard without login, the app shows a login-required page.

After login, the Home page shows:

- Name
- Email
- Role
- Plan
- Subscription status

### 6. Prime Subscription

RoadSense includes a Prime subscription page with Razorpay support.

Prime features include:

- Predictive traffic risk
- Expanded parking coverage
- Road repair priority queue
- Operations playbook
- Faster refresh option
- Larger parking search coverage

For hackathon demonstration, the app also includes:

```txt
Activate Prime Demo
```

This upgrades the logged-in user to Prime demo mode without requiring a completed Razorpay payment.

## Tech Stack

### Frontend

```txt
React
Vite
Leaflet
Lucide React Icons
CSS
```

### Backend

```txt
Python
FastAPI
Uvicorn
HTTPX
python-dotenv
python-multipart
SQLAlchemy
psycopg2-binary
Pillow
NumPy
OpenCV headless
```

### External Services

```txt
OpenStreetMap Nominatim - India location search
OpenStreetMap Overpass - Parking data
OSRM - Route geometry
TomTom API - Optional live traffic support
Razorpay - Optional Prime subscription support
SQLite - Local database
PostgreSQL - Render/production database
Render - Deployment
```

## Project Structure

```txt
RoadSense/
|-- backend/
|   |-- app/
|   |   |-- core/
|   |   |   `-- config.py
|   |   |-- services/
|   |   |   |-- auth.py
|   |   |   |-- cache.py
|   |   |   |-- database.py
|   |   |   |-- geo.py
|   |   |   |-- india_locations.py
|   |   |   |-- parking.py
|   |   |   |-- payments.py
|   |   |   |-- road_damage.py
|   |   |   |-- traffic.py
|   |   |   `-- weather.py
|   |   |-- main.py
|   |   `-- schemas.py
|   |-- requirements.txt
|   |-- render.yaml
|   `-- .env.example
|-- frontend/
|   |-- src/
|   |   |-- components/
|   |   |   `-- MapPanel.jsx
|   |   |-- services/
|   |   |   `-- api.js
|   |   |-- utils/
|   |   |   `-- roadDamage.js
|   |   |-- main.jsx
|   |   `-- styles.css
|   |-- index.html
|   |-- package.json
|   |-- package-lock.json
|   |-- vite.config.js
|   `-- .env.example
`-- README.md
```

## Backend API

Base URL locally:

```txt
http://127.0.0.1:8000
```

Important endpoints:

```txt
GET  /api/health
POST /api/auth/signup
POST /api/auth/login
GET  /api/auth/me
POST /api/auth/logout
GET  /api/india-locations
GET  /api/location-search
GET  /api/traffic-route
GET  /api/parking
GET  /api/dashboard
POST /api/subscriptions/prime
POST /api/subscriptions/prime/activate-demo
POST /api/road-damage/analyze
```

### Example API Requests

Search Indian locations:

```txt
GET /api/location-search?q=MG Road Bengaluru&limit=8
```

Get traffic route:

```txt
GET /api/traffic-route?start=Chennai&end=Bengaluru
```

Get parking:

```txt
GET /api/parking?provider=india&city=Bengaluru&limit=180
```

Health check:

```txt
GET /api/health
```

## Environment Variables

### Backend Environment Variables

Create a backend `.env` file from:

```txt
backend/.env.example
```

Variables:

```txt
BACKEND_CORS_ORIGINS=http://localhost:8501,http://127.0.0.1:8501
TOMTOM_API_KEY=
REQUEST_TIMEOUT_SECONDS=15
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_PRIME_PLAN_ID=
RAZORPAY_PRIME_TOTAL_COUNT=12
AUTH_TOKEN_SECRET=change_this_to_a_long_random_secret
AUTH_TOKEN_TTL_SECONDS=86400
DATABASE_URL=sqlite:///./roadsense.db
```

Explanation:

| Variable | Required | Description |
| --- | --- | --- |
| `BACKEND_CORS_ORIGINS` | Yes | Frontend URLs allowed to call backend |
| `TOMTOM_API_KEY` | Optional | Enables TomTom traffic support |
| `REQUEST_TIMEOUT_SECONDS` | Yes | Timeout for external API calls |
| `RAZORPAY_KEY_ID` | Optional | Razorpay key ID |
| `RAZORPAY_KEY_SECRET` | Optional | Razorpay key secret |
| `RAZORPAY_PRIME_PLAN_ID` | Optional | Razorpay subscription plan ID |
| `RAZORPAY_PRIME_TOTAL_COUNT` | Optional | Subscription cycle count |
| `AUTH_TOKEN_SECRET` | Yes | Secret used for login tokens |
| `AUTH_TOKEN_TTL_SECONDS` | Yes | Login token lifetime in seconds |
| `DATABASE_URL` | Yes | Database connection URL for users and subscriptions |

Beginner minimum backend variables:

```txt
BACKEND_CORS_ORIGINS=http://localhost:8501,http://127.0.0.1:8501
REQUEST_TIMEOUT_SECONDS=15
AUTH_TOKEN_SECRET=roadsense_login_secret_2026_make_it_long
AUTH_TOKEN_TTL_SECONDS=86400
RAZORPAY_PRIME_TOTAL_COUNT=12
DATABASE_URL=sqlite:///./roadsense.db
```

Local database:

```txt
DATABASE_URL=sqlite:///./roadsense.db
```

Render PostgreSQL database:

```txt
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE
```

RoadSense automatically creates the `users` table on backend startup.

### Frontend Environment Variables

Create a frontend `.env` file from:

```txt
frontend/.env.example
```

Local value:

```txt
VITE_BACKEND_URL=http://127.0.0.1:8000
```

Render value:

```txt
VITE_BACKEND_URL=https://your-backend-service.onrender.com

```

## Local Setup

### 1. Clone the Repository

```bash
git clone https://github.com/ThirumalJeegari/RoadSense.git
cd RoadSense
```

### 2. Run Backend Locally

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Backend will run at:

```txt
http://127.0.0.1:8000
```

Health check:

```txt
http://127.0.0.1:8000/api/health
```

### 3. Run Frontend Locally

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend will run at:

```txt
http://127.0.0.1:8501
```

## Render Deployment

Deploy RoadSense as two services:

1. Backend as Web Service
2. Frontend as Static Site or Node Web Service

### Backend on Render

Create a new Web Service:

```txt
Root Directory: backend
Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /api/health
```

Backend environment variables:

```txt
PYTHON_VERSION=3.11.9
BACKEND_CORS_ORIGINS=https://your-frontend-url.onrender.com,http://localhost:8501,http://127.0.0.1:8501
REQUEST_TIMEOUT_SECONDS=15
AUTH_TOKEN_SECRET=roadsense_login_secret_2026_make_it_long
AUTH_TOKEN_TTL_SECONDS=86400
TOMTOM_API_KEY=your_tomtom_api_key
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
RAZORPAY_PRIME_PLAN_ID=your_razorpay_plan_id
RAZORPAY_PRIME_TOTAL_COUNT=12
DATABASE_URL=your_render_postgresql_external_database_url
```

TomTom and Razorpay variables can be left empty if you want demo mode.

For permanent login storage on Render:

1. Create a PostgreSQL database in Render.
2. Copy its External Database URL.
3. Add it to backend environment variables as `DATABASE_URL`.
4. Redeploy the backend.

Without PostgreSQL on Render, local SQLite can work for development but is not ideal for production persistence.

### Frontend on Render as Static Site

Recommended option:

```txt
Root Directory: frontend
Build Command: npm install && npm run build
Publish Directory: dist
```

Frontend environment variable:

```txt
VITE_BACKEND_URL=https://your-backend-service.onrender.com
```

### Frontend on Render as Web Service

If you choose Web Service instead of Static Site:

```txt
Root Directory: frontend
Language: Node
Build Command: npm install && npm run build
Start Command: npm run start -- --port $PORT
Health Check Path: /
```

Frontend environment variable:

```txt
VITE_BACKEND_URL=https://your-backend-service.onrender.com
```

Important: frontend health check path should be:

```txt
/
```

Do not use `/healthz` for frontend.

## Razorpay Setup

To enable live Razorpay subscription:

1. Login to Razorpay Dashboard
2. Go to Settings
3. Create API Keys
4. Copy Key ID and Key Secret
5. Go to Subscriptions
6. Create a Plan
7. Copy Plan ID

Add these to Render backend environment:

```txt
RAZORPAY_KEY_ID=rzp_test_or_live_key_id
RAZORPAY_KEY_SECRET=your_key_secret
RAZORPAY_PRIME_PLAN_ID=plan_xxxxxxxxx
RAZORPAY_PRIME_TOTAL_COUNT=12
```

## TomTom Setup

To enable TomTom traffic:

1. Create a TomTom Developer account
2. Create an app
3. Copy the API key
4. Add it to Render backend:

```txt
TOMTOM_API_KEY=your_tomtom_api_key
```

If TomTom is not configured, RoadSense still works using OSRM and demo traffic coloring.

## Demo Flow

Use this flow during a hackathon presentation:

1. Open RoadSense frontend
2. Create an account using Signup
3. Login
4. Home page shows profile details
5. Open Dashboard
6. Search start and destination using map search
7. View traffic route on map
8. Open Smart Parking tab
9. Search parking area
10. View parking points and slot data
11. Open Road Damage Detection tab
12. View road damage points and maintenance data
13. Open Subscription page
14. Click Activate Prime Demo
15. Return to Dashboard and show Prime insights

## Important Notes

- This project uses public map APIs, so very small gullies appear only if they exist in OpenStreetMap.
- TomTom API is optional.
- Razorpay API is optional for demo mode.
- Current frontend road damage detection is map-based and does not require image upload.
- Backend has a road damage image endpoint that can be expanded later.
- User accounts are stored in a database through SQLAlchemy.
- Local development uses SQLite by default.
- Render production should use PostgreSQL through `DATABASE_URL`.

## Future Improvements

- Add Razorpay webhook verification
- Add admin dashboard
- Add real municipal parking datasets
- Add citizen complaint reporting
- Add AI image-based road damage detection in the frontend
- Add SMS/email alerts
- Add mobile app
- Add route alternatives and fuel/time savings

## Author
Jeegari Thirumal
