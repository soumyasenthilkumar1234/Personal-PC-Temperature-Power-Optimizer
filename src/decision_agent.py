import subprocess
import os
import sys
import pandas as pd
import numpy as np

class PowerSchemeManager:
    def __init__(self):
        self.monitor_only_mode = False
        self.last_status_msg = "Initialized"

    def run_powercfg(self, args):
        """Runs a powercfg command, catching permissions and other errors."""
        if self.monitor_only_mode:
            return False
            
        try:
            # Using startupinfo to hide CMD window if executed from GUI without console
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0 # SW_HIDE

            result = subprocess.run(
                ["powercfg"] + args,
                capture_output=True,
                text=True,
                check=True,
                startupinfo=startupinfo
            )
            return True
        except (subprocess.CalledProcessError, PermissionError, FileNotFoundError) as e:
            self.monitor_only_mode = True
            self.last_status_msg = f"Access Denied or powercfg failed: {e}. Falling back to Monitor & Alert Only mode."
            print(f"[PowerManager] {self.last_status_msg}")
            return False

    def apply_throttle(self, throttle_pct):
        """Throttles both E-cores and P-cores under AC and DC profiles to throttle_pct (e.g., 60)."""
        print(f"[PowerManager] Attempting to set Maximum Processor State to {throttle_pct}%")
        
        # E-Cores (PROCTHROTTLEMAX)
        ac_e = self.run_powercfg(["/setacvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX", str(throttle_pct)])
        dc_e = self.run_powercfg(["/setdcvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX", str(throttle_pct)])
        
        # P-Cores (PROCTHROTTLEMAX1)
        ac_p = self.run_powercfg(["/setacvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX1", str(throttle_pct)])
        dc_p = self.run_powercfg(["/setdcvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX1", str(throttle_pct)])
        
        # Apply changes active
        applied = self.run_powercfg(["/setactive", "SCHEME_CURRENT"])
        
        if ac_e and dc_e and ac_p and dc_p and applied:
            self.last_status_msg = f"Throttled CPU successfully to {throttle_pct}%"
            return True
        return False

    def restore_full_performance(self):
        """Restores both E-cores and P-cores under AC and DC profiles to 100%."""
        print("[PowerManager] Restoring Maximum Processor State to 100%")
        
        # E-Cores (PROCTHROTTLEMAX)
        ac_e = self.run_powercfg(["/setacvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX", "100"])
        dc_e = self.run_powercfg(["/setdcvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX", "100"])
        
        # P-Cores (PROCTHROTTLEMAX1)
        ac_p = self.run_powercfg(["/setacvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX1", "100"])
        dc_p = self.run_powercfg(["/setdcvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX1", "100"])
        
        # Apply changes active
        applied = self.run_powercfg(["/setactive", "SCHEME_CURRENT"])
        
        if ac_e and dc_e and ac_p and dc_p and applied:
            self.last_status_msg = "Restored CPU to 100% (unthrottled)"
            return True
        return False

class DecisionAgent:
    def __init__(self):
        self.power_manager = PowerSchemeManager()
        self.is_throttled = False

    def calculate_discharge_rate(self, recent_df):
        """Calculates battery discharge rate in percentage per hour from recent logs.
        
        Returns discharge_rate_pct_hr (float) and boolean indicating if discharging.
        """
        if len(recent_df) < 5:
            return 0.0, False
            
        try:
            df = recent_df.copy()
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            
            # Check if plugged in at the latest record
            latest = df.iloc[-1]
            if latest['battery_plugged_in'] == 1:
                return 0.0, False
                
            # Compute total time delta and battery percentage change
            first = df.iloc[0]
            time_delta_sec = (latest['timestamp'] - first['timestamp']).total_seconds()
            
            if time_delta_sec < 60:
                return 0.0, False
                
            battery_delta = first['battery_pct'] - latest['battery_pct']
            
            # If battery_delta is positive, it means discharging
            if battery_delta > 0:
                discharge_rate = (battery_delta / time_delta_sec) * 3600.0
                return discharge_rate, True
        except Exception as e:
            print(f"[DecisionAgent] Error calculating discharge rate: {e}")
            
        return 0.0, False

    def evaluate_and_act(self, recent_df, predictor, auto_optimize=True):
        """Analyzes recent telemetry and predictions, making optimization actions.
        
        Returns:
            dict: {
                "predicted_cpu": float,
                "discharge_rate": float,
                "action": str ("Throttle" | "Restore" | "None"),
                "status_msg": str
            }
        """
        if recent_df.empty:
            return {
                "predicted_cpu": 0.0,
                "discharge_rate": 0.0,
                "action": "None",
                "status_msg": "No telemetry data available"
            }
            
        # 1. Get Prediction for CPU 10 minutes in the future
        predicted_cpu = predictor.predict_future_cpu(recent_df)
        
        # 2. Get battery discharge rate
        discharge_rate, is_discharging = self.calculate_discharge_rate(recent_df)
        
        # 3. Determine if throttle is needed
        # Thresholds: Predicted CPU usage > 75% OR discharge rate > 15% per hour
        need_throttle = (predicted_cpu > 75.0) or (is_discharging and discharge_rate > 15.0)
        
        action = "None"
        status_msg = "System operating within normal limits."
        
        if need_throttle:
            if not self.is_throttled:
                action = "Throttle"
                if auto_optimize:
                    success = self.power_manager.apply_throttle(60)  # Throttling to 60%
                    if success:
                        self.is_throttled = True
                        status_msg = "CPU throttled due to predicted high load or rapid battery discharge."
                    else:
                        status_msg = f"Throttle action triggered but failed. {self.power_manager.last_status_msg}"
                else:
                    status_msg = "Optimization triggered but skipped (Auto-Optimization OFF)."
            else:
                status_msg = "CPU is already throttled."
        else:
            if self.is_throttled:
                action = "Restore"
                if auto_optimize:
                    success = self.power_manager.restore_full_performance()
                    if success:
                        self.is_throttled = False
                        status_msg = "CPU restored to 100% performance."
                    else:
                        status_msg = f"Restore action triggered but failed. {self.power_manager.last_status_msg}"
                else:
                    status_msg = "Throttling removal triggered but skipped (Auto-Optimization OFF)."
            else:
                status_msg = "CPU running at full capacity."
                
        if self.power_manager.monitor_only_mode:
            status_msg = f"[Monitor-Only Mode] {status_msg} (Powercfg commands disabled/unprivileged)"
            
        return {
            "predicted_cpu": predicted_cpu,
            "discharge_rate": discharge_rate,
            "action": action,
            "status_msg": status_msg
        }

if __name__ == "__main__":
    agent = DecisionAgent()
    print("DecisionAgent module initialized.")
