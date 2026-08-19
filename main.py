import os
import gc
import cv2
import torch
import numpy as np
import supervision as sv

from ultralytics import YOLO
from config import *

# =========================================================
# CREATE DATASET FOLDERS
# =========================================================

os.makedirs(DATASET_FOLDER, exist_ok=True)

# =========================================================
# LOAD MODEL
# =========================================================

print("[INFO] Loading YOLO model...")

device = "cuda" if torch.cuda.is_available() else "cpu"

print(f"[INFO] Using device: {device}")

model = YOLO(MODEL_PATH)

model.to(device)

print(model.names)

# =========================================================
# TRACKER
# =========================================================

tracker = sv.ByteTrack(

    track_activation_threshold=0.1,

    lost_track_buffer=30
)

# =========================================================
# OPEN VIDEO
# =========================================================

cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():

    print("[ERROR] Could not open video.")

    exit()

# =========================================================
# VIDEO INFO
# =========================================================

fps = cap.get(cv2.CAP_PROP_FPS)

# =========================================================
# CLASS MAPS
# =========================================================

AUTO_CLASS_MAP = {

    "Two-wheeler": "Two Wheeler",

    "Three-wheeler": "Auto",

    "Hatchback": "Car",

    "Sedan": "Car",

    "SUV": "Car",

    "MUV": "Car",

    "Van": "Car",

    "Tempo-traveller": "Car",

    "Bicycle": "Cycle"
}

REVIEW_REQUIRED_MAP = {

    "Bus": "Std Bus",

    "Mini-bus": "Mini Bus",

    "Truck": "LCV",

    "LCV": "LCV",

    "Others": "Others"
}

# =========================================================
# GEOMETRY MODE
# =========================================================

MODE = input(

    "\nSelect Mode:\n"

    "1 -> Polygon ROI\n"

    "2 -> Line Crossing\n\n"

    "Enter choice: "

)

if MODE == "1":

    MODE = "polygon"

elif MODE == "2":

    MODE = "line"

else:

    print("[ERROR] Invalid mode.")

    exit()

# =========================================================
# DRAW GEOMETRY
# =========================================================

geometry_points = []

ret, first_frame = cap.read()

if not ret:

    print("[ERROR] Could not read first frame.")

    exit()

first_frame = cv2.resize(

    first_frame,

    (1280, 720)
)

clone = first_frame.copy()

def draw_geometry(event, x, y, flags, param):

    global geometry_points

    if event == cv2.EVENT_LBUTTONDOWN:

        if MODE == "line":

            if len(geometry_points) < 2:

                geometry_points.append((x, y))

                print(f"[POINT ADDED] ({x}, {y})")

        else:

            geometry_points.append((x, y))

            print(f"[POINT ADDED] ({x}, {y})")

window_name = (

    "Draw Line"

    if MODE == "line"

    else "Draw Polygon"
)

cv2.namedWindow(window_name)

cv2.setMouseCallback(

    window_name,

    draw_geometry
)

print("\n========== DRAW GEOMETRY ==========")

if MODE == "line":

    print("Select 2 points for line")

else:

    print("Select polygon points")

print("'c' = Confirm")
print("'r' = Reset")
print("'q' = Quit")

print("===================================\n")

while True:

    temp_frame = clone.copy()

    for point in geometry_points:

        cv2.circle(

            temp_frame,

            point,

            5,

            (0, 255, 0),

            -1
        )

    if MODE == "line":

        if len(geometry_points) == 2:

            cv2.line(

                temp_frame,

                geometry_points[0],

                geometry_points[1],

                (0, 0, 255),

                2
            )

    else:

        if len(geometry_points) > 1:

            cv2.polylines(

                temp_frame,

                [np.array(geometry_points)],

                False,

                (0, 255, 255),

                POLYGON_THICKNESS
            )

    cv2.imshow(

        window_name,

        temp_frame
    )

    key = cv2.waitKey(1)

    if key == ord('r'):

        geometry_points = []

    elif key == ord('c'):

        if MODE == "line":

            if len(geometry_points) == 2:

                break

        else:

            if len(geometry_points) >= 3:

                break

    elif key == ord('q'):

        exit()

cv2.destroyWindow(window_name)

if MODE == "polygon":

    polygon_np = np.array(

        geometry_points,

        dtype=np.int32
    )

# =========================================================
# RESET VIDEO
# =========================================================

cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

# =========================================================
# MEMORY
# =========================================================

vehicle_memory = {}

last_detections = sv.Detections.empty()

snapshot_count = 0

frame_count = 0

# =========================================================
# LINE FUNCTION
# =========================================================

