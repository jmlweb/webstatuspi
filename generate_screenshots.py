#!/usr/bin/env python3
"""Generate fake monitoring data and take dashboard screenshots.

This script creates a temporary database with fictional but realistic
monitoring data, starts the API server, and captures screenshots of:
1. Dashboard home page (all URLs overview)
2. URL detail modal (history view)
"""

import random
import sqlite3
import sys
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path

# Add webstatuspi to path
sys.path.insert(0, str(Path(__file__).parent))

from webstatuspi.database import init_db, insert_check
from webstatuspi.api import ApiServer
from webstatuspi.config import ApiConfig
from webstatuspi.models import CheckResult


# Fictional but realistic URLs with varied statuses
FAKE_URLS = [
    {
        "name": "API_PROD",
        "url": "https://api.prod.techcorp.io/v1/health",
        "base_latency": 120,
        "latency_variation": 40,
        "uptime_target": 99.5,
        "status": "up",
    },
    {
        "name": "WEB_FRONT",
        "url": "https://www.dataflux.app",
        "base_latency": 450,
        "latency_variation": 100,
        "uptime_target": 97.2,
        "status": "up",
    },
    {
        "name": "DB_SERVICE",
        "url": "https://db-api.cloudsync.net/status",
        "base_latency": 1200,
        "latency_variation": 300,
        "uptime_target": 100.0,
        "status": "up",
    },
    {
        "name": "AUTH_API",
        "url": "https://auth.securelogin.dev/health",
        "base_latency": 0,
        "latency_variation": 0,
        "uptime_target": 0.0,
        "status": "down",
        "error": "Connection timeout after 5000ms",
    },
    {
        "name": "CACHE_SVC",
        "url": "https://cache.edge-network.io/ping",
        "base_latency": 80,
        "latency_variation": 20,
        "uptime_target": 98.8,
        "status": "up",
    },
]


def generate_history(conn: sqlite3.Connection, url_config: dict, hours: int = 24) -> None:
    """Generate check history for a URL over the past N hours."""
    now = datetime.utcnow()
    interval_minutes = 10  # Check every 10 minutes = 6 checks/hour
    
    total_checks = (hours * 60) // interval_minutes
    checks_to_generate = min(total_checks, 100)  # Limit to 100 as per API
    
    # Calculate how many should be "up" to match uptime_target
    target_up = int(checks_to_generate * (url_config["uptime_target"] / 100.0))
    
    for i in range(checks_to_generate):
        check_time = now - timedelta(minutes=interval_minutes * i)
        
        # Determine if this check should be up or down
        is_up = url_config["status"] == "up"
        if url_config["status"] == "up" and i >= target_up:
            # After reaching target, make some checks fail to match uptime
            # For 100% uptime, all checks are up
            if url_config["uptime_target"] < 100:
                is_up = random.random() < (url_config["uptime_target"] / 100.0)
        
        # Generate check result
        if is_up:
            status_code = 200
            latency = max(1, url_config["base_latency"] + random.randint(
                -url_config["latency_variation"], 
                url_config["latency_variation"]
            ))
            error = None
        else:
            status_code = None
            latency = random.randint(3000, 8000)  # Timeout latencies
            error = url_config.get("error", "Connection refused")
        
        check = CheckResult(
            url_name=url_config["name"],
            url=url_config["url"],
            status_code=status_code,
            response_time_ms=latency,
            is_up=is_up,
            error_message=error,
            checked_at=check_time,
        )
        
        insert_check(conn, check)


def setup_fake_database(db_path: str) -> sqlite3.Connection:
    """Create database and populate with fake data."""
    print(f"Creating fake database at {db_path}...")
    conn = init_db(db_path)
    
    # Generate history for each URL
    for url_config in FAKE_URLS:
        print(f"  Generating history for {url_config['name']}...")
        generate_history(conn, url_config)
    
    print(f"Database populated with fake data.")
    return conn


def start_api_server(db_conn: sqlite3.Connection, port: int = 8080) -> ApiServer:
    """Start the API server in a background thread."""
    print(f"Starting API server on port {port}...")
    api_config = ApiConfig(port=port)
    server = ApiServer(api_config, db_conn)
    server.start()
    
    # Wait a moment for server to start
    time.sleep(1)
    return server


def main():
    """Main function to generate screenshots."""
    import tempfile
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        # Setup database with fake data
        db_conn = setup_fake_database(db_path)
        
        # Start API server
        server = start_api_server(db_conn, port=8080)
        
        print("\n" + "="*60)
        print("API server is running at http://localhost:8080")
        print("Dashboard: http://localhost:8080/")
        print("="*60)
        print("\nYou can now:")
        print("1. Open http://localhost:8080/ in your browser")
        print("2. Take a screenshot of the home page")
        print("3. Click on any URL card to see the detail modal")
        print("4. Take a screenshot of the detail modal")
        print("\nPress Ctrl+C to stop the server...")
        
        # Keep server running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            server.stop()
            db_conn.close()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Clean up temp database
        try:
            Path(db_path).unlink()
        except:
            pass
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
