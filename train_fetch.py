import requests
import sys
import json
import os

def fetch_train_data(config_file, data_path):
    with open(config_file) as f:
        cfg = json.load(f)

    stations = cfg.get("train_stations", [])

    for st in stations:
        crs = st.get("crs", "").strip().upper()
        name = st.get("name", "").strip()

        output_file = os.path.join(data_path, f"train_{crs}.latest.html")

        # Skip disabled or invalid CRS
        if not crs or crs == "NO":
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("")
            print(f"Train fetch skipped for CRS {crs}")
            continue

        url = f"https://www.realtimetrains.co.uk/search/simple/gb-nr:{crs}"

        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(r.text)

            print(f"Fetched train data for {crs}")

        except Exception as e:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("")
            print(f"Train fetch failed for CRS {crs}: {e}")
            print("Continuing without this station.")


if __name__ == "__main__":
    try:
        config_file = sys.argv[1]
        data_path = sys.argv[2]
    except IndexError:
        print("Usage: train_fetch.py <config.json> <data_path>")
        sys.exit(1)

    fetch_train_data(config_file, data_path)
