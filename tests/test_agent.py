import unittest
import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Ensure src can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from decision_agent import DecisionAgent

class MockPredictor:
    def __init__(self, mock_pred_val):
        self.mock_pred_val = mock_pred_val

    def predict_future_cpu(self, recent_df):
        return self.mock_pred_val

class TestDecisionAgent(unittest.TestCase):
    def setUp(self):
        self.agent = DecisionAgent()
        # Set monitor-only mode for tests so it doesn't run actual powercfg commands on host
        self.agent.power_manager.monitor_only_mode = True

    def test_normal_operation_no_action(self):
        # Create normal telemetry data (CPU 20%, RAM 50%, Battery 80% charging)
        timestamps = [datetime.now() - timedelta(seconds=i*5) for i in range(10)]
        timestamps.reverse()
        
        df = pd.DataFrame({
            "timestamp": [t.strftime('%Y-%m-%d %H:%M:%S') for t in timestamps],
            "cpu_usage_pct": [20.0] * 10,
            "ram_usage_pct": [50.0] * 10,
            "battery_pct": [80.0] * 10,
            "battery_plugged_in": [1] * 10
        })
        
        predictor = MockPredictor(30.0) # predicted load: 30%
        result = self.agent.evaluate_and_act(df, predictor, auto_optimize=True)
        
        self.assertEqual(result["action"], "None")
        self.assertFalse(self.agent.is_throttled)

    def test_cpu_spike_triggers_throttle(self):
        # Create telemetry data
        timestamps = [datetime.now() - timedelta(seconds=i*5) for i in range(10)]
        timestamps.reverse()
        
        df = pd.DataFrame({
            "timestamp": [t.strftime('%Y-%m-%d %H:%M:%S') for t in timestamps],
            "cpu_usage_pct": [40.0] * 10,
            "ram_usage_pct": [50.0] * 10,
            "battery_pct": [80.0] * 10,
            "battery_plugged_in": [1] * 10
        })
        
        predictor = MockPredictor(85.0) # predicted load: 85% (>75%)
        result = self.agent.evaluate_and_act(df, predictor, auto_optimize=True)
        
        # In mock mode, actual powercfg call returns True but is_throttled is set based on action
        # Let's verify it triggers the "Throttle" action recommendation
        self.assertEqual(result["action"], "Throttle")

    def test_rapid_battery_discharge_triggers_throttle(self):
        # Create telemetry data showing rapid battery drop on battery power
        # Drop 3% in 150 seconds -> 72% drop per hour (rapid)
        timestamps = [datetime.now() - timedelta(seconds=(5-i)*30) for i in range(6)]
        
        df = pd.DataFrame({
            "timestamp": [t.strftime('%Y-%m-%d %H:%M:%S') for t in timestamps],
            "cpu_usage_pct": [15.0] * 6,
            "ram_usage_pct": [50.0] * 6,
            "battery_pct": [85.0, 84.4, 83.8, 83.2, 82.6, 82.0], # dropping
            "battery_plugged_in": [0] * 6 # not plugged in
        })
        
        predictor = MockPredictor(25.0) # CPU prediction is low
        
        discharge_rate, is_discharging = self.agent.calculate_discharge_rate(df)
        self.assertTrue(is_discharging)
        # Expected rate: 3% drop over 25 seconds = 0.12%/s = 432%/hr
        self.assertGreater(discharge_rate, 15.0)
        
        result = self.agent.evaluate_and_act(df, predictor, auto_optimize=True)
        self.assertEqual(result["action"], "Throttle")

    def test_restore_performance(self):
        self.agent.is_throttled = True # Simulate previously throttled state
        
        timestamps = [datetime.now() - timedelta(seconds=i*5) for i in range(10)]
        timestamps.reverse()
        
        df = pd.DataFrame({
            "timestamp": [t.strftime('%Y-%m-%d %H:%M:%S') for t in timestamps],
            "cpu_usage_pct": [15.0] * 10,
            "ram_usage_pct": [50.0] * 10,
            "battery_pct": [80.0] * 10,
            "battery_plugged_in": [1] * 10
        })
        
        predictor = MockPredictor(20.0) # low load
        result = self.agent.evaluate_and_act(df, predictor, auto_optimize=True)
        
        self.assertEqual(result["action"], "Restore")

if __name__ == "__main__":
    unittest.main()
