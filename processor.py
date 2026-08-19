import os
import gc
import cv2
import json
import torch
import numpy as np
import supervision as sv

from ultralytics import YOLO

from config import *

# =========================================================
# CREATE FOLDERS
# =========================================================

os.makedirs(DATASETS_FOLDER, exist_ok=True)

os.makedirs(PROCESSED_LOGS_FOLDER, exist_ok=True)

# =========================================================
# LOAD MODEL
# =========================================================

print("\n[INFO] Loading model...")

device = "cuda" if torch.cuda.is_available() else "cpu"

print(f"[INFO] Device: {device}")

model = YOLO(MODEL_PATH)

model.to(device)

print(f"[INFO] Classes: {model.names}")

# =========================================================
# TRACKER
# =========================================================

tracker = sv.ByteTrack(

    track_activation_threshold=0.1,

    lost_track_buffer=30
)

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

    "Truck": "2 axle",

    "LCV": "LCV",

    "Others": "Others"
}

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
# FIND VIDEOS
# =========================================================

video_files = [

    file for file in os.listdir(INPUT_FOLDER)

    if file.lower().endswith(

        (".mp4", ".mov", ".avi")
    )
]

print(f"\n[INFO] Videos Found: {len(video_files)}")

# =========================================================
# PROCESS VIDEOS
# =========================================================

