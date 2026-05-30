import os
import sys
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor

# Ensure database module can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import get_historical_data

MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
MODEL_PATH = os.path.join(MODEL_DIR, "model.pkl")

class TempPredictor:
    def __init__(self):
        self.model = None
        self.features = [
            'cpu_usage_pct', 'cpu_usage_roll_1m', 'cpu_usage_roll_5m',
            'ram_usage_pct', 'battery_pct', 'battery_plugged_in',
            'hour', 'minute'
        ]
        self.load_model()

    def load_model(self):
        """Loads the serialized model if it exists."""
        if os.path.exists(MODEL_PATH):
            try:
                with open(MODEL_PATH, 'rb') as f:
                    data = pickle.load(f)
                    self.model = data.get('model')
                    self.features = data.get('features', self.features)
                print("[ML Predictor] Model loaded successfully.")
            except Exception as e:
                print(f"[ML Predictor] Error loading model: {e}")
                self.model = None

    def save_model(self):
        """Serializes and saves the model."""
        os.makedirs(MODEL_DIR, exist_ok=True)
        try:
            with open(MODEL_PATH, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'features': self.features,
                    'saved_at': datetime.now().isoformat()
                }, f)
            print(f"[ML Predictor] Model saved to {MODEL_PATH}")
            return True
        except Exception as e:
            print(f"[ML Predictor] Error saving model: {e}")
            return False

    def train(self, min_records=50, forecast_horizon_sec=600, tolerance_sec=30):
        """Trains the Random Forest model on historical telemetry logs."""
        print("[ML Predictor] Fetching data for training...")
        df = get_historical_data(limit=50000)
        
        if len(df) < min_records:
            print(f"[ML Predictor] Training aborted. Insufficient records (have {len(df)}, need {min_records}).")
            return False

        print(f"[ML Predictor] Preprocessing {len(df)} records...")
        X, y = self._prepare_data(df, forecast_horizon_sec, tolerance_sec)
        
        if X is None or len(X) < 10:
            print("[ML Predictor] Training aborted. Not enough valid feature-target pairs spanning the 10-minute horizon.")
            return False

        print(f"[ML Predictor] Training Random Forest Regressor on {len(X)} samples...")
        model = RandomForestRegressor(n_estimators=50, max_depth=8, random_state=42, n_jobs=-1)
        model.fit(X, y)
        
        self.model = model
        self.save_model()
        return True

    def _prepare_data(self, df, forecast_horizon_sec=600, tolerance_sec=30):
        """Preprocesses telemetry logs into ML feature matrix X and target y."""
        try:
            df = df.copy()
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # Calculate rolling features using a datetime index
            df.set_index('timestamp', inplace=True)
            df['cpu_usage_roll_1m'] = df['cpu_usage_pct'].rolling('1Min', min_periods=1).mean()
            df['cpu_usage_roll_5m'] = df['cpu_usage_pct'].rolling('5Min', min_periods=1).mean()
            df.reset_index(inplace=True)
            
            # Extract time features
            df['hour'] = df['timestamp'].dt.hour
            df['minute'] = df['timestamp'].dt.minute
            
            # Match current row with row in the future (timestamp + forecast_horizon_sec)
            timestamps = df['timestamp'].values
            cpu_usages = df['cpu_usage_pct'].values
            
            targets = []
            valid_indices = []
            
            for i, t in enumerate(timestamps):
                future_t = t + np.timedelta64(forecast_horizon_sec, 's')
                idx = np.searchsorted(timestamps, future_t)
                
                best_idx = None
                best_diff = None
                
                # Check surrounding indices for the closest match within tolerance
                for test_idx in [idx - 1, idx, idx + 1]:
                    if 0 <= test_idx < len(timestamps):
                        diff = abs((timestamps[test_idx] - future_t) / np.timedelta64(1, 's'))
                        if diff <= tolerance_sec:
                            if best_diff is None or diff < best_diff:
                                best_diff = diff
                                best_idx = test_idx
                                
                if best_idx is not None:
                    targets.append(cpu_usages[best_idx])
                    valid_indices.append(i)
            
            if not valid_indices:
                return None, None
                
            features_df = df.iloc[valid_indices].copy()
            X = features_df[self.features]
            y = np.array(targets)
            return X, y
            
        except Exception as e:
            print(f"[ML Predictor] Preprocessing error: {e}")
            return None, None

    def predict_future_cpu(self, recent_df):
        """Predicts the CPU utilization 10 minutes in the future based on recent telemetry.
        
        recent_df: A pandas DataFrame containing recent telemetry records (at least last 5 minutes of data).
        """
        if self.model is None:
            # Fallback to current CPU usage if model is not trained yet
            if not recent_df.empty:
                return float(recent_df.iloc[-1]['cpu_usage_pct'])
            return 20.0  # Safe default baseline
            
        try:
            # Prepare current features
            df = recent_df.copy()
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # Calculate rolling metrics
            df.set_index('timestamp', inplace=True)
            df['cpu_usage_roll_1m'] = df['cpu_usage_pct'].rolling('1Min', min_periods=1).mean()
            df['cpu_usage_roll_5m'] = df['cpu_usage_pct'].rolling('5Min', min_periods=1).mean()
            df.reset_index(inplace=True)
            
            # Time features
            df['hour'] = df['timestamp'].dt.hour
            df['minute'] = df['timestamp'].dt.minute
            
            # Extract last row as our current feature vector
            last_row = df.iloc[-1]
            X_curr = pd.DataFrame([last_row[self.features]])
            
            prediction = self.model.predict(X_curr)[0]
            return float(prediction)
        except Exception as e:
            print(f"[ML Predictor] Inference error: {e}")
            if not recent_df.empty:
                return float(recent_df.iloc[-1]['cpu_usage_pct'])
            return 20.0

if __name__ == "__main__":
    predictor = TempPredictor()
    print("Initializing TempPredictor module.")
