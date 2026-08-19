import os

from collections import defaultdict

from openpyxl import Workbook

# =========================================================
# EXCEL HEADERS
# =========================================================

HEADERS = [

    "Block",

    "Two Wheeler",

    "Auto",

    "Car/Jeep/Van/Taxi",

    "Std Bus",

    "Mini Bus",

    "LCV",

    "2 axle",

    "3 axle",

    "Multi axle",

    "Tractor",

    "Cycle",

    "Bullock Cart",

    "Animal Drawn"
]

# =========================================================
# FOLDER MAP
# =========================================================

EXCEL_FOLDER_MAP = {

    "Two Wheeler": "Two Wheeler",

    "Auto": "Auto",

    "Car": "Car/Jeep/Van/Taxi",

    "Cycle": "Cycle",

    "Std Bus": "Std Bus",

    "Mini Bus": "Mini Bus",

    "LCV": "LCV",

    "2 axle": "2 axle",

    "3 axle": "3 axle",

    "Multi axle": "Multi axle",

    "Tractor": "Tractor",

    "Bullock Cart": "Bullock Cart",

    "Animal Drawn": "Animal Drawn"
}

# =========================================================
# PROCESS ALL DATASETS
# =========================================================

datasets_root = "datasets"

dataset_folders = [

    folder for folder in os.listdir(datasets_root)

    if os.path.isdir(

        os.path.join(datasets_root, folder)
    )
]

for dataset_name in dataset_folders:

    print(f"\n[PROCESSING] {dataset_name}")

    dataset_path = os.path.join(

        datasets_root,

        dataset_name
    )

    classified_folder = os.path.join(

        dataset_path,

        "classified"
    )

    output_excel = os.path.join(

        dataset_path,

        "traffic_counts.xlsx"
    )

    clock_data = defaultdict(

        lambda: {

            header: 0

            for header in HEADERS
        }
    )

    # =====================================================
    # SCAN CLASS FOLDERS
    # =====================================================

    for folder_name, excel_column in EXCEL_FOLDER_MAP.items():

        folder_path = os.path.join(

            classified_folder,

            folder_name
        )

        if not os.path.exists(folder_path):

            continue

        for file_name in os.listdir(folder_path):

            if not file_name.lower().endswith(

                (".jpg", ".jpeg", ".png")
            ):

                continue

            parts = file_name.split("_")

            if len(parts) < 2:

                continue

            clock_name = parts[0]

            clock_data[clock_name][

                "Block"

            ] = clock_name

            clock_data[clock_name][

                excel_column

            ] += 1

    # =====================================================
    # CREATE EXCEL
    # =====================================================

    wb = Workbook()

    ws = wb.active

    ws.title = "Traffic Counts"

    ws.append(HEADERS)

    sorted_clocks = sorted(

        clock_data.keys(),

        key=lambda x: int(

            x.replace("clock", "")
        )
    )

    for clock_name in sorted_clocks:

        row = clock_data[clock_name]

        ws.append([

            row["Block"],

            row["Two Wheeler"],

            row["Auto"],

            row["Car/Jeep/Van/Taxi"],

            row["Std Bus"],

            row["Mini Bus"],

            row["LCV"],

            row["2 axle"],

            row["3 axle"],

            row["Multi axle"],

            row["Tractor"],

            row["Cycle"],

            row["Bullock Cart"],

            row["Animal Drawn"]
        ])

    wb.save(output_excel)

    print(f"[EXCEL SAVED] {output_excel}")

print("\n[INFO] All Excel files generated.")