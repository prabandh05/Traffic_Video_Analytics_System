import os
import cv2
import json
import numpy as np

from config import *

os.makedirs(CONFIG_FOLDER, exist_ok=True)

video_files = [

    file for file in os.listdir(INPUT_FOLDER)

    if file.lower().endswith(

        (".mp4", ".mov", ".avi")
    )
]

for video_file in video_files:

    print(f"\n[VIDEO] {video_file}")

    mode = input(

        "\n1 -> Polygon\n"

        "2 -> Line\n\n"

        "Choice: "
    )

    if mode == "1":

        mode = "polygon"

    elif mode == "2":

        mode = "line"

    else:

        continue

    video_path = os.path.join(

        INPUT_FOLDER,

        video_file
    )

    cap = cv2.VideoCapture(video_path)

    ret, frame = cap.read()

    if not ret:

        continue

    frame = cv2.resize(frame, (1280, 720))

    points = []

    def draw(event, x, y, flags, param):

        global points

        if event == cv2.EVENT_LBUTTONDOWN:

            if mode == "line":

                if len(points) < 2:

                    points.append((x, y))

            else:

                points.append((x, y))

    cv2.namedWindow(video_file)

    cv2.setMouseCallback(video_file, draw)

    while True:

        temp = frame.copy()

        for point in points:

            cv2.circle(

                temp,

                point,

                5,

                (0,255,0),

                -1
            )

        if mode == "line":

            if len(points) == 2:

                cv2.line(

                    temp,

                    points[0],

                    points[1],

                    (0,0,255),

                    2
                )

        else:

            if len(points) > 1:

                cv2.polylines(

                    temp,

                    [np.array(points)],

                    False,

                    (0,255,255),

                    2
                )

        cv2.imshow(video_file, temp)

        key = cv2.waitKey(1)

        if key == ord('r'):

            points = []

        elif key == ord('c'):

            if mode == "line":

                if len(points) == 2:

                    break

            else:

                if len(points) >= 3:

                    break

    cv2.destroyAllWindows()

    config_data = {

        "mode": mode,

        "points": points
    }

    config_name = os.path.splitext(

        video_file

    )[0] + ".json"

    config_path = os.path.join(

        CONFIG_FOLDER,

        config_name
    )

    with open(config_path, "w") as file:

        json.dump(config_data, file)

    cap.release()

    print(f"[CONFIG SAVED] {config_name}")

print("\n[INFO] Geometry setup completed.")