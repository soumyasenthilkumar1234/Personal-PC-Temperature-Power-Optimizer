import os
import sys
import ctypes
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import pandas as pd
from datetime import datetime
import time

# Import components
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from telemetry import TelemetryDaemon, get_active_scheme_info
from ml_predictor import TempPredictor
from decision_agent import DecisionAgent
from database import init_db, DB_PATH

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except AttributeError:
        return False

def run_as_admin():
    try:
        # Re-run the python interpreter with admin rights for this script
        # sys.executable is path to python.exe
        # sys.argv[0] is path to main.py
        script = os.path.abspath(sys.argv[0])
        params = f'"{script}"'
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1
        )
        sys.exit(0)
    except Exception as e:
        messagebox.showerror("Elevation Failed", f"Could not restart with admin rights:\n{e}")

class DashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Personal PC Temperature & Power Optimizer")
        self.root.geometry("900x650")
        self.root.configure(bg="#121214")
        
        # Initialize Core Systems
        init_db()
        self.daemon = TelemetryDaemon(interval_sec=5)
        self.predictor = TempPredictor()
        self.agent = DecisionAgent()
        
        # UI State variables
        self.auto_optimize = tk.BooleanVar(value=True)
        self.admin_status = is_admin()
        
        # Styling configuration
        self.setup_styles()
        
        # Create Layout
        self.create_widgets()
        
        # Start Telemetry Daemon
        self.daemon.start()
        
        # Start periodic GUI updates
        self.update_gui_loop()
        
        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Dark mode styling for custom widgets
        style.configure("TFrame", background="#121214")
        style.configure("Card.TFrame", background="#1A1A1E", relief="flat")
        style.configure("TLabel", background="#121214", foreground="#FFFFFF")
        style.configure("CardLabel.TLabel", background="#1A1A1E", foreground="#FFFFFF")
        style.configure("ValueLabel.TLabel", background="#1A1A1E", foreground="#00D2C4", font=("Consolas", 18, "bold"))
        style.configure("TitleLabel.TLabel", background="#121214", foreground="#FFFFFF", font=("Segoe UI", 16, "bold"))
        
        style.configure("TButton", 
                        background="#2A2A30", 
                        foreground="#FFFFFF", 
                        bordercolor="#3A3A40",
                        lightcolor="#3A3A40",
                        darkcolor="#1A1A1E",
                        font=("Segoe UI", 9, "bold"),
                        padding=6)
        style.map("TButton",
                  background=[("active", "#00D2C4"), ("pressed", "#00A89D")],
                  foreground=[("active", "#121214")])
                  
        style.configure("AdminButton.TButton", 
                        background="#FF5F56", 
                        foreground="#FFFFFF",
                        bordercolor="#FF5F56",
                        font=("Segoe UI", 9, "bold"),
                        padding=6)
        style.map("AdminButton.TButton",
                  background=[("active", "#FF4B40"), ("pressed", "#D9362E")])

        style.configure("TCheckbutton", 
                        background="#1A1A1E", 
                        foreground="#FFFFFF",
                        font=("Segoe UI", 10))
        style.map("TCheckbutton",
                  background=[("active", "#1A1A1E")],
                  foreground=[("active", "#00D2C4")])

    def create_widgets(self):
        # 1. Header Frame
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill="x", side="top")
        
        title = ttk.Label(header, text="PERSONAL PC POWER & TEMP OPTIMIZER", style="TitleLabel.TLabel")
        title.pack(side="left")
        
        # Elevation status indicator
        elev_frame = ttk.Frame(header)
        elev_frame.pack(side="right")
        
        elev_lbl = ttk.Label(elev_frame, text="ELEVATED STATUS: ")
        elev_lbl.pack(side="left")
        
        status_color = "#27C93F" if self.admin_status else "#FF5F56"
        status_text = "YES (ADMIN)" if self.admin_status else "NO (MONITOR ONLY)"
        
        self.elev_status_val = tk.Label(elev_frame, text=status_text, fg=status_color, bg="#121214", font=("Segoe UI", 10, "bold"))
        self.elev_status_val.pack(side="left")
        
        if not self.admin_status:
            admin_btn = ttk.Button(elev_frame, text="Run as Admin", command=run_as_admin, style="AdminButton.TButton")
            admin_btn.pack(side="left", padx=10)

        # 2. Main content area splits (Top: Cards, Middle: Charts, Bottom: Logs)
        main_container = ttk.Frame(self.root, padding=10)
        main_container.pack(fill="both", expand=True)

        # Dashboard metrics row
        metrics_row = ttk.Frame(main_container)
        metrics_row.pack(fill="x", pady=10)
        
        # Create Card helper
        def create_card(parent, title_text, col):
            card = ttk.Frame(parent, style="Card.TFrame", padding=15)
            card.grid(row=0, column=col, sticky="nsew", padx=5)
            parent.grid_columnconfigure(col, weight=1)
            
            lbl_title = ttk.Label(card, text=title_text, style="CardLabel.TLabel", font=("Segoe UI", 9))
            lbl_title.pack(anchor="w")
            
            lbl_val = ttk.Label(card, text="--", style="ValueLabel.TLabel")
            lbl_val.pack(anchor="w", pady=5)
            return lbl_val
            
        self.card_cpu = create_card(metrics_row, "CURRENT CPU LOAD", 0)
        self.card_pred_cpu = create_card(metrics_row, "PREDICTED LOAD (10 MIN)", 1)
        self.card_temp = create_card(metrics_row, "CPU TEMPERATURE", 2)
        self.card_battery = create_card(metrics_row, "BATTERY STATUS", 3)

        # Status & Toggle Row
        ctrl_row = ttk.Frame(main_container, style="Card.TFrame", padding=10)
        ctrl_row.pack(fill="x", pady=5)
        
        self.chk_auto = ttk.Checkbutton(ctrl_row, text="Auto-Throttling Optimization", variable=self.auto_optimize)
        self.chk_auto.pack(side="left", padx=10)
        
        self.lbl_active_plan = ttk.Label(ctrl_row, text="Active Power Plan: Checking...", style="CardLabel.TLabel", font=("Segoe UI", 10, "italic"))
        self.lbl_active_plan.pack(side="left", padx=30)
        
        btn_train = ttk.Button(ctrl_row, text="Force Model Retrain", command=self.trigger_retrain)
        btn_train.pack(side="right", padx=10)
        
        # Chart & Logs division (Horizontal Split)
        workspace_row = ttk.Frame(main_container)
        workspace_row.pack(fill="both", expand=True, pady=10)
        workspace_row.grid_rowconfigure(0, weight=1)
        workspace_row.grid_columnconfigure(0, weight=3) # Chart
        workspace_row.grid_columnconfigure(1, weight=2) # System Logs

        # 3. Canvas Real-Time Chart
        chart_frame = ttk.Frame(workspace_row, style="Card.TFrame", padding=10)
        chart_frame.grid(row=0, column=0, sticky="nsew", padx=5)
        
        chart_lbl = ttk.Label(chart_frame, text="REAL-TIME CPU UTILIZATION HISTORY (%)", style="CardLabel.TLabel", font=("Segoe UI", 9, "bold"))
        chart_lbl.pack(anchor="w")
        
        self.chart_canvas = tk.Canvas(chart_frame, bg="#1E1E24", bd=0, highlightthickness=0)
        self.chart_canvas.pack(fill="both", expand=True, pady=5)

        # 4. Console log output
        log_frame = ttk.Frame(workspace_row, style="Card.TFrame", padding=10)
        log_frame.grid(row=0, column=1, sticky="nsew", padx=5)
        
        log_lbl = ttk.Label(log_frame, text="DECISION AGENT LOGS", style="CardLabel.TLabel", font=("Segoe UI", 9, "bold"))
        log_lbl.pack(anchor="w")
        
        self.console = tk.Text(log_frame, bg="#1E1E24", fg="#CCCCCC", font=("Consolas", 8), state="disabled", wrap="word", bd=0, highlightthickness=0)
        self.console.pack(fill="both", expand=True, pady=5)

    def write_console(self, text):
        self.console.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console.insert("end", f"[{timestamp}] {text}\n")
        self.console.see("end")
        self.console.configure(state="disabled")

    def draw_chart(self, cpu_history):
        self.chart_canvas.delete("all")
        w = self.chart_canvas.winfo_width()
        h = self.chart_canvas.winfo_height()
        
        if w < 10 or h < 10:
            return
            
        padding_x = 40
        padding_y = 20
        chart_w = w - padding_x - 10
        chart_h = h - (padding_y * 2)
        
        # Draw background grids
        for i in range(5):
            y_val = 100 - (i * 25)
            y_coord = padding_y + (i * (chart_h / 4))
            self.chart_canvas.create_line(padding_x, y_coord, w - 10, y_coord, fill="#2C2C35", width=1)
            self.chart_canvas.create_text(padding_x - 15, y_coord, text=f"{y_val}%", fill="#8A8A93", font=("Segoe UI", 8))
            
        if not cpu_history:
            return
            
        # Draw line graph
        max_points = 60
        history = cpu_history[-max_points:]
        num_points = len(history)
        
        x_step = chart_w / (max_points - 1) if max_points > 1 else chart_w
        
        coords = []
        for i, val in enumerate(history):
            # Calculate x and y coordinates
            # Account for missing points by shifting to the right end
            index_offset = max_points - num_points + i
            cx = padding_x + (index_offset * x_step)
            cy = padding_y + chart_h - (val / 100.0 * chart_h)
            coords.append((cx, cy))
            
        # Draw fill area
        if len(coords) > 1:
            poly_coords = [padding_x + ((max_points - num_points) * x_step), padding_y + chart_h]
            for cx, cy in coords:
                poly_coords.extend([cx, cy])
            poly_coords.extend([coords[-1][0], padding_y + chart_h])
            # Draw semi-transparent grid polygon (using stipple or color blending)
            self.chart_canvas.create_polygon(poly_coords, fill="#0F3836", outline="")

        # Draw glowing line
        for i in range(len(coords) - 1):
            x1, y1 = coords[i]
            x2, y2 = coords[i+1]
            self.chart_canvas.create_line(x1, y1, x2, y2, fill="#00D2C4", width=2, smooth=True)

    def trigger_retrain(self):
        self.write_console("Starting forced ML model retraining on main thread...")
        success = self.predictor.train(min_records=100)
        if success:
            self.write_console("Model retrained successfully. Loaded weights refreshed.")
            messagebox.showinfo("Success", "Model retrained successfully!")
        else:
            self.write_console("Model retraining failed. Less than 100 historical data points spanning 10m horizon.")
            messagebox.showwarning("Incomplete", "Could not train: database needs at least 10 minutes of logged historical activity.")

    def update_gui_loop(self):
        try:
            # 1. Fetch latest data from database
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query("SELECT * FROM telemetry ORDER BY timestamp DESC LIMIT 60", conn)
            conn.close()
            
            if not df.empty:
                # Reverse to chronological order
                recent_df = df.iloc[::-1].reset_index(drop=True)
                latest_data = recent_df.iloc[-1]
                
                # Update Card values
                self.card_cpu.configure(text=f"{latest_data['cpu_usage_pct']:.1f}%")
                
                temp_val = latest_data['cpu_temp_c']
                if temp_val is not None:
                    self.card_temp.configure(text=f"{temp_val:.1f}°C")
                else:
                    self.card_temp.configure(text="N/A (No Admin)", font=("Consolas", 12, "bold"))
                    
                bat_pct = latest_data['battery_pct']
                bat_plugged = latest_data['battery_plugged_in'] == 1
                bat_text = f"{int(bat_pct)}% " + ("(AC)" if bat_plugged else "(Bat)")
                self.card_battery.configure(text=bat_text)
                
                # Active Power plan
                active_guid, active_name = get_active_scheme_info()
                throttle_suffix = " [THROTTLED]" if self.agent.is_throttled else ""
                self.lbl_active_plan.configure(text=f"Active Power Scheme: {active_name} ({active_guid[:8]}){throttle_suffix}")
                
                # 2. Evaluate Decision Loop
                eval_res = self.agent.evaluate_and_act(
                    recent_df=recent_df,
                    predictor=self.predictor,
                    auto_optimize=self.auto_optimize.get()
                )
                
                # Update cards and logs
                pred_cpu = eval_res['predicted_cpu']
                self.card_pred_cpu.configure(text=f"{pred_cpu:.1f}%")
                
                # Log action changes
                if eval_res['action'] != "None":
                    self.write_console(f"ACTION TRIGGERED: {eval_res['action']}. Info: {eval_res['status_msg']}")
                elif int(time.time()) % 30 < 5:  # Print heartbeat log every ~30 seconds
                    self.write_console(f"System health check: Predicted Future CPU load is {pred_cpu:.1f}%. Status: {eval_res['status_msg']}")
                    
                # Update memory tracker in Daemon
                self.daemon.is_throttled = self.agent.is_throttled
                
                # 3. Update Chart
                cpu_history = recent_df['cpu_usage_pct'].tolist()
                self.draw_chart(cpu_history)
                
        except Exception as e:
            self.write_console(f"GUI Loop Error: {e}")
            
        # Re-schedule update in 2.5 seconds (twice as fast as logging interval to keep graph smooth)
        self.root.after(2500, self.update_gui_loop)

    def on_close(self):
        # Stop background threads gracefully
        self.write_console("Stopping telemetry background daemon...")
        self.daemon.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = DashboardApp(root)
    root.mainloop()