def side_of_line(point, line_start, line_end):

    return (

        (line_end[0] - line_start[0]) *

        (point[1] - line_start[1])

        -

        (line_end[1] - line_start[1]) *

        (point[0] - line_start[0])

    )

# =========================================================
# FRAME LOOP
# =========================================================

while True:

    ret, frame = cap.read()

    if not ret:
        break

    # =====================================================
    # OPTIONAL RESIZE FOR MEMORY/STABILITY
    # =====================================================

    frame = cv2.resize(

        frame,

        (1280, 720)
    )

    raw_frame = frame.copy()

    frame_count += 1

    # =====================================================
    # TIMESTAMP
    # =====================================================

    current_seconds = frame_count / fps

    hours = int(current_seconds // 3600)

    minutes = int((current_seconds % 3600) // 60)

    seconds = int(current_seconds % 60)

    timestamp = (

        f"{hours:02d}-"

        f"{minutes:02d}-"

        f"{seconds:02d}"
    )

    # =====================================================
    # BLOCK
    # =====================================================

    block_number = int(

        current_seconds //

        (BLOCK_DURATION_MINUTES * 60)

    ) + 1

    block_name = f"clock{block_number}"

    # =====================================================
    # YOLO DETECTION
    # =====================================================

    run_detection = (

        frame_count %

        DETECTION_INTERVAL == 0
    )

    if run_detection:

        results = model(

            frame,

            conf=CONFIDENCE_THRESHOLD,

            imgsz=INFERENCE_SIZE,

            half=True,

            verbose=False

        )[0]

        detections = sv.Detections.from_ultralytics(

            results
        )

        last_detections = detections

    else:

        detections = last_detections

    # =====================================================
    # TRACKER
    # =====================================================

    tracked_detections = tracker.update_with_detections(

        detections
    )

    # =====================================================
    # DRAW GEOMETRY
    # =====================================================

    if DEBUG_MODE:

        if MODE == "polygon":

            cv2.polylines(

                frame,

                [polygon_np],

                True,

                (0, 0, 255),

                POLYGON_THICKNESS
            )

        else:

            cv2.line(

                frame,

                geometry_points[0],

                geometry_points[1],

                (0, 0, 255),

                2
            )

    # =====================================================
    # PROCESS DETECTIONS
    # =====================================================

    for detection in tracked_detections:

        x1, y1, x2, y2 = detection[0]

        class_id = detection[3]

        track_id = int(detection[4])

        x1 = int(x1)
        y1 = int(y1)
        x2 = int(x2)
        y2 = int(y2)

        class_name = model.names[class_id]

        # =================================================
        # CENTER POINT
        # =================================================

        center_x = int((x1 + x2) / 2)

        center_y = int((y1 + y2) / 2)

        # =================================================
        # MEMORY INIT
        # =================================================

        if track_id not in vehicle_memory:

            vehicle_memory[track_id] = {

                "inside": False,

                "saved": False,

                "best_area": 0,

                "best_crop": None,

                "best_class": class_name,

                "timestamp": timestamp,

                "previous_side": None,

                "last_seen": frame_count
            }

        memory = vehicle_memory[track_id]

        memory["last_seen"] = frame_count

        # =================================================
        # POLYGON MODE
        # =================================================

        if MODE == "polygon":

            inside_geometry = cv2.pointPolygonTest(

                polygon_np,

                (center_x, center_y),

                False

            ) >= 0

        # =================================================
        # LINE MODE
        # =================================================

        else:

            current_side = side_of_line(

                (center_x, center_y),

                geometry_points[0],

                geometry_points[1]
            )

            previous_side = memory["previous_side"]

            inside_geometry = True

        # =================================================
        # INSIDE GEOMETRY
        # =================================================

        if inside_geometry:

            memory["inside"] = True

            width = x2 - x1

            height = y2 - y1

            area = width * height

            if area > memory["best_area"]:

                crop = raw_frame[y1:y2, x1:x2].copy()

                if crop.size > 0:

                    memory["best_area"] = area

                    memory["best_crop"] = crop

                    memory["best_class"] = class_name

                    memory["timestamp"] = timestamp

            # =================================================
            # LINE MODE SAVE
            # =================================================

            if MODE == "line":

                crossed = False

                if previous_side is not None:

                    if previous_side * current_side < 0:

                        crossed = True

                if (

                    crossed

                    and

                    not memory["saved"]

                    and

                    memory["best_crop"] is not None
                ):

                    predicted_class = memory["best_class"]

                    # =========================================
                    # AUTO CLASSIFIED
                    # =========================================

                    if predicted_class in AUTO_CLASS_MAP:

                        folder_name = AUTO_CLASS_MAP[
                            predicted_class
                        ]

                        save_folder = os.path.join(

                            DATASET_FOLDER,

                            "classified",

                            folder_name

                        )

                    # =========================================
                    # REVIEW REQUIRED
                    # =========================================

                    else:

                        folder_name = REVIEW_REQUIRED_MAP.get(

                            predicted_class,

                            "Others"
                        )

                        save_folder = os.path.join(

                            DATASET_FOLDER,

                            "review_required",

                            folder_name
                        )

                    os.makedirs(

                        save_folder,

                        exist_ok=True
                    )

                    snapshot_name = (

                        f"{block_name}_"

                        f"{track_id}_"

                        f"{memory['timestamp']}.jpg"
                    )

                    snapshot_path = os.path.join(

                        save_folder,

                        snapshot_name
                    )

                    cv2.imwrite(

                        snapshot_path,

                        memory["best_crop"]
                    )

                    memory["saved"] = True

                    snapshot_count += 1

                    print(

                        f"[LINE SAVED] "

                        f"{snapshot_name}"
                    )

                memory["previous_side"] = current_side

            color = (0, 255, 0)

        # =================================================
        # POLYGON SAVE
        # =================================================

        elif MODE == "polygon":

            if (

                memory["inside"]

                and

                not memory["saved"]

                and

                memory["best_crop"] is not None
            ):

                predicted_class = memory["best_class"]

                # =========================================
                # AUTO CLASSIFIED
                # =========================================

                if predicted_class in AUTO_CLASS_MAP:

                    folder_name = AUTO_CLASS_MAP[
                        predicted_class
                    ]

                    save_folder = os.path.join(

                        DATASET_FOLDER,

                        "classified",

                        folder_name
                    )

                # =========================================
                # REVIEW REQUIRED
                # =========================================

                else:

                    folder_name = REVIEW_REQUIRED_MAP.get(

                        predicted_class,

                        "Others"
                    )

                    save_folder = os.path.join(

                        DATASET_FOLDER,

                        "review_required",

                        folder_name
                    )

                os.makedirs(

                    save_folder,

                    exist_ok=True
                )

                snapshot_name = (

                    f"{block_name}_"

                    f"{track_id}_"

                    f"{memory['timestamp']}.jpg"
                )

                snapshot_path = os.path.join(

                    save_folder,

                    snapshot_name
                )

                cv2.imwrite(

                    snapshot_path,

                    memory["best_crop"]
                )

                memory["saved"] = True

                snapshot_count += 1

                print(

                    f"[POLYGON SAVED] "

                    f"{snapshot_name}"
                )

            color = (0, 0, 255)

        # =================================================
        # VISUALIZATION
        # =================================================

        if DEBUG_MODE:

            cv2.rectangle(

                frame,

                (x1, y1),

                (x2, y2),

                color,

                BOX_THICKNESS
            )

            label = (

                f"{class_name} "

                f"ID:{track_id}"
            )

            cv2.putText(

                frame,

                label,

                (x1, y1 - 10),

                cv2.FONT_HERSHEY_SIMPLEX,

                FONT_SCALE,

                (255, 255, 255),

                TEXT_THICKNESS
            )

    # =====================================================
    # CLEAN OLD TRACKS
    # =====================================================

    tracks_to_delete = []

    for track_id, memory in vehicle_memory.items():

        # =============================================
        # SAVED TRACKS
        # =============================================

        if memory["saved"]:

            tracks_to_delete.append(track_id)

        # =============================================
        # STALE TRACKS
        # =============================================

        elif frame_count - memory["last_seen"] > 300:

            tracks_to_delete.append(track_id)

    for track_id in tracks_to_delete:

        del vehicle_memory[track_id]

    # =====================================================
    # FORCE MEMORY CLEANUP
    # =====================================================

    if frame_count % 500 == 0:

        gc.collect()

        if torch.cuda.is_available():

            torch.cuda.empty_cache()

        print(

            f"[MEMORY CLEANED] "

            f"Frame: {frame_count}"
        )

    # =====================================================
    # DISPLAY
    # =====================================================

    if DEBUG_MODE:

        display_frame = cv2.resize(

            frame,

            (1280, 720)
        )

        cv2.imshow(

            "Traffic Analyzer",

            display_frame
        )

        key = cv2.waitKey(1)

        if key == ord('q'):

            break

# =========================================================
# CLEANUP
# =========================================================

cap.release()

cv2.destroyAllWindows()

gc.collect()

if torch.cuda.is_available():

    torch.cuda.empty_cache()

print("\n[INFO] Processing Complete.")

print(f"[INFO] Total Snapshots: {snapshot_count}")