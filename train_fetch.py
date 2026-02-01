# train_fetch.py
import requests
import sys
import json

def fetch_train_data(config_file, output_file):
    with open(config_file) as f:
        cfg = json.load(f)

    crs = cfg["train_station"]["crs"]

    url = f"https://www.realtimetrains.co.uk/search/simple/gb-nr:{crs}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(r.text)

if __name__ == "__main__":
    try:
        config_file = sys.argv[1]
        output_file = sys.argv[2]
    except IndexError:
        print("Usage: train_fetch.py <config.json> <output_file>")
        sys.exit(1)

    fetch_train_data(config_file, output_file)
