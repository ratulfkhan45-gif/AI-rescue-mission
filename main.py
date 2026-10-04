"""
main.py
-------
Entry point for AI Rescue Mission - Intelligent Disaster Response
Simulator. Starts a local web server and opens the HTML/CSS interface
in your browser:

    python main.py

Then use the page at http://127.0.0.1:8000/ (the next free port is used
if 8000 is busy). Press Ctrl+C in the terminal to stop the server.
"""

from web.server import run

if __name__ == "__main__":
    run()
