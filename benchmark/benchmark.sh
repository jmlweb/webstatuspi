#!/bin/bash
#
# Benchmark: WebStatusPi vs Uptime Kuma vs Statping-ng
#
# Measures RAM and CPU usage under identical conditions:
# - 5 URLs monitored every 60 seconds
# - 10-minute measurement window
#
# Usage:
#   ./benchmark.sh
#
# Requirements:
#   - Docker and Docker Compose
#   - curl (for health checks)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

SAMPLES=10
INTERVAL=60  # seconds between samples
RESULTS_FILE="benchmark-results.txt"

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           WebStatusPi Benchmark vs Alternatives              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Cleaning up containers...${NC}"
    docker compose down -v 2>/dev/null || true
}
trap cleanup EXIT

# Step 1: Build and start containers
echo -e "${GREEN}[1/5] Building and starting containers...${NC}"
docker compose up -d --build

# Step 2: Wait for services to be ready
echo -e "${GREEN}[2/5] Waiting for services to start (60s warmup)...${NC}"
sleep 60

# Check health
echo -e "${GREEN}[3/5] Verifying services are running...${NC}"

check_service() {
    local name=$1
    local url=$2
    if curl -sf "$url" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} $name is running"
        return 0
    else
        echo -e "  ${RED}✗${NC} $name is NOT running"
        return 1
    fi
}

check_service "WebStatusPi" "http://localhost:8081/health" || true
check_service "Uptime Kuma" "http://localhost:8082" || true
check_service "Statping" "http://localhost:8083" || true

# Step 3: Collect samples
echo -e "${GREEN}[4/5] Collecting $SAMPLES samples (every ${INTERVAL}s)...${NC}"
echo ""

# Initialize arrays
declare -a wsp_mem wsp_cpu
declare -a uk_mem uk_cpu
declare -a sp_mem sp_cpu

for i in $(seq 1 $SAMPLES); do
    echo -ne "\r  Sample $i/$SAMPLES..."

    # Get stats in one call
    stats=$(docker stats --no-stream --format "{{.Name}},{{.MemUsage}},{{.CPUPerc}}" 2>/dev/null)

    # Parse WebStatusPi
    wsp_line=$(echo "$stats" | grep "bench-webstatuspi" || echo ",,")
    wsp_mem+=("$(echo "$wsp_line" | cut -d',' -f2 | cut -d'/' -f1 | tr -d ' ')")
    wsp_cpu+=("$(echo "$wsp_line" | cut -d',' -f3 | tr -d '%')")

    # Parse Uptime Kuma
    uk_line=$(echo "$stats" | grep "bench-uptime-kuma" || echo ",,")
    uk_mem+=("$(echo "$uk_line" | cut -d',' -f2 | cut -d'/' -f1 | tr -d ' ')")
    uk_cpu+=("$(echo "$uk_line" | cut -d',' -f3 | tr -d '%')")

    # Parse Statping
    sp_line=$(echo "$stats" | grep "bench-statping" || echo ",,")
    sp_mem+=("$(echo "$sp_line" | cut -d',' -f2 | cut -d'/' -f1 | tr -d ' ')")
    sp_cpu+=("$(echo "$sp_line" | cut -d',' -f3 | tr -d '%')")

    [ $i -lt $SAMPLES ] && sleep $INTERVAL
done

echo -e "\r  Collected $SAMPLES samples.          "

# Step 4: Calculate averages
echo -e "${GREEN}[5/5] Calculating results...${NC}"
echo ""

# Calculate averages using awk (more portable than bc + nameref)
calc_mem_avg() {
    echo "$@" | tr ' ' '\n' | awk '
    {
        val = $1
        if (val ~ /GiB/) { gsub(/GiB/, "", val); sum += val * 1024; count++ }
        else if (val ~ /MiB/) { gsub(/MiB/, "", val); sum += val; count++ }
        else if (val ~ /KiB/) { gsub(/KiB/, "", val); sum += val / 1024; count++ }
    }
    END { if (count > 0) printf "%.1f", sum/count; else print "N/A" }
    '
}

calc_cpu_avg() {
    echo "$@" | tr ' ' '\n' | awk '
    BEGIN { sum = 0; count = 0 }
    /^[0-9]/ { sum += $1; count++ }
    END { if (count > 0) printf "%.2f", sum/count; else print "N/A" }
    '
}

