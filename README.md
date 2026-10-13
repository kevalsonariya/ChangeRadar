# ChangeRadar 📡

> **Real-time Webpage Sentinel & Deadline Tracker**\
> *A 5th Semester Software Group Project (SGP) College MVP built for rapid deployment.*

ChangeRadar monitors supported public webpages (such as university circulars, scholarship portals, and assignment boards), detects meaningful content changes using text difference analysis, maintains an audit history with visual diffs, and extracts upcoming deadlines to help students never miss a critical cutoff.

---

## 🚀 Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend Framework** | **React 19 + Vite** | High-performance SPA with TypeScript |
| **Styling** | **Tailwind CSS** | Polished dark navy & teal SaaS theme |
| **Icons** | **Lucide React** | Clean, consistent interface iconography |
| **HTTP Client (UI)** | **Axios** | Typed API service communicating with backend |
| **Backend Framework** | **Python FastAPI** | Asynchronous REST API service |
| **Database** | **SQLite (SQLAlchemy)** | Zero-config, lightweight relational storage (`changeradar.db`) |
| **Web Scraping** | **HTTPX + BeautifulSoup4**| Robust asynchronous HTML fetching & content parsing |
| **Difference Engine** | **Python `difflib`** | Standard library unified text delta computation |

---

## 🎨 Theme & User Interface

- **Theme**: Dark Navy (`#070d18`, `#0b1324`, `#14223e`) with vibrant Teal accents (`#14b8a6`, `#2dd4bf`).
- **Sidebar Navigation**:
  - 📊 **Dashboard / Command Center**: Real-time summary cards, latest content diff viewer, and urgent deadline alerts.
  - 🌐 **Monitored Websites**: Target management, CSS selectors, polling intervals, and "Check Now" triggers.
  - 🕒 **Change History**: Audit log of modifications, additions, and deletions with unified and side-by-side diff viewers.
  - 📅 **Deadlines**: Extracted key dates, days-remaining countdowns, priority tags, and source links.
  - 🔔 **Notifications**: System and change alerts with mark-as-read workflows.
  - ⚙️ **Settings**: Polling engine configuration, User-Agent customization, and FastAPI backend health tester.
- **Graceful Demonstration Mode**:
  - The frontend works immediately out of the box with realistic demonstration data for visual prototyping.
  - When the FastAPI backend is launched, the frontend automatically detects the live API and syncs in real-time.

---

## 📂 Project Structure

```text
ChangeRadar/
├── backend/
│   ├── app/
│   │   ├── models/           # SQLAlchemy database models (Website, Snapshot, Change, Notification, Deadline)
│   │   ├── routers/          # FastAPI routers (websites, changes, deadlines, notifications)
│   │   ├── schemas/          # Pydantic schemas and request/response validation
│   │   ├── services/         # Scraper, differ, and website database CRUD service
│   │   ├── database.py       # SQLite engine, sessionmaker, and table initializer
│   │   └── main.py           # FastAPI entrypoint with CORS middleware & lifespan
│   ├── requirements.txt      # Python dependencies
│   └── changeradar.db        # Persistent SQLite database file
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/       # Card, Badge, DiffViewer, EmptyState, LoadingSpinner
│   │   │   ├── layout/       # Sidebar, Navbar
│   │   │   └── modals/       # AddWebsiteModal
│   │   ├── data/             # Mock demonstration data
│   │   ├── pages/            # DashboardView, WatchlistView, ChangeHistoryView, DeadlinesView, etc.
│   │   ├── services/         # Typed Axios API layer
│   │   ├── types/            # TypeScript interfaces
│   │   ├── App.tsx           # State management & view routing
│   │   ├── index.css         # Tailwind base & dark theme tokens
│   │   └── main.tsx          # Application mount
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
│
└── README.md
```

---

## 🛠️ Getting Started

### 1. Backend Setup & Run Commands (FastAPI + SQLite)

```powershell
# Navigate to backend directory
cd "e:\DEGREE\5TH SEM\SGP\ChangeRadar\backend"

# (Optional) Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

# Install required dependencies
pip install -r requirements.txt

# Start the FastAPI server with Uvicorn
uvicorn app.main:app --reload --port 8000
```

Alternatively, from the project root:
```powershell
uvicorn backend.app.main:app --reload --port 8000
```

The backend API will be available at:
- **API Root**: `http://localhost:8000/`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **ReDoc Specification**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

#### Available API Endpoints:
- `GET /health` — Service health and active SQLite connection check
- `GET /websites` or `GET /api/websites` — List all monitored websites
- `POST /websites` or `POST /api/websites` — Register a new website to monitor (validates URL and prevents duplicates)
- `GET /websites/{id}` or `GET /api/websites/{id}` — Get details for a specific website
- `DELETE /websites/{id}` or `DELETE /api/websites/{id}` — Delete a website and related data
- `GET /api/changes` — List detected content diffs
- `GET /api/deadlines` — List upcoming deadlines
- `GET /api/deadlines/summary` — Aggregate counts for dashboard summary
- `GET /api/notifications` — List system and change alerts

---

### 2. Frontend Setup (React + Vite)

```powershell
# Navigate to frontend directory
cd "e:\DEGREE\5TH SEM\SGP\ChangeRadar\frontend"

# Install frontend dependencies
npm install --legacy-peer-deps

# Start Vite development server
npm run dev
```

The frontend will be available at: **`http://localhost:5173`**

To test or generate a production build:
```powershell
npm run build
```

---

## 🗄️ Database Architecture (SQLite Models)

1. **`websites`**: Stores target URL, name, status (`active`, `warning`, `error`, `paused`), check interval, category, selector, and timestamps.
2. **`snapshots`**: Stores captured webpage text, SHA-256 content hash, capture timestamp, and foreign key link to `website_id`.
3. **`changes`**: Records detected text modifications, line addition/deletion counts, foreign keys to previous and new snapshots, diff unified text, and change summary.
4. **`notifications`**: Stores alert title, message, creation timestamp, read status, and associations to `website_id` and `change_id`.
5. **`deadlines`**: Tracks title, description, due date, urgency priority (`high`, `medium`, `low`), days left, and completion status.
