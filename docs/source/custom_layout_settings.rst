Customizing layout and settings
===============================

You can create your own custom layout by specifying which views you'd like
to see, and where they go. The basic window layout supports eight "zones",
which are laid out as follows:

.. code-block:: bash

    +---------------+--------------+
    | zone1   zone2 | zone3  zone4 |
    +               +              +
    | zone5   zone6 | zone7  zone8 |
    +---------------+--------------+

If a zone has free space below it or to the right of it, it will try to use it.
Stretching downwards takes precedence over stretching rightwards.
E.g. suppose your layout is only non-empty in zones 1, 4, 5, 6 and 7:

.. code-block:: bash

    +---------------+--------------+
    | zone1         |        zone4 |
    +               +              +
    | zone5   zone6 | zone7        |
    +---------------+--------------+


Then zone1 will stretch right-wards to make a two-zone view. Zone4 will stretch
downwards to make a long two-zone view.

To specify your own layout, put the specification in a ``.json`` file. This should
be a list of zones, and which views should appear in which zones. An example:

**my_layout.json**

.. code-block:: json

   {
       "zone1": ["unitlist", "spikelist"], 
       "zone2": ["spikeamplitude"], 
       "zone3": ["waveform", "waveformheatmap"], 
       "zone4": ["similarity"], 
       "zone5": ["spikedepth"], 
       "zone6": [], 
       "zone7": [], 
       "zone8": ["correlogram"]
   }

When you open spikeinterface-gui, you can then point to the ``my_layout.json``
using the ``--layout_file`` flag:

.. code-block:: bash

   sigui --layout_file=path/to/my_layout.json path/to/sorting_analyzer

Find a list of available views `in this file <https://github.com/SpikeInterface/spikeinterface-gui/blob/main/spikeinterface_gui/viewlist.py>`_.

You can also edit the initial settings for each view. There are two ways to do this.
First, you can open the gui, edit the settings of any or all views, then press the 
"Save as default settings" button in the ``mainsettings`` view. This will save a 
``settings.json`` file in your spikeinterface-gui config (saved in ``~/.config/spikeinterface_gui/``).
The saved settings will automatically load next time you start the gui.

If you want more direct control, you can pass your own setting json file
to the ``settings-file`` flag (or by passing a ``user_settings`` dict to ``run_mainwindow``). 
The settings file should contain a settings dict for each view. The view names are the
same as used in the layout file, and each setting name can be seen in the settings
tab of each view. Below is an example settings file:

**my_settings.json**

.. code-block:: json

    {
        "probe": {
            "show_channel_id": true
        },
        "waveform": {
            "overlap": false, 
            "plot_std": false
        },
        "spikeamplitude": {
            "max_spikes_per_unit": 1000, 
            "alpha": 0.2
        }
    }


You can then use this file by running e.g.

.. code-block:: bash

    sigui --settings_file=path/to/my_settings.json path/to/sorting_analyzer
