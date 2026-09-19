# TravelPilot ✈️

> **"Your trip changes. TravelPilot adapts."**  
> An AI travel co-pilot that plans, manages, and dynamically replans your journey in real time.

---

## 🌟 Project Overview

**TravelPilot** is an autonomous travel planning and real-time disruption management application designed for hackathon agility. Rather than presenting rigid, static itineraries that fall apart the moment a flight is delayed or an attraction is closed, TravelPilot monitors ongoing trips and deploys intelligent adaptations—safeguarding reservations, adjusting time buffers, and balancing budgets automatically.

The project works completely offline out of the box with realistic mock datasets, requiring zero paid API keys to run and evaluate.

---

## 🛠️ Tech Stack

### Frontend
- **Framework:** [React 19](https://react.dev/) + [Vite](https://vitejs.dev/)
- **Styling:** [Tailwind CSS v4](https://tailwindcss.com/)
- **Icons:** [Lucide React](https://lucide.dev/)
- **Architecture:** Context-driven state management with clean service abstractions

### Backend (Skeleton Ready)
- **Framework:** [Python 3](https://www.python.org/) + [FastAPI](https://fastapi.tiangolo.com/)
- **ASGI Server:** [Uvicorn](https://www.uvicorn.org/)
- **Database:** [SQLite](https://www.sqlite.org/) via SQLAlchemy
- **AI Integration:** Abstracted LLM provider architecture designed for future Google Gemini integration

---

## 📂 Project Structure

```text
AI TravelPilot/
├── README.md                 # Project documentation and startup guide
├── .gitignore                # Git ignore rules for Node & Python
├── .env.example              # Environment variables template
│
├── data/
│   └── mock_travel_data.json # Baseline mock travel & disruption scenarios
│
├── frontend/
│   ├── package.json          # Frontend dependencies & scripts
│   ├── vite.config.js        # Vite & Tailwind CSS configuration
│   ├── index.html            # Application HTML shell
│   └── src/
│       ├── main.jsx          # React DOM entry point
│       ├── App.jsx           # Top-level view router & toast provider
│       ├── index.css         # Tailwind base styles and theme
│       ├── components/
│       │   ├── Navbar.jsx    # Top navigation with status pill & page links
│       │   ├── Footer.jsx    # Modern SaaS footer
│       │   └── DisruptionAlertBanner.jsx # Real-time disruption alert bar
│       ├── pages/
│       │   ├── LandingPage.jsx     # Modern AI SaaS hero & feature pillars
│       │   ├── TripCreatePage.jsx  # Constraint-based trip creation form
│       │   ├── DashboardPage.jsx   # Live journey stats, schedule & insights
│       │   ├── ItineraryPage.jsx   # Interactive day timeline with filters
│       │   ├── BudgetPage.jsx      # Financial breakdown & visual charts
│       │   ├── DisruptionPage.jsx  # 5 Disruption simulator controls & log
│       │   └── AIAssistantPage.jsx # Interactive travel co-pilot chat
│       ├── services/
│       │   └── api.js        # Service layer connecting UI to backend/mock
│       ├── hooks/
│       │   └── useTrip.jsx   # Context provider for trips, alerts & chat
│       ├── data/
│       │   └── mockTravelData.js # Comprehensive mock trips & presets
│       └── types/
│           └── index.js      # JSDoc type contracts
│
└── backend/
    ├── requirements.txt      # Minimal Python dependencies
    └── app/
        ├── main.py           # FastAPI entry point with CORS & health endpoint
        ├── api/              # API route controllers
        ├── agents/           # Future Gemini agent implementation
        ├── tools/            # Tools for transit, weather, and scheduling
        ├── models/           # Pydantic schemas & DB models
        ├── services/         # Pluggable LLM provider services
        └── database/         # SQLite database session configuration
```

---

## 🚀 How to Run the Frontend

The frontend is completely self-contained and runs with mock data out of the box.

### Prerequisites
- [Node.js](https://nodejs.org/) (v18 or higher recommended)
- `npm`

### Steps
1. Open a terminal in the `frontend` directory:
   ```bash
   cd frontend
   ```

2. Install dependencies (if not already installed):
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open your browser and navigate to:
   ```text
   http://localhost:5173
   ```

5. Build for production (verifies bundling):
   ```bash
   npm run build
   ```

---

## ⚡ How to Run the Backend

The backend is structured as a lightweight FastAPI skeleton.

### Prerequisites
- [Python 3.10+](https://www.python.org/)

### Steps
1. Open a terminal in the `backend` directory:
   ```bash
   cd backend
   ```

2. (Optional but recommended) Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Launch the FastAPI server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

5. Test the health endpoint:
   ```text
   http://127.0.0.1:8000/api/health
   ```
   Interactive Swagger docs are available at `http://127.0.0.1:8000/docs`.

---

## 🧭 Pages Implemented in the Frontend

1. **Landing Page:** Hero with *"Your trip changes. TravelPilot adapts."*, how it works, and 4 feature pillars (AI planning, smart optimization, disruption management, zero-API-key local demo).
2. **Trip Creation Page:** Interactive form with destination, dates, budget, travelers, interests, travel style, transit preference, and 1-click sample presets.
3. **Trip Dashboard:** High-level summary of active trip, budget burn rate, remaining buffer, today's schedule, upcoming activities, and AI insights.
4. **Itinerary Page:** Day-by-day interactive timeline with time, activity duration, location, cost, transportation pills, and status tags. Includes an "Add Activity" modal.
5. **Budget Page:** Total budget, estimated spending, remaining margin, allocation breakdown by category (accommodation, transport, activities, food, misc), and visual charts.
6. **Disruption Center:** Real-time simulation controls for:
   - Activity cancelled
   - Transportation delayed
   - Hotel unavailable
   - Budget reduced
   - Custom disruption builder with live AI adaptation logging
7. **AI Assistant:** Chat interface with quick prompt chips, typing simulation, and context-aware responses calibrated to the active journey.
