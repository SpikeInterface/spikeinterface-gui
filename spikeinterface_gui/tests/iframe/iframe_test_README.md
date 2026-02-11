# SpikeInterface GUI Iframe Test - Bidirectional Communication

This is a test application that demonstrates bidirectional communication between a parent window and the SpikeInterface GUI embedded in an iframe.

## Overview

The test consists of:

1. `iframe_test.html` - An HTML page that:
   - Embeds the SpikeInterface GUI in an iframe
   - Sends curation data TO the iframe
   - Receives curation data FROM the iframe
   
2. `iframe_server.py` - A Flask server that:
   - Serves the HTML page
   - Starts the Panel application

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

## Testing the Bidirectional Communication

### Test 1: Send Data to iframe (Parent → iframe)

1. Once the GUI is loaded, navigate to the "curation" tab
2. In the parent window, edit the curation data in the textarea
3. Click "Send to iframe" button
4. The GUI should refresh and display the new curation data in its tables
5. The "Auto send when ready" button will automatically send the curation data when the iframe is ready

### Test 2: Receive Data from iframe (iframe → Parent)

1. In the GUI's curation view, click the "Submit to parent" button
2. The data will appear in the "Received Data from iframe" section of the parent window
3. Multiple submissions will be accumulated and displayed

### Test 3: Clear All Curation

1. Click the "Clear All Curation" button
2. This sends an empty curation object to the iframe
3. All tables in the curation view should become empty

## How It Works

### Parent → iframe Communication

1. Parent window constructs a curation data object
2. The iframe sends a `loaded=true` message when ready to receive data
3. Sends it via `postMessage` with `type: 'curation-data'`
4. The iframe's JavaScript listener receives the message
5. Python updates `controller.set_curation_data` and refreshes the view

### iframe → Parent Communication

1. User clicks "Submit to parent" in the curation view
2. Python generates a JSON string of the curation model
3. JavaScript code is injected that sends the data via `postMessage`
4. Parent window's message listener receives the data
5. Data is parsed and displayed


## Technical Details

The curation data needs to follow the [`CurationModel`](https://spikeinterface.readthedocs.io/en/stable/api.html#curation-model).

### Message Format (Parent → iframe)
```javascript
{
  type: 'curation-data',
  data: {
    // Full curation model JSON
  }
}
```

### Message Format (iframe → Parent)
```javascript
{
  type: 'panel-data',
  data: {
    // Full curation model JSON
  }
}
```
