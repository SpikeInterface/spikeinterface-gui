# SpikeInterface GUI Iframe Test

This is a simple test application that demonstrates how to embed the SpikeInterface GUI in an iframe and receive data from it.

## Overview

The test consists of:

1. `iframe_test.html` - A simple HTML page that embeds the SpikeInterface GUI in an iframe and displays data received from it
2. `iframe_server.py` - A Flask server that serves the HTML page and starts the Panel application

## How to Run

1. Install the required dependencies:
   ```bash
   pip install flask
   ```

2. Run the Flask server:
   ```bash
   python iframe_server.py
   ```

3. This will open a browser window with the test application. Click the "Start Test Server" button to launch the SpikeInterface GUI.

4. Once the GUI is loaded, navigate to the "curation" tab (you may need to look for it in the different zones of the interface).

5. Click the "Submit to parent" button in the curation view to send data to the parent window.

6. The received data will be displayed in the "Received Data" section of the parent window.

## How It Works

1. The Flask server serves the HTML page and provides an endpoint to start the Panel application.

2. The HTML page embeds the Panel application in an iframe.

3. The curationview.py file has been modified to send data to the parent window using the `postMessage` API when the "Submit to parent" button is clicked.

4. The parent window listens for messages from the iframe and displays the received data.

## Troubleshooting

- If the Panel application fails to start, check the console for error messages.
- If no data is received when clicking the "Submit to parent" button, make sure you're using the latest version of the curationview.py file with the fix for the DataCloneError.
- If you're running the Panel application separately, you can manually set the iframe URL using the `setIframeUrl` function in the browser console.

## Technical Details

The fix for the DataCloneError involves:

1. Converting the complex object to a JSON string before sending it to the parent window
2. Parsing the JSON string back to an object in the parent window

This avoids the issue where the browser tries to clone a complex object that contains non-cloneable properties.