for video_file in video_files:

    video_name = os.path.splitext(

        video_file

    )[0]

    done_file = os.path.join(

        PROCESSED_LOGS_FOLDER,

        video_name + ".done"
    )

    # =====================================================
    # SKIP PROCESSED
    # =====================================================

    if os.path.exists(done_file):

        print(f"\n[SKIPPED] {video_name}")

        continue

    print(f"\n===================================")
    print(f"[PROCESSING] {video_name}")
    print(f"===================================\n")

    # =====================================================
    # DATASET FOLDER
    # =====================================================

    dataset_folder = os.path.join(

        DATASETS_FOLDER,

        video_name
    )

    os.makedirs(dataset_folder, exist_ok=True)

    # =====================================================
    # VIDEO PATH
    # =====================================================

    video_path = os.path.join(

        INPUT_FOLDER,

        video_file
    )

    # =====================================================
    # CONFIG PATH
    # =====================================================

    config_path = os.path.join(

        CONFIG_FOLDER,

        video_name + ".json"
    )

    if not os.path.exists(config_path):

        print(f"[NO CONFIG FOUND] {video_name}")

        continue

    # =====================================================
    # LOAD CONFIG
    # =====================================================

    with open(config_path, "r") as file:

        config_data = json.load(file)

    MODE = config_data["mode"]

    geometry_points = config_data["points"]

    print(f"[MODE] {MODE}")

    # =====================================================
    # POLYGON
    # =====================================================

    if MODE == "polygon":

        polygon_np = np.array(

            geometry_points,

            dtype=np.int32
        )

    # =====================================================
    # VIDEO CAPTURE
    # =====================================================

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():

        print(f"[ERROR] Cannot open {video_name}")

        continue

    fps = cap.get(cv2.CAP_PROP_FPS)

    total_frames = int(

        cap.get(cv2.CAP_PROP_FRAME_COUNT)
    )

    total_minutes = (

        total_frames / fps
    ) / 60

    print(

        f"[INFO] Duration: "

        f"{total_minutes:.2f} minutes"
    )

    # =====================================================
    # MEMORY
    # =====================================================

    vehicle_memory = {}

    last_detections = sv.Detections.empty()

    frame_count = 0

    snapshot_count = 0

    # =====================================================
    # FRAME LOOP
    # =====================================================

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        # =================================================
        # RESIZE
        # =================================================

        frame = cv2.resize(

            frame,

            (1280, 720)
        )

        raw_frame = frame.copy()

        frame_count += 1

        # =================================================
        # TIME
        # =================================================

        current_seconds = frame_count / fps

        block_number = int(

            current_seconds //

            (BLOCK_DURATION_MINUTES * 60)

        ) + 1

        block_name = f"clock{block_number}"

        timestamp = f"{int(current_seconds)}"

        # =================================================
        # STATUS PRINT
        # =================================================

        if frame_count % 300 == 0:

            progress = (

                frame_count /

                total_frames
            ) * 100

            print(

                f"[PROGRESS] "

                f"{video_name} | "

                f"{progress:.1f}% | "

                f"Snapshots: {snapshot_count}"
            )

        # =================================================
        # DETECTION
        # =================================================

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

        # =================================================
        # TRACKER
        # =================================================

        tracked_detections = tracker.update_with_detections(

            detections
        )

        # =================================================
        # DRAW GEOMETRY
        # =================================================

        if DEBUG_MODE:

            if MODE == "polygon":

                cv2.polylines(

                    frame,

                    [polygon_np],

                    True,

                    (0, 0, 255),

                    2
                )

            else:

                cv2.line(

                    frame,

                    tuple(geometry_points[0]),

                    tuple(geometry_points[1]),

                    (0, 0, 255),

                    2
                )

        # =================================================
        # PROCESS DETECTIONS
        # =================================================

        for detection in tracked_detections:

            x1, y1, x2, y2 = detection[0]

            class_id = detection[3]

            track_id = int(detection[4])

            x1 = int(x1)
            y1 = int(y1)
            x2 = int(x2)
            y2 = int(y2)

            class_name = model.names[class_id]

            center_x = int((x1 + x2) / 2)

            center_y = int((y1 + y2) / 2)

            # =============================================
            # DRAW DETECTION
            # =============================================

            if DEBUG_MODE:

                cv2.rectangle(

                    frame,

                    (x1, y1),

                    (x2, y2),

                    (0, 255, 0),

                    2
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

                    0.5,

                    (255, 255, 255),

                    2
                )

            # =============================================
            # MEMORY INIT
            # =============================================

            if track_id not in vehicle_memory:

                vehicle_memory[track_id] = {

                    "saved": False,

                    "best_area": 0,

                    "best_crop": None,

                    "best_class": class_name,

                    "previous_side": None,

                    "last_seen": frame_count
                }

            memory = vehicle_memory[track_id]

            memory["last_seen"] = frame_count

            # =============================================
            # POLYGON MODE
            # =============================================

            if MODE == "polygon":

                inside = cv2.pointPolygonTest(

                    polygon_np,

                    (center_x, center_y),

                    False

                ) >= 0

            # =============================================
            # LINE MODE
            # =============================================

            else:

                current_side = side_of_line(

                    (center_x, center_y),

                    geometry_points[0],

                    geometry_points[1]
                )

                previous_side = memory["previous_side"]

                inside = True

            # =============================================
            # INSIDE
            # =============================================

            if inside:

                width = x2 - x1

                height = y2 - y1

                area = width * height

                # =========================================
                # STORE BEST CROP
                # =========================================

                if area > memory["best_area"]:

                    crop = raw_frame[y1:y2, x1:x2].copy()

                    if crop.size > 0:

                        memory["best_area"] = area

                        memory["best_crop"] = crop

                        memory["best_class"] = class_name

                # =========================================
                # SAVE LOGIC
                # =========================================

                save_now = False

                if MODE == "line":

                    if previous_side is not None:

                        if previous_side * current_side < 0:

                            save_now = True

                    memory["previous_side"] = current_side

                else:

                    save_now = True

                # =========================================
                # SAVE SNAPSHOT
                # =========================================

                if (

                    save_now

                    and

                    not memory["saved"]

                    and

                    memory["best_crop"] is not None
                ):

                    predicted_class = memory["best_class"]

                    # =====================================
                    # AUTO CLASSIFIED
                    # =====================================

                    if predicted_class in AUTO_CLASS_MAP:

                        folder_name = AUTO_CLASS_MAP[
                            predicted_class
                        ]

                        save_folder = os.path.join(

                            dataset_folder,

                            "classified",

                            folder_name
                        )

                    # =====================================
                    # REVIEW REQUIRED
                    # =====================================

                    else:

                        folder_name = REVIEW_REQUIRED_MAP.get(

                            predicted_class,

                            "Others"
                        )

                        save_folder = os.path.join(

                            dataset_folder,

                            "classified",

                            folder_name
                        )

                    os.makedirs(

                        save_folder,

                        exist_ok=True
                    )

                    snapshot_name = (

                        f"{block_name}_"

                        f"{track_id}_"

                        f"{timestamp}.jpg"
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

                        f"[SAVED] "

                        f"{snapshot_name} "

                        f"-> "

                        f"{folder_name}"
                    )

        # =================================================
        # CLEAN MEMORY
        # =================================================

        tracks_to_delete = []

        for track_id, memory in vehicle_memory.items():

            if memory["saved"]:

                tracks_to_delete.append(track_id)

            elif frame_count - memory["last_seen"] > 300:

                tracks_to_delete.append(track_id)

        for track_id in tracks_to_delete:

            del vehicle_memory[track_id]

        # =================================================
        # MEMORY CLEANUP
        # =================================================

        if frame_count % 500 == 0:

            gc.collect()

            if torch.cuda.is_available():

                torch.cuda.empty_cache()

            print(

                f"[MEMORY CLEANED] "

                f"Frame: {frame_count}"
            )

        # =================================================
        # DISPLAY
        # =================================================

        if DEBUG_MODE:

            display_frame = cv2.resize(

                frame,

                (1280, 720)
            )

            cv2.imshow(

                "Traffic Processor",

                display_frame
            )

            key = cv2.waitKey(1)

            if key == ord('q'):

                break

    # =====================================================
    # CLEANUP VIDEO
    # =====================================================

    cap.release()

    open(done_file, "w").close()

    print(

        f"\n[DONE] "

        f"{video_name}"
    )

    print(

        f"[TOTAL SNAPSHOTS] "

        f"{snapshot_count}"
    )

    gc.collect()

    if torch.cuda.is_available():

        torch.cuda.empty_cache()

# =========================================================
# FINAL CLEANUP
# =========================================================

cv2.destroyAllWindows()

print("\n[INFO] All videos processed successfully.")