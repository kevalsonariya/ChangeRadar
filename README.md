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
| **Database** | **SQLite (SQLAlchemy)** | Zero-config, lightweight relational storage |
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
│   │   ├── models/           # SQLAlchemy database models (Website, Change, Deadline)
│   │   ├── routers/          # FastAPI routers (websites, changes, deadlines, notifications)
│   │   ├── schemas/          # Pydantic schemas and request/response models
│   │   ├── services/         # Scraper (HTTPX + BS4) and Differ (difflib)
│   │   ├── database.py       # SQLite engine and session management
│   │   └── main.py           # FastAPI entrypoint with CORS middleware
│   └── requirements.txt      # Python dependencies
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

### 1. Frontend Setup (React + Vite)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (already prepared)
npm install --legacy-peer-deps

# Start Vite development server
npm run dev
```

The frontend will be available at: **`http://localhost:5173`**

To test or generate a production build:
```bash
npm run build
```

---

### 2. Backend Setup (FastAPI + Python)

```bash
# Navigate to backend directory
cd backend

# Create a virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt

# Start the FastAPI server with uvicorn
uvicorn app.main:app --reload --port 8000
```

The backend API will be available at:
- **API Root**: `http://localhost:8000`
- **Swagger Documentation**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`

---

## ⚡ Key Features

1. **Intelligent Diff Viewer**: Side-by-side and unified code/text diff views highlighting insertions in emerald and deletions in rose.
2. **Selector Isolation**: Monitor either entire webpage text or target a specific CSS selector (e.g. `.circular-table` or `#announcements`).
3. **Deadline Urgency Badges**: Automatic categorization into Critical (≤ 3 days), Upcoming, or Passed.
4. **Resilient API Architecture**: Transparent error handling that alerts the user if the backend is down without crashing the UI.
