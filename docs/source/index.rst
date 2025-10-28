.. spikeinterface-gui documentation master file, created by
   sphinx-quickstart on Fri Oct 10 12:53:19 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

SpikeInterface-GUI documentation
================================


GUI for the ``SortingAnalyzer`` object from SpikeInterface.

This is a cross platform interactive viewer to inspect the final results
and quality of any spike sorter supported by ``spikeinterface``.

This interactive GUI offers several views that dynamically refresh other views.
This allows us to very quickly check the strengths and weaknesses of any sorter output
and to perform manual curation.

This can be used as a replacement of `phy <https://github.com/cortex-lab/phy>`_.

This viewer has 2 modes:

Desktop
-------

This a local desktop app using internally Qt, fast and easy when the data is local

.. image:: images/gui_desktop.png
   :alt: desktop
   :width: 600px
   :align: center

Web
---

This is a web app internally using Panel, useful when the data is remote


.. image:: images/gui_web.png
   :alt: web
   :width: 600px
   :align: center



.. toctree::
   :maxdepth: 1
   :caption: Contents:

   installation
   launch
   usage
   custom_layout_settings
   deployments
   views
   developers
   credits
