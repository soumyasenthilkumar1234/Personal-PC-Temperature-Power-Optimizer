import sqlite3
import os
import pandas as pd

DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
DB_PATH = os.path.join(DB_DIR, "telemetry.db")

def init_db():
    """Initializes the database and creates the telemetry table if it doesn't exist."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            cpu_usage_pct REAL NOT NULL,
            ram_usage_pct REAL NOT NULL,
            battery_pct REAL,
            battery_plugged_in INTEGER,
            cpu_temp_c REAL,
            active_power_plan TEXT,
            is_throttled INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def log_telemetry(cpu_usage_pct, ram_usage_pct, battery_pct, battery_plugged_in, cpu_temp_c, active_power_plan, is_throttled):
    """Inserts a telemetry record into the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO telemetry (
            cpu_usage_pct, 
            ram_usage_pct, 
            battery_pct, 
            battery_plugged_in, 
            cpu_temp_c, 
            active_power_plan, 
            is_throttled
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        cpu_usage_pct,
        ram_usage_pct,
        battery_pct,
        1 if battery_plugged_in else 0,
        cpu_temp_c,
        active_power_plan,
        1 if is_throttled else 0
    ))
    conn.commit()
    conn.close()

def get_historical_data(limit=10000):
    """Retrieves historical data from the database and returns it as a pandas DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM telemetry ORDER BY timestamp DESC LIMIT ?"
    df = pd.read_sql_query(query, conn, params=(limit,))
    conn.close()
    # Return chronologically sorted data
    return df.iloc[::-1].reset_index(drop=True)

if __name__ == "__main__":
    init_db()
    print(f"Database initialized at: {DB_PATH}")
