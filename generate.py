import os
import sys
from collections import defaultdict
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
import bus

# ---------------------------------------------------------
# Load configuration
# ---------------------------------------------------------
try:
    config_file = sys.argv[1]
except IndexError:
    print("Usage: generate.py <config.json>")
    sys.exit(1)

settings = bus.open_settings(config_file)

data_path = settings["data"]
html_path = settings["html"]
output_html_filename = os.path.join(html_path, settings["output_html_file"])
page_title = settings["output_html_title"]

num_deps = settings["num_departures"]

# ---------------------------------------------------------
# Load BUS departures
# ---------------------------------------------------------
all_departures = []

for stop in settings["stops"]:
    xml_file = os.path.join(data_path, stop["stop_id"] + ".latest.xml")
    deps = bus.convert_xmlfile_to_array(xml_file, stop["stop_name"])[:num_deps]
    all_departures.extend(deps)

# ---------------------------------------------------------
# TRAIN PARSER
# ---------------------------------------------------------
def parse_train_html(filename, station_name):
    with open(filename, encoding="utf-8") as f:
        html = f.read()

    if not html.strip():
        return []

    soup = BeautifulSoup(html, "html.parser")
    results = []
    today = datetime.now().date()

    for svc in soup.select("a.service"):
        time_div = svc.select_one(".time")
        if not time_div:
            continue

        raw = time_div.get_text(strip=True)
        if len(raw) == 4 and raw.isdigit():
            sched = raw[:2] + ":" + raw[2:]
        else:
            continue

        dest_span = svc.select_one(".location span")
        if not dest_span:
            continue
        dest = dest_span.get_text(strip=True)

        plat_div = svc.select_one(".platformbox")
        plat = plat_div.get_text(strip=True) if plat_div else ""

        addl = svc.select_one(".addl")
        exp_raw = addl.get_text(" ", strip=True) if addl else ""

        if "Expected at" in exp_raw:
            hhmm = exp_raw.split()[-1]
            if len(hhmm) == 4 and hhmm.isdigit():
                exp = hhmm[:2] + ":" + hhmm[2:]
            else:
                exp = sched
        elif len(exp_raw) == 4 and exp_raw.isdigit():
            exp = exp_raw[:2] + ":" + exp_raw[2:]
        elif len(exp_raw) == 5 and exp_raw[2] == ":":
            exp = exp_raw
        else:
            exp = sched

        sched_dt = datetime.strptime(sched, "%H:%M").replace(
            year=today.year, month=today.month, day=today.day
        )
        exp_dt = datetime.strptime(exp, "%H:%M").replace(
            year=today.year, month=today.month, day=today.day
        )

        results.append({
            "station": station_name,
            "direction": dest,
            "scheduled_departure": sched_dt,
            "expected_departure": exp_dt,
            "platform": plat,
        })

    return results

# ---------------------------------------------------------
# Load TRAIN departures for multiple stations
# ---------------------------------------------------------
train_departures_by_station = []

stations = settings.get("train_stations", [])

for st in stations:
    crs = st.get("crs", "").strip().upper()
    name = st.get("name", "").strip()

    if not crs or crs == "NO":
        continue

    filename = os.path.join(data_path, f"train_{crs}.latest.html")

    try:
        deps = parse_train_html(filename, name)[:num_deps]
        if len(deps) > 0:
            train_departures_by_station.append((name, deps))
    except Exception:
        continue

# ---------------------------------------------------------
# Load HTML template
# ---------------------------------------------------------
template_path = os.path.join(os.path.dirname(__file__), "template.html")

with open(template_path, "r", encoding="utf-8") as f:
    page_template = f.read()

# ---------------------------------------------------------
# Build HTML content
# ---------------------------------------------------------
content = ""

grouped = defaultdict(list)
for d in all_departures:
    grouped[d["bus_stop"]].append(d)

# BUS CARDS
for stop_name, deps in grouped.items():
    content += "<div class='stop-card'>"
    content += f"<div class='stop-title'>{stop_name}</div>"
    content += "<table>"
    content += "<tr><th>Line</th><th>Direction</th><th>Sched</th><th>Exp</th></tr>"

    for d in deps:
        sched = d["scheduled_departure"].strftime("%H:%M")
        exp = d["expected_departure"].strftime("%H:%M")

        status_class = "on-time" if exp == sched else "delayed"

        content += (
            f"<tr>"
            f"<td>{d['line_name']}</td>"
            f"<td>{d['direction']}</td>"
            f"<td>{sched}</td>"
            f"<td class='{status_class}'>{exp}</td>"
            f"</tr>"
        )

    content += "</table></div>"

# TRAIN CARDS
for station_name, deps in train_departures_by_station:
    content += "<div class='train-card'>"
    content += f"<div class='train-title'>{station_name} (Train)</div>"
    content += "<table class='train-table'>"
    content += "<tr><th>To</th><th>Sched</th><th>Exp</th><th>Plat</th></tr>"

    for t in deps:
        sched = t["scheduled_departure"].strftime("%H:%M")
        exp = t["expected_departure"].strftime("%H:%M")
        plat = t.get("platform", "")

        diff = int((t["expected_departure"] - t["scheduled_departure"]).total_seconds() / 60)

        if diff <= 0:
            status_class = "train-on-time"
        elif diff <= 5:
            status_class = "train-due-soon"
        else:
            status_class = "train-delayed"

        content += (
            f"<tr>"
            f"<td>{t['direction']}</td>"
            f"<td class='train-time'>{sched}</td>"
            f"<td class='{status_class}'>{exp}</td>"
            f"<td>{plat}</td>"
            f"</tr>"
        )

    content += "</table></div>"

# ---------------------------------------------------------
# Timestamp (Europe/London)
# ---------------------------------------------------------
last_updated = datetime.now(ZoneInfo("Europe/London")).strftime("%Y-%m-%d %H:%M:%S")

# ---------------------------------------------------------
# Write final HTML
# ---------------------------------------------------------
with open(output_html_filename, "w", encoding="utf-8") as f:
    f.write(page_template.format(
        title=page_title,
        heading=page_title,
        content=content,
        last_updated=last_updated
    ))

print("Generated:", output_html_filename)
