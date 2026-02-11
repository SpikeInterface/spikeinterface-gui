Creating Custom Views
=====================

The SpikeInterface GUI can be extended with custom views through a plugin system using Python's entry points.
This allows you to create specialized visualizations or analysis tools that integrate seamlessly with the GUI.

Overview
--------

A custom view plugin is a Python package that:

1. Contains one or more view classes that inherit from ``ViewBase``
2. Registers these views using entry points in ``pyproject.toml``
3. Can be installed via pip and automatically discovered by the GUI

The plugin system supports both the Qt (desktop) and Panel (web) backends.

Creating a Custom View Plugin
------------------------------

Plugin Structure
~~~~~~~~~~~~~~~~

A minimal plugin package has the following structure:

.. code-block:: text

    my_custom_view_plugin/
    ├── my_custom_view_plugin/
    │   ├── __init__.py
    │   ├── customview1.py
    │   └── customview2.py
    ├── pyproject.toml
    ├── LICENSE
    └── README.md

Minimal View Example
~~~~~~~~~~~~~~~~~~~~

Here's a minimal example of a custom view class:

.. code-block:: python

    from spikeinterface_gui.view_base import ViewBase

    class MyAwesomeView(ViewBase):
        # Unique identifier for this view (used in layouts)
        id = "myawesome"
        
        # Supported backends: ['qt'], ['panel'], or ['qt', 'panel']
        _supported_backend = ['qt']
        
        # Help text displayed to users
        _gui_help_txt = "My custom view that displays unit information"
        
        # Optional settings (None if no settings needed)
        _settings = None
        
        def _qt_make_layout(self):
            """Create the Qt widget layout (called once during initialization)"""
            from spikeinterface_gui.myqt import QT
            
            self.layout = QT.QVBoxLayout()
            self.qt_widget.setLayout(self.layout)
            
            self.label = QT.QLabel("Hello from custom view!")
            self.layout.addWidget(self.label)
        
        def _qt_refresh(self):
            """Update the view with current data (called when data changes)"""
            unit_count = len(self.controller.get_visible_unit_ids())
            self.label.setText(f"Visible units: {unit_count}")

Package Configuration
~~~~~~~~~~~~~~~~~~~~~

In your ``pyproject.toml`` file, configure the package and register the entry points:

.. code-block:: toml

    [project]
    name = "my-custom-view-plugin"
    version = "0.1.0"
    authors = [
      { name="Your Name", email="your.email@example.com" },
    ]
    description = "Custom view plugin for SpikeInterface GUI"
    requires-python = ">=3.10"
    dependencies = [
        "spikeinterface-gui>=0.12.0",
    ]

    [build-system]
    requires = ["setuptools>=62.0"]
    build-backend = "setuptools.build_meta"

    [tool.setuptools]
    packages = ["my_custom_view_plugin"]

    # Register your custom views
    [project.entry-points."spikeinterface_gui.views"]
    myawesome1 = "my_custom_view_plugin.customview1:MyAwesomeView1"
    myawesome2 = "my_custom_view_plugin.customview2:MyAwesomeView2"

The entry point format is: ``view_id = "package.module:ClassName"``

- **view_id**: The identifier used to reference the view in layouts
- **package.module:ClassName**: The import path to your view class

Installation and Usage
----------------------

Installing Your Plugin
~~~~~~~~~~~~~~~~~~~~~~

Install the plugin in development mode for testing:

.. code-block:: bash

    cd my_custom_view_plugin
    pip install -e .

Or install from PyPI (after publishing):

.. code-block:: bash

    pip install my-custom-view-plugin

Using Custom Views
~~~~~~~~~~~~~~~~~~

Once installed, custom views are automatically discovered and can be used in layouts:

.. code-block:: python

    from spikeinterface_gui import run_mainwindow

    app = run_mainwindow(
        analyzer,
        layout={
            'zone1': ['unitlist', 'myawesome1'],
            'zone2': ['waveform'],
            'zone3': ['myawesome2']
        },
        mode='desktop'
    )

Verifying Installation
~~~~~~~~~~~~~~~~~~~~~~

Check that your views are discovered:

.. code-block:: python

    import spikeinterface_gui as sigui
    
    # List all available views
    print(sigui.viewlist.possible_class_views.keys())
    
    # Check if your view is loaded
    assert 'myawesome1' in sigui.viewlist.possible_class_views
