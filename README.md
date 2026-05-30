# ⚡ Personal PC Temperature & Power Optimizer

An end-to-end Machine Learning project that predicts **future CPU utilization** and proactively optimizes processor power states to reduce overheating and battery drain. The project includes continuous telemetry collection, local SQLite storage, predictive modeling, automated power management, and an **interactive Tkinter desktop application**.

---

## 🚀 Project Overview

Modern laptops often experience overheating and rapid battery drain during intensive workloads. Traditional thermal management systems are reactive, reducing performance only after temperatures become critically high.

This project leverages Machine Learning to analyze historical system telemetry, including CPU utilization, memory usage, and battery status, to predict future resource demand and proactively optimize processor power settings.

The final outcome is a **desktop-based intelligent assistant** that continuously monitors system health and automatically adjusts CPU power limits using Windows power management commands, helping maintain system stability, reduce thermal stress, and extend battery life.

---

## ✨ Key Features

* Predicts future CPU utilization based on historical telemetry
* Combines CPU, memory, and battery status data
* Automated processor power optimization using Windows power settings
* Dynamic adjustment of processor limits for AC and battery modes
* Resilient fallback mechanisms for missing hardware sensor data
* Local SQLite-based telemetry storage
* Interactive Tkinter desktop application
* Live CPU utilization visualization with custom performance charts

---

## 🧠 Machine Learning Model

* **Algorithm:** Random Forest Regressor
* **Target Variable:** Future CPU Utilization (%)
* **Evaluation Metrics:**

  * R² Score
  * RMSE
  * MSE
* **Why Random Forest?**

  * Captures non-linear system usage patterns effectively
  * Robust against noisy telemetry data
  * Lightweight and suitable for local offline deployment
  * Provides reliable predictions for proactive system optimization

---

## 📊 Dataset Information

### System Telemetry Dataset

* Source: **psutil Python Library**
* Real-time system monitoring data
* Collected at regular intervals and stored locally
* Includes:

  * CPU utilization
  * Per-core CPU statistics
  * Memory usage
  * Battery percentage
  * Charging status

### Local Database Storage

* Source: **SQLite Database**
* Stores historical telemetry records
* Supports model retraining and future utilization prediction
* Fully offline and self-contained storage solution

---

## 📁 Project Structure

```text
personal-pc-power-optimizer/
│
├── test_env.py
├── verify_pipeline.py
├── requirements.txt
│
├── data/
│   ├── model.pkl
│   └── telemetry.db
│
├── src/
│   ├── database.py
│   ├── decision_agent.py
│   ├── gui.py
│   ├── main.py
│   ├── ml_predictor.py
│   └── telemetry.py
│
├── tests/
│   └── test_agent.py
│
├── screenshots/
│   ├── dashboard.png
│   └── verification.png
│
└── README.md
```

---

## 🖥️ Application Screenshots

### 🏠 Desktop Dashboard

```text
Screenshots/dashboard.png
```

### 📊 System Verification Dashboard

```text
Screenshots/verification.png
```

---

## ▶️ How to Run the Application

```bash
pip install -r requirements.txt
```

```bash
cd src
python src/main.py
```

**Note:** To allow automatic processor power adjustments, run Command Prompt as Administrator before launching the application or use the built-in elevation option within the GUI.
