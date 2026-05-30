import os
import sys
import ctypes
import subprocess
import psutil

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except AttributeError:
        return False

def get_active_power_plan():
    try:
        # Run powercfg /getactivescheme to get the active plan GUID and name
        result = subprocess.run(
            ["powercfg", "/getactivescheme"],
            capture_output=True,
            text=True,
            check=True
        )
        output = result.stdout.strip()
        return output
    except Exception as e:
        return f"Error querying powercfg: {e}"

def get_power_plans_list():
    try:
        # Run powercfg /list to get all schemes
        result = subprocess.run(
            ["powercfg", "/list"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error listing power schemes: {e}"

def query_cpu_temp():
    try:
        import WinTmp
        # Inspect available attributes in WinTmp
        attrs = dir(WinTmp)
        print(f"[WinTmp] Available attributes/methods: {attrs}")
        
        # Try calling CPU_Temp
        if hasattr(WinTmp, 'CPU_Temp'):
            temp = WinTmp.CPU_Temp()
            return f"CPU Temperature: {temp}°C"
        else:
            # Fallback to other functions if CPU_Temp is not present
            return f"WinTmp imported successfully, but no CPU_Temp found. Attributes: {attrs}"
    except ImportError:
        return "WinTmp is not installed or failed to import."
    except Exception as e:
        return f"Error querying CPU temperature: {str(e)} (Ensure running as Administrator)"

def main():
    print("=" * 60)
    print("PERSONAL PC TEMPERATURE & POWER OPTIMIZER - TELEMETRY TEST")
    print("=" * 60)
    
    admin_status = is_admin()
    print(f"Running with Administrator Privileges: {admin_status}")
    print("-" * 60)
    
    # 1. CPU Telemetry
    print("--- CPU Telemetry ---")
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_cores = psutil.cpu_percent(interval=1, percpu=True)
    cpu_freq = psutil.cpu_freq()
    print(f"Overall CPU Usage: {cpu_percent}%")
    print(f"Per-Core CPU Usage: {cpu_cores}")
    if cpu_freq:
        print(f"CPU Frequency: Current={cpu_freq.current:.1f}MHz, Min={cpu_freq.min:.1f}MHz, Max={cpu_freq.max:.1f}MHz")
    print("-" * 60)
    
    # 2. Memory Telemetry
    print("--- Memory Telemetry ---")
    vm = psutil.virtual_memory()
    print(f"Total RAM: {vm.total / (1024**3):.2f} GB")
    print(f"Available RAM: {vm.available / (1024**3):.2f} GB")
    print(f"Used RAM: {vm.used / (1024**3):.2f} GB ({vm.percent}%)")
    print("-" * 60)
    
    # 3. Battery Telemetry
    print("--- Battery Telemetry ---")
    battery = psutil.sensors_battery()
    if battery:
        print(f"Battery Percentage: {battery.percent}%")
        print(f"Power Plugged In: {battery.power_plugged}")
        if battery.secsleft == psutil.POWER_TIME_UNLIMITED:
            print("Battery Time Remaining: Unlimited (Plugged in)")
        elif battery.secsleft == psutil.POWER_TIME_UNKNOWN:
            print("Battery Time Remaining: Unknown")
        else:
            hours = battery.secsleft // 3600
            minutes = (battery.secsleft % 3600) // 60
            print(f"Battery Time Remaining: {hours}h {minutes}m")
    else:
        print("Battery sensor not found (Desktop PC or virtual machine)")
    print("-" * 60)
    
    # 4. Power Schemes Telemetry
    print("--- Power Schemes (powercfg) ---")
    print(f"Active Power Scheme:\n{get_active_power_plan()}")
    print(f"\nAvailable Power Schemes:\n{get_power_plans_list()}")
    print("-" * 60)
    
    # 5. CPU Temperature Telemetry (WinTmp / LibreHardwareMonitor)
    print("--- Temperature Telemetry (WinTmp) ---")
    temp_result = query_cpu_temp()
    print(temp_result)
    print("=" * 60)

if __name__ == "__main__":
    main()
