import subprocess
import sys
import time
import os

def run_services():
    # Get the path to the virtual environment's python executable
    if os.name == 'nt':  # Windows
        python_exe = os.path.join(".venv", "Scripts", "python.exe")
        streamlit_exe = os.path.join(".venv", "Scripts", "streamlit.exe")
    else:  # Unix
        python_exe = os.path.join(".venv", "bin", "python")
        streamlit_exe = os.path.join(".venv", "bin", "streamlit")

    # Verify existing of executables
    if not os.path.exists(python_exe):
        print(f"Error: Could not find {python_exe}. Make sure the virtual environment is created.")
        return

    print("🚀 Starting Opti-Quality System...")

    # 1. Start FastAPI Backend
    print("📡 Starting Backend (FastAPI) on http://localhost:8000...")
    backend_process = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    # Give the backend a moment to start
    time.sleep(3)

    # 2. Start Streamlit Frontend
    print("🎨 Starting Frontend (Streamlit) on http://localhost:8501...")
    frontend_process = subprocess.Popen(
        [python_exe, "-m", "streamlit", "run", "frontend/app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    print("\n✅ Both services are starting!")
    print("👉 Backend API: http://localhost:8000")
    print("👉 Frontend UI: http://localhost:8501")
    print("\nPress Ctrl+C to stop both services.")

    try:
        # Keep the script running to monitor the processes
        while True:
            # Check if processes are still running
            if backend_process.poll() is not None:
                print("\n❌ Backend process stopped unexpectedly.")
                break
            if frontend_process.poll() is not None:
                print("\n❌ Frontend process stopped unexpectedly.")
                break
            time.sleep(1)
            
            # Optionally print output (commented out to keep terminal clean)
            # print(backend_process.stdout.readline(), end="")
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")
        backend_process.terminate()
        frontend_process.terminate()
        print("Done.")

if __name__ == "__main__":
    run_services()
