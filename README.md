# Traffic Video Analytics System

An offline, scalable computer vision pipeline for traffic counting and classification. It detects, tracks, and extracts snapshots of vehicles crossing a defined line or entering a polygon Region of Interest (ROI) in traffic videos, and generates Excel reports grouped by time intervals.

## Core Features

1. **Geometry Setup:** Draw lines or polygons on the first frame of your videos to define counting zones.
2. **Detection & Tracking:** Uses YOLO and ByteTrack to detect and track vehicles, preventing double counting.
3. **Snapshot Extraction:** Automatically captures and saves cropped images of vehicles that enter the defined geometry.
4. **Auto-Classification:** Sorts vehicles into predefined folders based on YOLO predictions.
5. **Excel Reporting:** Aggregates counts into 15-minute intervals (configurable) and generates a structured Excel report.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Detection | YOLO (ultralytics) |
| Tracking | ByteTrack (via `supervision`) |
| Video I/O & UI | OpenCV |
| Export | `openpyxl` (Excel) |

## Project Structure

```
Traffic_Video_Analytics_System/
├── input_videos/       # Place your source videos (.mp4, .avi, .mov) here
├── configs/            # Auto-generated JSON files storing line/polygon coordinates
├── datasets/           # Output directory containing cropped images and Excel reports
├── processed_logs/     # Tracks which videos have already been processed
├── models/             # YOLO model weights (e.g., best.pt)
├── config.py           # Global settings (thresholds, block duration, folders)
├── setup_geometry.py   # Script 1: Draw lines/polygons for your videos
├── processor.py        # Script 2: Process videos, track vehicles, extract crops
└── controller.py       # Script 3: Generate Excel reports from the extracted crops
```

## Setup Instructions

1. **Install Dependencies:**
   Ensure you have Python installed, then install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

2. **Prepare Videos and Models:**
   - Place your traffic videos in the `input_videos/` directory.
   - Ensure your YOLO model weights are in the `models/` directory (configured in `config.py` as `MODEL_PATH = "models/VehicleNet-Y26s/best.pt"`).

## Workflow Pipeline

### Step 1: Define Geometry
Run the geometry setup script to define the counting zone for each video:
```bash
python setup_geometry.py
```
- Select `1` for Polygon or `2` for Line crossing.
- Click to draw points. Press `c` to confirm, `r` to reset.
- Configurations are automatically saved as JSON in `configs/`.

### Step 2: Process Videos
Run the video processor to run detection, tracking, and snapshot extraction:
```bash
python processor.py
```
- The script automatically skips already processed videos.
- Snapshots are saved in `datasets/<video_name>/classified/<class_name>/`.
- Unmapped classes are routed to `Others` or `review_required` folders.

### Step 3: Generate Reports
Run the controller script to aggregate the data and generate Excel reports:
```bash
python controller.py
```
- An Excel file (`traffic_counts.xlsx`) will be generated inside each `datasets/<video_name>/` folder.
- Counts are aggregated into blocks defined by `BLOCK_DURATION_MINUTES` in `config.py` (default: 15 mins).

## Vehicle Categories

The system supports mapping YOLO detections to structured categories, including:
- Two Wheeler, Auto, Cycle
- Car/Jeep/Van/Taxi
- Std Bus & Mini Bus
- LCV, 2 axle, 3 axle, Multi axle
- Tractor, Bullock Cart, Animal Drawn

*(Note: Custom models can be plugged in by changing `MODEL_PATH` and updating the `AUTO_CLASS_MAP` in `processor.py`)*

## GPU Support

The system will automatically detect and use a CUDA-enabled GPU if available, falling back to CPU otherwise.

## License

MIT