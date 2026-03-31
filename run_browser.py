"""Build and serve the game for the browser using Pygbag.

Usage:
    python run_browser.py

This will:
1. Install pygbag if needed
2. Build and serve the game on http://localhost:8000
3. Open your browser automatically
"""
import subprocess
import sys
import os
import webbrowser
import time
import threading

def ensure_pygbag():
    try:
        import pygbag
        return True
    except ImportError:
        print("Installing pygbag...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pygbag"])
        return True

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    ensure_pygbag()

    # Generate levels if needed
    if not os.path.exists("levels/world_1_1.json"):
        print("Pre-generating levels...")
        subprocess.run([sys.executable, "-c",
            "import sys; sys.path.insert(0,'.'); from levels.level_loader import generate_all_levels; generate_all_levels()"])

    print("\n" + "="*50)
    print("  Sonic Spaceship Platformer")
    print("  Building for browser with Pygbag...")
    print("  Open http://localhost:8000 in your browser")
    print("="*50 + "\n")

    # Open browser after a delay
    def open_browser():
        time.sleep(4)
        webbrowser.open("http://localhost:8000")

    threading.Thread(target=open_browser, daemon=True).start()

    # Run pygbag (serves on port 8000)
    subprocess.run([sys.executable, "-m", "pygbag", "--ume_block", "0", "."])

if __name__ == "__main__":
    main()
