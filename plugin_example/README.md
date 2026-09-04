# SpikeInterface GUI Plugin Example

This is a complete, working example of a custom view plugin for the SpikeInterface GUI. 
It demonstrates how to create custom views that integrate seamlessly with the GUI using Python's entry points system.

To create a custom view plugin, you can use this example as a template. 
A plugin can include one or more custom views that extend the GUI's functionality.

### Build a new custom view plugin package

The plugin is a Python package with the following minimal structure (assuming the package is 
called `my_custom_view_plugin`):

```
├── my_custom_view_plugin/ # main src folder with code
    ├── __init__.py
    ├── customview1.py
    ├── customview2.py
├── pyproject.toml
├── README.md (optional)
```

The `customview1.py` file contains the implementation of your custom view class, which should inherit from `ViewBase`.

Here is a minimal example of a custom view class:

```python
from spikeinterface_gui.view_base import ViewBase

class MyAwsome1View(ViewBase):
    id = "myawesome1"  # this is the lowercase version of the class name minus "View"
    _supported_backend = ['qt'] # or  ["qt", "panel"] if you implement both backends
    _gui_help_txt = "My custom view"
    _settings = {
        {
            'name': 'max_units',
            'type': 'int',
            'value': 10,
            'default': 10,
            'label': 'Maximum units to display'
        },
    }
    
    def _qt_make_layout(self):
        from spikeinterface_gui.myqt import QT
        self.layout = QT.QVBoxLayout()
        self.qt_widget.setLayout(self.layout)
        self.label = QT.QLabel("Hello!")
        self.layout.addWidget(self.label)
    
    def _qt_refresh(self):
        unit_count = len(self.controller.get_visible_unit_ids())
        self.label.setText(f"Visible units: {unit_count}")

    def _panel_make_layout(self):
        import panel as pn
        self.text_pane = pn.pane.Markdown("# My Awesome View")
        self.layout = pn.Column(self.text_pane)

    def _panel_refresh(self):
        unit_count = len(self.controller.get_visible_unit_ids())
        self.text_pane.object = f"Visible units: {unit_count}"
```

To register your custom view with the SpikeInterface GUI, add an entry point in your `pyproject.toml` file:

```toml
[project.entry-points."spikeinterface_gui.views"]
myawesome1 = "my_custom_view_plugin.customview1:MyAwsome1View"
myawesome2 = "my_custom_view_plugin.customview2:MyAwsome2View"
```

This will automatically make your custom view available in the `SpikeInterface-GUI`.


### Use your custom plugin

Before using your custom plugin, you need to install it.

```bash
cd plugin_example
pip install -e .
```
(or pip-install it if distributed on PyPI)

Now you can use your custom view in the SpikeInterface GUI by including it in your layout configuration:

```python
from spikeinterface_gui import run_mainwindow

# Include 'customview' in your layout
app = run_mainwindow(
    analyzer,
    layout={
        'zone1': ['unitlist', 'myawesome1'],
        'zone2': ['waveform'],
        'zone3': ['myawesome2']
    },
    mode='desktop'
)
```

**Happy plugin development!** 🎉

If you create something cool, please share it with the SpikeInterface community!
