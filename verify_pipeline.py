import os
import sys
import time
import random
import sqlite3
from datetime import datetime, timedelta
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from database import init_db, log_telemetry, DB_PATH
from ml_predictor import TempPredictor

def populate_mock_data(minutes=30, interval_sec=5):
    """Fills the database with realistic looking simulated telemetry data for testing."""
    print(f"Populating DB at {DB_PATH} with {minutes} minutes of simulated data...")
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Clear any existing data
    cursor.execute("DELETE FROM telemetry")
    conn.commit()
    conn.close()
    
    start_time = datetime.now() - timedelta(minutes=minutes)
    
    # We will generate data points
    num_points = int((minutes * 60) / interval_sec)
    
    # Base CPU usage pattern (sine wave + noise + random spikes)
    cpu_base = 20.0
    
    for i in range(num_points):
        timestamp = start_time + timedelta(seconds=i * interval_sec)
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        # Simulate CPU cycles (peaks and troughs)
        cycle = (i / 100.0) * 2.0 * 3.14159
        cpu = cpu_base + 15 * (1.0 + (i % 200 > 150)) * (random.random() * 0.5 + 0.5)
        # Add random spikes
        if random.random() < 0.05:
            cpu = random.uniform(70.0, 95.0)
        cpu = min(max(cpu, 0.0), 100.0)
        
        ram = random.uniform(50.0, 60.0)
        battery = max(10, 100 - int(i * 0.1))
        plugged = 0 if battery < 90 else 1
        
        # CPU temp is NULL (as non-admin fallback)
        temp = None
        
        active_plan = "Balanced (381b4222)"
        is_throttled = 0
        
        # Manually insert with the mock timestamp to simulate historical log
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO telemetry (
                timestamp, cpu_usage_pct, ram_usage_pct, battery_pct, 
                battery_plugged_in, cpu_temp_c, active_power_plan, is_throttled
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp_str, cpu, ram, battery, plugged, temp, active_plan, is_throttled))
        conn.commit()
        conn.close()
        
    print(f"Successfully inserted {num_points} records.")

def main():
    # 1. Populate mock database
    populate_mock_data(minutes=25, interval_sec=5) # 25 minutes of logs (300 records)
    
    # 2. Instantiate and train predictor
    predictor = TempPredictor()
    print("\n--- Training Pipeline Verification ---")
    
    # Run training with min_records=100, forecasting 10 minutes (600s) ahead
    success = predictor.train(min_records=100, forecast_horizon_sec=600, tolerance_sec=30)
    
    if success:
        print("Training completed successfully!")
    else:
        print("Training failed.")
        sys.exit(1)
        
    # 3. Test Inference
    print("\n--- Inference Verification ---")
    conn = sqlite3.connect(DB_PATH)
    recent_df = pd.read_sql_query("SELECT * FROM telemetry ORDER BY timestamp DESC LIMIT 60", conn)
    conn.close()
    
    # Reverse to chronological order for prediction
    recent_df = recent_df.iloc[::-1].reset_index(drop=True)
    
    curr_cpu = recent_df.iloc[-1]['cpu_usage_pct']
    predicted_cpu = predictor.predict_future_cpu(recent_df)
    
    print(f"Current CPU Usage: {curr_cpu:.2f}%")
    print(f"Predicted CPU Usage 10 minutes from now: {predicted_cpu:.2f}%")
    
    if os.path.exists(predictor.model_path if hasattr(predictor, 'model_path') else "data/model.pkl"):
        print("Model file exists on disk: YES")
    else:
        print("Model file exists on disk: NO")

if __name__ == "__main__":
    main()
