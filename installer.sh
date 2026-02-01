#!/bin/bash

set -e

echo "=============================================="
echo " NextBus GB API Parser – Installer"
echo "=============================================="
echo

# ------------------------------------------------------------
# Detect OS family
# ------------------------------------------------------------
if [ -f /etc/debian_version ]; then
    OS_FAMILY="debian"
    echo "Detected Debian-based system."
elif [ -f /etc/redhat-release ]; then
    OS_FAMILY="rhel"
    echo "Detected RHEL/CentOS/Oracle Linux system."
else
    echo "Unsupported OS. Exiting."
    exit 1
fi

# ------------------------------------------------------------
# Install Python + pip
# ------------------------------------------------------------
echo
echo "Installing Python3, pip, and full standard library..."

if [ "$OS_FAMILY" = "debian" ]; then
    sudo apt update
    sudo apt install -y python3 python3-full python3-pip python3-venv git
else
    sudo yum install -y python3 python3-pip python3-virtualenv git
fi

# ------------------------------------------------------------
# Clone repo
# ------------------------------------------------------------
echo
echo "Cloning NextBus GB API Parser repo..."

if [ ! -d "NextBus-GB-API-Python-parser" ]; then
    git clone https://github.com/valemaio2/NextBus-GB-API-Python-parser
fi

cd NextBus-GB-API-Python-parser

# ------------------------------------------------------------
# Ask user if they want a virtual environment
# ------------------------------------------------------------
echo
read -p "Create Python virtual environment? (y/n): " USE_VENV

if [[ "$USE_VENV" =~ ^[Yy]$ ]]; then
    python3 -m venv venv
    source venv/bin/activate
    echo "Virtual environment activated."
fi

# ------------------------------------------------------------
# Install Python requirements
# ------------------------------------------------------------
echo
echo "Installing Python dependencies..."
pip install -r requirements.txt

# ------------------------------------------------------------
# Interactive config.json builder
# ------------------------------------------------------------
echo
echo "=============================================="
echo " Building config.json"
echo "=============================================="

# -----------------------------
# Collect bus stops
# -----------------------------
STOPS=()
while true; do
    read -p "Enter ATCO bus stop code (or press ENTER to stop): " STOP_ID
    if [ -z "$STOP_ID" ]; then
        if [ ${#STOPS[@]} -eq 0 ]; then
            echo "At least one bus stop is required."
            continue
        fi
        break
    fi

    read -p "Enter a friendly name for this stop: " STOP_NAME
    STOPS+=("{\"stop_id\": \"$STOP_ID\", \"stop_name\": \"$STOP_NAME\"}")
done

# -----------------------------
# Collect train stations
# -----------------------------
TRAIN_STATIONS=()
while true; do
    read -p "Enter train station CRS code (or press ENTER to stop): " CRS
    if [ -z "$CRS" ]; then
        if [ ${#TRAIN_STATIONS[@]} -eq 0 ]; then
            echo "At least one train station is required."
            continue
        fi
        break
    fi

    read -p "Enter a friendly name for this station: " CRS_NAME
    TRAIN_STATIONS+=("{\"crs\": \"${CRS^^}\", \"name\": \"$CRS_NAME\"}")
done

# -----------------------------
# Number of departures
# -----------------------------
read -p "Number of departures to show (default 5): " NUM
NUM=${NUM:-5}

# -----------------------------
# API credentials
# -----------------------------
echo
echo "Enter your NextBus API credentials:"
read -p "Username: " API_USER
read -s -p "Password: " API_PASS
echo

# -----------------------------
# Write config.json
# -----------------------------
echo
echo "Writing config.json..."

cat > config.json <<EOF
{
  "api_username": "$API_USER",
  "api_password": "$API_PASS",

  "data": "./data",
  "html": "./html",

  "stops": [
    $(IFS=,; echo "${STOPS[*]}")
  ],

  "train_stations": [
    $(IFS=,; echo "${TRAIN_STATIONS[*]}")
  ],

  "num_departures": $NUM,
  "output_html_file": "buses.html",
  "output_html_title": "Live Bus/Train Timetable"
}
EOF

echo "config.json created."

# ------------------------------------------------------------
# Run the pipeline
# ------------------------------------------------------------
echo
echo "Running parser and HTML generator..."

mkdir -p data

python3 train_fetch.py config.json data/
python3 sync.py config.json
python3 generate.py config.json

echo
echo "=============================================="
echo " Installation complete!"
echo " HTML output is in the 'output/' directory."
echo "=============================================="
