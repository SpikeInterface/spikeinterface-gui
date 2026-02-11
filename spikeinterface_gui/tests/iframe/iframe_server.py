import threading
import webbrowser
from pathlib import Path
import argparse
import socket
import time

from flask import Flask, send_file, jsonify

app = Flask(__name__)

PANEL_HOST = "localhost"  # <- switch back to localhost

panel_server = None
panel_url = None
panel_thread = None
panel_port_global = None
panel_last_error = None


def _wait_for_port(host: str, port: int, timeout_s: float = 20.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.25):
                return True
        except OSError:
            time.sleep(0.1)
    return False


@app.route("/")
def index():
    here = Path(__file__).parent
    return send_file(str(here / "iframe_test.html"))


@app.route("/curation.json")
def curation_json():
    here = Path(__file__).parent
    return send_file(str(here / "curation.json"))


@app.route("/start_test_server")
def start_test_server():
    global panel_server, panel_url, panel_thread, panel_port_global, panel_last_error

    if panel_url:
        return jsonify({"success": True, "url": panel_url})

    panel_last_error = None

    test_folder = Path(__file__).parent / "my_dataset"
    if not test_folder.is_dir():
        from spikeinterface_gui.tests.testingtools import make_analyzer_folder

        make_analyzer_folder(test_folder)

    def run_panel_server():
        global panel_server, panel_url, panel_port_global, panel_last_error
        try:
            import panel as pn
            from spikeinterface import load_sorting_analyzer
            from spikeinterface_gui import run_mainwindow

            pn.extension("tabulator", "gridstack")

            analyzer = load_sorting_analyzer(test_folder / "sorting_analyzer")

            def app_factory():
                win = run_mainwindow(
                    analyzer,
                    mode="web",
                    start_app=False,
                    verbose=True,
                    curation=True,
                    panel_window_servable=True,
                )
                return win.main_layout

            allowed = [
                f"localhost:{int(panel_port_global)}",
                f"127.0.0.1:{int(panel_port_global)}",
            ]
            print(panel_port_global)
            server = pn.serve(
                app_factory,
                port=int(panel_port_global),
                address=PANEL_HOST,
                allow_websocket_origin=allowed,
                show=False,
                start=False,
            )

            panel_server = server
            panel_url = f"http://{PANEL_HOST}:{panel_port_global}/"
            print(f"Panel server starting at {panel_url} (allow_websocket_origin={allowed})")

            server.start()
            server.io_loop.start()

        except Exception as e:
            panel_last_error = repr(e)
            panel_server = None
            panel_url = None
            import traceback

            traceback.print_exc()

    panel_thread = threading.Thread(target=run_panel_server, daemon=True)
    panel_thread.start()

    if not _wait_for_port("127.0.0.1", int(panel_port_global), timeout_s=30.0):
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Panel server did not become ready (port not open).",
                    "panel_host": PANEL_HOST,
                    "panel_port": panel_port_global,
                    "last_error": panel_last_error,
                }
            ),
            500,
        )

    return jsonify({"success": True, "url": panel_url})


def main(flask_port=5000, panel_port=5007):
    global panel_port_global
    panel_port_global = panel_port
    webbrowser.open(f"http://localhost:{flask_port}")
    app.run(debug=False, port=flask_port, host="localhost")


parser = argparse.ArgumentParser(description="Run the Flask and Panel servers.")
parser.add_argument("--flask-port", type=int, default=5000)
parser.add_argument("--panel-port", type=int, default=5006)

if __name__ == "__main__":
    args = parser.parse_args()
    main(flask_port=int(args.flask_port), panel_port=int(args.panel_port))
