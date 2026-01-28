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
   - Starts the Panel application with `listen_for_curation_changes=True`

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

Example curation data to send:
```json
{
  "merges": [
    {"unit_ids": [1, 2]},
    {"unit_ids": [5, 6, 7]}
  ],
  "removed": [3, 8],
  "splits": [
    {
      "unit_id": 4,
      "indices": [[0, 1, 2, 3, 4]]
    }
  ]
}
```

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
2. Sends it via `postMessage` with `type: 'curation-data'`
3. The iframe's JavaScript listener receives the message
4. The listener dispatches a custom event
5. Panel's jscallback receives the event and calls Python's `receive_curation_data` method
6. Python updates `controller.curation_data` and refreshes the view

### iframe → Parent Communication

1. User clicks "Submit to parent" in the curation view
2. Python generates a JSON string of the curation model
3. JavaScript code is injected that sends the data via `postMessage`
4. Parent window's message listener receives the data
5. Data is parsed and displayed

## Troubleshooting

- **Panel server fails to start**: Check the console for error messages
- **No data received when clicking "Send to iframe"**: 
  - Make sure `listen_for_curation_changes=True` is set
  - Check browser console for JavaScript errors
  - Verify the iframe has fully loaded
- **No data received when clicking "Submit to parent"**: 
  - Check that you're using the latest curationview.py
  - Look for JSON parsing errors in browser console

## Technical Details

### Message Format (Parent → iframe)
```javascript
{
  type: 'curation-data',
  data: {
    merges: [...],
    removed: [...],
    splits: [...]
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

### Required Settings

The Panel server must be started with:
```python
view_settings={
    "curation": {
        "listen_for_curation_changes": True
    }
}
```
