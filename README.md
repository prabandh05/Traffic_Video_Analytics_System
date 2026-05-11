# Traffic Video Analytics System

**Offline Scalable Traffic Counting System** — Detect, track, and count vehicles crossing a defined line in traffic videos. Export results to Excel.

## What This Does

1. **Upload** traffic videos (web UI or local folder)
2. **Draw** a counting line on the first frame
3. **Detect** vehicles using YOLOv8m
4. **Track** vehicles using ByteTrack (prevents double counting)
5. **Count** vehicles crossing the line (1 car = 1 count, not 200)
6. **Classify** vehicles: Two Wheeler, Four Wheeler, Commercial, Auto
7. **Export** results to Excel/CSV
8. **Process** multiple videos in parallel (GPU-aware)

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Detection | YOLOv8m (ultralytics) |
| Tracking | ByteTrack (built into ultralytics) |
| Backend | Python + FastAPI |
| Frontend | React + Vite |
| Video I/O | OpenCV |
| Export | openpyxl (Excel) + csv |
| Parallel | ThreadPoolExecutor (GPU-aware) |

## Quick Start

### 1. Backend Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Start backend server
cd backend
uvicorn main:app --reload --port 8000
```

The backend will:
- Download YOLOv8m weights on first run (~50MB)
- Create directory structure automatically
- Detect GPU and set optimal worker count

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173` and proxies API calls to the backend.

### 3. Usage

1. Open `http://localhost:5173`
2. Upload a traffic video (MP4, AVI, MOV, MKV)
3. Click **Draw Line** → click two points on the frame
4. Click **Process** → wait for detection + tracking
5. View results → download Excel/CSV

### API Docs

FastAPI auto-generates interactive docs at: `http://localhost:8000/docs`

## Project Structure

```
Traffic_Video_Analytics_System/
├── backend/
│   ├── api/            # FastAPI routes + Pydantic models
│   ├── detection/      # YOLOv8m detector + ByteTrack config
│   ├── tracking/       # Vehicle track state management
│   ├── processing/     # Video processor, batch processor, GPU manager
│   ├── exports/        # Excel + CSV exporters
│   ├── utils/          # Classifier, line drawer utilities
│   └── main.py         # FastAPI app entry point
├── frontend/           # React + Vite dashboard
│   └── src/
│       ├── components/ # VideoUpload, VideoCard, LineDrawer
│       ├── api.js      # API client
│       └── App.jsx     # Main app component
├── videos/             # Video storage (pending/processing/completed)
├── outputs/            # Excel/CSV output files
├── models/             # YOLO model weights (auto-downloaded)
└── requirements.txt    # Python dependencies
```

## How Counting Works

```
Video → Frame Reader → YOLO Detection → ByteTrack Tracking → Line Crossing Check → Count
```

1. Each vehicle gets a unique **track ID** from ByteTrack
2. The vehicle's **centroid** is tracked across frames
3. When the centroid crosses from one side of the line to the other → **count +1**
4. That track ID is marked as counted → **never counted again**

This is why 1 car appearing in 200 frames = **1 count**, not 200.

## Vehicle Categories

| Category | YOLO COCO Classes |
|----------|------------------|
| Two Wheeler | motorcycle, bicycle |
| Four Wheeler | car |
| Commercial | bus, truck |
| Auto | *(requires custom model — Phase 6)* |

> **Note:** Standard YOLO does not detect Indian auto-rickshaws. The pipeline is built to support custom model fine-tuning in Phase 6.

## GPU Support

The system auto-detects GPU and allocates workers:

| GPU VRAM | Parallel Videos |
|----------|----------------|
| No GPU | 1 (CPU) |
| 4 GB | 1 |
| 8 GB | 2 |
| 16 GB | 4 |

## License

MIT