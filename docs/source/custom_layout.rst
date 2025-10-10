Customizing the layout
======================

You can create your own custom layout by specifying which views you'd like
to see, and where they go. The basic window layout supports eight "zones",
which are laid out as follows:


+---------------+--------------+
| zone1   zone2 | zone3  zone4 |
+               +              +
| zone5   zone6 | zone7  zone8 |
+---------------+--------------+

If a zone has free space below it or to the right of it, it will try to use it.
Stretching downwards takes precedence over stretching rightwards.
E.g. suppose your layout is only non-empty in zones 1, 4, 5, 6 and 7:

+-------------+----------+
| zone1   --  | -- zone4 |
+-------------+----------+
| zone5 zone6 | zone7 -- |
+-------------+----------+

Then zone1 will stretch right-wards to make a three-zone view. Zone4 will stretch
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
