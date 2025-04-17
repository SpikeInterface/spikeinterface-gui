import threading
import webbrowser
from pathlib import Path
import argparse
from flask import Flask, send_file, jsonify

app = Flask(__name__)
panel_server = None
panel_url = None
panel_thread = None
panel_port_global = None

@app.route('/')
def index():
    """Serve the iframe test HTML page"""
    return send_file('iframe_test.html')

@app.route('/start_test_server')
def start_test_server():
    """Start the Panel server in a separate thread"""
    global panel_server, panel_url, panel_thread, panel_port_global
    
    # If a server is already running, return its URL
    if panel_url:
        return jsonify({"success": True, "url": panel_url})
    
    # Make sure the test dataset exists
    test_folder = Path(__file__).parent / "my_dataset"
    if not test_folder.is_dir():
        from spikeinterface_gui.tests.testingtools import make_analyzer_folder
        make_analyzer_folder(test_folder)
    
    # Function to run the Panel server in a thread
    def run_panel_server():
        global panel_server, panel_url, panel_port_global
        try:
            # Start the Panel server with curation enabled
            # Use a direct import to avoid circular imports
            from spikeinterface import load_sorting_analyzer
            from spikeinterface_gui import run_mainwindow
            
            # Load the analyzer
            analyzer = load_sorting_analyzer(test_folder / "sorting_analyzer")
            
            # Start the Panel server directly
            win = run_mainwindow(
                analyzer,
                backend="panel",
                start_app=False,
                verbose=True,
                curation=True,
                make_servable=True
            )
            
            # Start the server manually
            import panel as pn
            pn.serve(win.main_layout, port=panel_port_global, address="localhost", show=False, start=True)
            
            # Get the server URL
            panel_url = f"http://localhost:{panel_port_global}"
            panel_server = win
            
            print(f"Panel server started at {panel_url}")
        except Exception as e:
            print(f"Error starting Panel server: {e}")
            import traceback
            traceback.print_exc()
    
    # Start the Panel server in a separate thread
    panel_thread = threading.Thread(target=run_panel_server)
    panel_thread.daemon = True
    panel_thread.start()
    
    # Give the server some time to start
    import time
    time.sleep(5)  # Increased wait time
    
    # Check if the server is actually running
    import requests
    try:
        response = requests.get(f"http://localhost:{panel_port_global}", timeout=2)
        if response.status_code == 200:
            return jsonify({"success": True, "url": f"http://localhost:{panel_port_global}"})
        else:
            return jsonify({"success": False, "error": f"Server returned status code {response.status_code}"})
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "error": f"Could not connect to Panel server: {str(e)}"})

@app.route('/stop_test_server')
def stop_test_server():
    """Stop the Panel server"""
    global panel_server, panel_url, panel_thread
    
    if panel_server:
        # Clean up resources
        # clean_all(Path(__file__).parent / 'my_dataset')
        panel_url = None
        panel_server = None
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "No server running"})

def main(flask_port=5000, panel_port=5006):
    """Start the Flask server and open the browser"""
    global panel_port_global
    panel_port_global = panel_port
    # Open the browser
    webbrowser.open(f'http://localhost:{flask_port}')
    
    # Start the Flask server
    app.run(debug=False, port=flask_port)


parser = argparse.ArgumentParser(description="Run the Flask and Panel servers.")
parser.add_argument('--flask-port', type=int, default=5000, help="Port for the Flask server (default: 5000)")
parser.add_argument('--panel-port', type=int, default=5006, help="Port for the Panel server (default: 5006)")

if __name__ == '__main__':
    args = parser.parse_args()

    main(flask_port=int(args.flask_port), panel_port=int(args.panel_port))
