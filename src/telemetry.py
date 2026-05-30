import time
import threading
import psutil
import subprocess
import os
import sys

# Add current directory to path to enable relative imports if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import log_telemetry

def get_active_scheme_info():
    """Queries powercfg to get the current power scheme GUID and its name."""
    try:
        result = subprocess.run(
            ["powercfg", "/getactivescheme"],
            capture_output=True,
            text=True,
            check=True
        )
        out = result.stdout.strip()
        if "GUID:" in out:
            parts = out.split("GUID:")
            guid_and_name = parts[1].strip()
            guid = guid_and_name.split()[0]
            name = guid_and_name.split("(")[-1].replace(")", "").strip()
            return guid, name
    except Exception as e:
        print(f"[Telemetry] Error querying active scheme: {e}")
    return "unknown_guid", "Unknown"

class TelemetryDaemon:
    def __init__(self, interval_sec=5):
        self.interval = interval_sec
        self.running = False
        self.thread = None
        self.last_cpu_percent = 0.0
        self.is_throttled = False  # Track current throttle state (in memory)
        self.has_win_tmp = False
        
        # Check if WinTmp is available
        try:
            import WinTmp
            self.has_win_tmp = True
        except Exception as e:
            self.has_win_tmp = False
            print(f"[Telemetry] WinTmp disabled due to import error: {e}")

    def query_temp(self):
        """Attempts to query the CPU temperature using WinTmp."""
        if not self.has_win_tmp:
            return None
        try:
            import WinTmp
            # Call the WinTmp CPU_Temp function
            temp = WinTmp.CPU_Temp()
            # If WinTmp returns 0.0 or a non-numeric error representation, handle it
            if isinstance(temp, (int, float)):
                return float(temp)
            return None
        except Exception:
            return None

    def collect_once(self):
        """Performs a single telemetry collection and database logging."""
        # CPU usage (non-blocking call, returns since last call)
        cpu_pct = psutil.cpu_percent(interval=None)
        
        # RAM usage
        ram_pct = psutil.virtual_memory().percent
        
        # Battery status
        battery = psutil.sensors_battery()
        if battery:
            battery_pct = battery.percent
            battery_plugged = battery.power_plugged
        else:
            # Default fallback for desktop computers
            battery_pct = 100.0
            battery_plugged = True
            
        # Temperature
        cpu_temp = self.query_temp()
        
        # Active power plan
        scheme_guid, scheme_name = get_active_scheme_info()
        plan_desc = f"{scheme_name} ({scheme_guid[:8]})"
        
        # Log to DB
        try:
            log_telemetry(
                cpu_usage_pct=cpu_pct,
                ram_usage_pct=ram_pct,
                battery_pct=battery_pct,
                battery_plugged_in=battery_plugged,
                cpu_temp_c=cpu_temp,
                active_power_plan=plan_desc,
                is_throttled=self.is_throttled
            )
        except Exception as e:
            print(f"[Telemetry] DB Log Error: {e}")
            
        return {
            "cpu_usage_pct": cpu_pct,
            "ram_usage_pct": ram_pct,
            "battery_pct": battery_pct,
            "battery_plugged_in": battery_plugged,
            "cpu_temp_c": cpu_temp,
            "active_power_plan": plan_desc,
            "is_throttled": self.is_throttled
        }

    def _loop(self):
        # Initialize psutil.cpu_percent (first call is always dummy/0.0)
        psutil.cpu_percent(interval=None)
        time.sleep(0.5)
        
        while self.running:
            start_time = time.time()
            self.collect_once()
            # Calculate sleep to maintain correct interval
            elapsed = time.time() - start_time
            sleep_time = max(0.1, self.interval - elapsed)
            
            # Sleep in small increments to allow responsive shutdown
            steps = int(sleep_time / 0.1)
            for _ in range(steps):
                if not self.running:
                    break
                time.sleep(0.1)
            # Sleep remainder
            if self.running:
                time.sleep(sleep_time % 0.1)

    def start(self):
        """Starts the daemon background thread."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        print(f"[Telemetry] Daemon started with interval {self.interval}s")

    def stop(self):
        """Stops the daemon background thread."""
        if not self.running:
            return
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("[Telemetry] Daemon stopped")

if __name__ == "__main__":
    from database import init_db
    init_db()
    
    daemon = TelemetryDaemon(interval_sec=2)
    daemon.start()
    try:
        print("Collecting 3 samples...")
        for i in range(3):
            time.sleep(2)
            data = daemon.collect_once()
            print(f"Sample {i+1}: {data}")
    finally:
        daemon.stop()