wsp_avg_mem=$(calc_mem_avg "${wsp_mem[@]}")
uk_avg_mem=$(calc_mem_avg "${uk_mem[@]}")
sp_avg_mem=$(calc_mem_avg "${sp_mem[@]}")

wsp_avg_cpu=$(calc_cpu_avg "${wsp_cpu[@]}")
uk_avg_cpu=$(calc_cpu_avg "${uk_cpu[@]}")
sp_avg_cpu=$(calc_cpu_avg "${sp_cpu[@]}")

# Get image sizes
echo "Getting image sizes..."
wsp_size=$(docker images --format "{{.Repository}},{{.Size}}" 2>/dev/null | grep -i webstatuspi | head -1 | cut -d',' -f2 || echo "N/A")
uk_size=$(docker images louislam/uptime-kuma --format "{{.Size}}" 2>/dev/null | head -1 || echo "N/A")
sp_size=$(docker images adamboutcher/statping-ng --format "{{.Size}}" 2>/dev/null | head -1 || echo "N/A")

# Generate report
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                     BENCHMARK RESULTS                        ║${NC}"
echo -e "${CYAN}╠══════════════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC} Workload: 5 URLs, 60s interval, $SAMPLES samples                   ${CYAN}║${NC}"
echo -e "${CYAN}╠════════════════╦═════════════╦═════════════╦═════════════════╣${NC}"
echo -e "${CYAN}║${NC} Tool           ${CYAN}║${NC} RAM (avg)   ${CYAN}║${NC} CPU (avg)   ${CYAN}║${NC} Image Size      ${CYAN}║${NC}"
echo -e "${CYAN}╠════════════════╬═════════════╬═════════════╬═════════════════╣${NC}"
printf "${CYAN}║${NC} %-14s ${CYAN}║${NC} %9s MB ${CYAN}║${NC} %9s%% ${CYAN}║${NC} %-15s ${CYAN}║${NC}\n" "WebStatusPi" "$wsp_avg_mem" "$wsp_avg_cpu" "$wsp_size"
printf "${CYAN}║${NC} %-14s ${CYAN}║${NC} %9s MB ${CYAN}║${NC} %9s%% ${CYAN}║${NC} %-15s ${CYAN}║${NC}\n" "Uptime Kuma" "$uk_avg_mem" "$uk_avg_cpu" "$uk_size"
printf "${CYAN}║${NC} %-14s ${CYAN}║${NC} %9s MB ${CYAN}║${NC} %9s%% ${CYAN}║${NC} %-15s ${CYAN}║${NC}\n" "Statping-ng" "$sp_avg_mem" "$sp_avg_cpu" "$sp_size"
echo -e "${CYAN}╚════════════════╩═════════════╩═════════════╩═════════════════╝${NC}"

# Save to file
{
    echo "# Benchmark Results - $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    echo "## Configuration"
    echo "- URLs monitored: 5"
    echo "- Check interval: 60 seconds"
    echo "- Samples: $SAMPLES"
    echo "- Sample interval: ${INTERVAL}s"
    echo ""
    echo "## Results"
    echo ""
    echo "| Tool | RAM (avg) | CPU (avg) | Image Size |"
    echo "|------|-----------|-----------|------------|"
    echo "| WebStatusPi | ${wsp_avg_mem} MB | ${wsp_avg_cpu}% | $wsp_size |"
    echo "| Uptime Kuma | ${uk_avg_mem} MB | ${uk_avg_cpu}% | $uk_size |"
    echo "| Statping-ng | ${sp_avg_mem} MB | ${sp_avg_cpu}% | $sp_size |"
    echo ""
    echo "## Raw Data"
    echo ""
    echo "### WebStatusPi"
    echo "Memory samples: ${wsp_mem[*]}"
    echo "CPU samples: ${wsp_cpu[*]}"
    echo ""
    echo "### Uptime Kuma"
    echo "Memory samples: ${uk_mem[*]}"
    echo "CPU samples: ${uk_cpu[*]}"
    echo ""
    echo "### Statping-ng"
    echo "Memory samples: ${sp_mem[*]}"
    echo "CPU samples: ${sp_cpu[*]}"
} > "$RESULTS_FILE"

echo ""
echo -e "${GREEN}Results saved to: $RESULTS_FILE${NC}"
echo ""
echo -e "${YELLOW}Note: Configure Uptime Kuma and Statping with 5 URLs manually"
echo -e "for accurate comparison (they require UI-based configuration).${NC}"
