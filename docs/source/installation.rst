Installation
============

For beginners users, please see our `installation tips <https://github.com/SpikeInterface/spikeinterface/tree/main/installation_tips>`_
where we provide a yaml for Mac/Windows/Linux to help properly install `spikeinterface` and `spikeinterface-gui` for you in a dedicated
``uv`` environment.

In your environment, if you wish to use the Desktop version of the GUI, you can do:

.. code-block:: bash

   pip install 'spikeinterface-gui[desktop]'

Note: this installs `PySide6`. You can use the `PyQt5` backend instead by uninstalling `PySide6` and then installing `PyQt5`.

If you wish to use the Web version of the GUI, you can do:

.. code-block:: bash

   pip install 'spikeinterface-gui[web]'

From source:

.. code-block:: bash

   git clone https://github.com/SpikeInterface/spikeinterface-gui.git
   cd spikeinterface-gui
   pip install .

You'll then need to install the appropriate backends yourself (`pyqtgraph` and `PySide6` or `PyQt5` for the desktop; `panel` and `bokeh` for web).