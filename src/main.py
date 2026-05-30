import os
import sys
import tkinter as tk

# Set up module paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gui import DashboardApp
from database import init_db

def main():
    print("=" * 60)
    print("PERSONAL PC TEMPERATURE & POWER OPTIMIZER - STARTING APP")
    print("=" * 60)
    
    # 1. Initialize SQLite Database
    init_db()
    
    # 2. Start Tkinter GUI (which orchestrates the telemetry thread and decision agent)
    root = tk.Tk()
    app = DashboardApp(root)
    
    # Run the Tkinter mainloop
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nKeyboard Interrupt detected. Shutting down application...")
        app.on_close()

if __name__ == "__main__":
    main()
