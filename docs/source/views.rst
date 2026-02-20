Views
=====

This page documents all available views in the SpikeInterface GUI, showing their functionality and appearance across different backends (desktop Qt and web panel).

Probe View
----------
Show contact and probe shape.
Units are color coded.

Controls
~~~~~~~~
- **left click** : select single unit
- **ctrl + left click** : add unit to selection
- **mouse drag from within circle** : change channel visibilty and unit visibility on other views
- **mouse drag from "diamond"** : change channel / unit radii size

Screenshots
~~~~~~~~~~~

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Desktop (Qt)
     - Web (Panel)
   * - .. image:: images/views/desktop/probe.png
          :width: 100%
     - .. image:: images/views/web/probe.png
          :width: 100%

Main settings
-------------

Overview and main controls.
Can save current settings for entire GUI as the default user settings using the "Save as default settings" button.

Screenshots
~~~~~~~~~~~

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Desktop (Qt)
     - Web (Panel)
   * - .. image:: images/views/desktop/mainsettings.png
          :width: 100%
     - .. image:: images/views/web/mainsettings.png
          :width: 100%

Unit List
---------

This view controls the visibility of units.

Controls
~~~~~~~~
* **check box** : make visible or unvisible
* **double click** : make it visible alone
* **space** : make selected units visible
* **arrow up/down** : select next/previous unit
* **ctrl + arrow up/down** : select next/previous unit and make it visible alone
* **press 'ctrl+d'** : delete selected units (if curation=True)
* **press 'ctrl+m'** : merge selected units (if curation=True)
* **press 'g'** : label selected units as good (if curation=True)
* **press 'm'** : label selected units as mua (if curation=True)
* **press 'n'** : label selected units as noise (if curation=True)
* **drag column headers** : reorder columns (Qt-only)
* **click on column header** : sort by this column (Qt-only)
* **"↻"** : reset the unit table

Screenshots
~~~~~~~~~~~

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Desktop (Qt)
     - Web (Panel)
   * - .. image:: images/views/desktop/unitlist.png
          :width: 100%
     - .. image:: images/views/web/unitlist.png
          :width: 100%

SpikeRateView View
==================

This view shows firing rate for spikes per `bin_s`.

Screenshots
~~~~~~~~~~~

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Desktop (Qt)
     - Web (Panel)
   * - .. image:: images/views/desktop/spikerate.png
          :width: 100%
     - .. image:: images/views/web/spikerate.png
          :width: 100%

Merge View
----------

This view allows you to compute potential merges between units based on their similarity or using the auto merge function.
Select the preset to use for merging units.
The available presets are inherited from spikeinterface.

Click "Calculate merges" to compute the potential merges. When finished, the table will be populated
with the potential merges.

Controls
~~~~~~~~
- **left click** : select a potential merge group
- **arrow up/down** : navigate through the potential merge groups
- **ctrl + a** : accept the selected merge group

Screenshots
~~~~~~~~~~~

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Desktop (Qt)
     - Web (Panel)
   * - .. image:: images/views/desktop/merge.png
          :width: 100%
     - .. image:: images/views/web/merge.png
          :width: 100%

Trace View
----------

This view shows the traces of the selected visible channels from the Probe View.

Controls
~~~~~~~~
* **x size (s)**: Set the time window size for the traces.
* **auto scale**: Automatically adjust the scale of the traces.
* **time (s)**: Set the time point to display traces.
* **mouse wheel**: change the scale of the traces.
* **double click**: select the nearest spike and center the view on it.

Screenshots
~~~~~~~~~~~

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Desktop (Qt)
     - Web (Panel)
   * - .. image:: images/views/desktop/trace.png
          :width: 100%
     - .. image:: images/views/web/trace.png
          :width: 100%

Trace Map View
--------------

This view shows the trace map of all the channels.

Controls
~~~~~~~~
* **x size (s)**: Set the time window size for the traces.
* **auto scale**: Automatically adjust the scale of the traces.
* **time (s)**: Set the time point to display traces.
* **mouse wheel**: change the scale of the traces.
* **double click**: select the nearest spike and center the view on it.

Screenshots
~~~~~~~~~~~

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Desktop (Qt)
     - Web (Panel)
   * - .. image:: images/views/desktop/tracemap.png
          :width: 100%
     - .. image:: images/views/web/tracemap.png
          :width: 100%

Waveform View
-------------

Display average template for visible units.
If one spike is selected (in spike list) then the spike is super-imposed (white trace)
(when the 'plot_selected_spike' setting is True)

There are 2 modes of display:
- 'geometry' : snippets are displayed centered on the contact position
- 'flatten' : snippets are concatenated in a flatten way (better to check the variance)

Controls
~~~~~~~~
* **mode** : change displaye mode (geometry or flatten)
* **ctrl + o** : toggle overlap mode
* **ctrl + p** : toggle plot waveform samples
* **mouse wheel** : scale waveform amplitudes
* **alt + mouse wheel** : widen/narrow x axis
* **shift + mouse wheel** : zoom
* **shift + alt + mouse wheel** : scale vertical spacing between channels

Screenshots
~~~~~~~~~~~

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Desktop (Qt)
     - Web (Panel)
   * - .. image:: images/views/desktop/waveform.png
          :width: 100%
     - .. image:: images/views/web/waveform.png
          :width: 100%

Waveform Heatmap View
---------------------

Check density around the average template for each unit, which is useful to check overlap between units.
For efficiency, no more than 4 units visible at same time.
This can be changed in the settings.

Controls
~~~~~~~~
* **mouse wheel** : color range for density (important!!)
* **right click** : X/Y zoom
* **left click** : move

Screenshots
~~~~~~~~~~~

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Desktop (Qt)
     - Web (Panel)
   * - .. image:: images/views/desktop/waveformheatmap.png
          :width: 100%
     - .. image:: images/views/web/waveformheatmap.png
          :width: 100%

ISI View
--------

This view shows the inter spike interval histograms for each unit.

Screenshots
~~~~~~~~~~~

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Desktop (Qt)
     - Web (Panel)
   * - .. image:: images/views/desktop/isi.png
          :width: 100%
     - .. image:: images/views/web/isi.png
          :width: 100%

Correlograms View
-----------------

This view shows the auto-correlograms and cross-correlograms of the selected units.

Screenshots
~~~~~~~~~~~

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Desktop (Qt)
     - Web (Panel)
   * - .. image:: images/views/desktop/correlogram.png
          :width: 100%
     - .. image:: images/views/web/correlogram.png
          :width: 100%

N-dimensional Scatter View
--------------------------

This view projects n-dimensional principal components (num channels x num components) of the selected units
in a 2D sub-space.

Controls
~~~~~~~~
- **next face** : rotates the projection
- **random** : randomly choose a projection
- **random tour** : runs dynamic "tour" of the pcs

Screenshots
~~~~~~~~~~~

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Desktop (Qt)
     - Web (Panel)
   * - .. image:: images/views/desktop/ndscatter.png
          :width: 100%
     - .. image:: images/views/web/ndscatter.png
          :width: 100%

Similarity View
---------------

This view displays the template similarity matrix between units.

Controls
~~~~~~~~
- **left click** : select a pair of units to show in the unit view.

Screenshots
~~~~~~~~~~~

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Desktop (Qt)
     - Web (Panel)
   * - .. image:: images/views/desktop/similarity.png
          :width: 100%
     - .. image:: images/views/web/similarity.png
          :width: 100%

Spike Amplitude View
--------------------

Check amplitudes of spikes across the recording time or in a histogram
comparing the distribution of ampltidues to the noise levels.

Controls
~~~~~~~~
- **select** : activate lasso selection to select individual spikes
- **split** or **ctrl+s** : split the selected spikes into a new unit (only if one unit is visible)

Screenshots
~~~~~~~~~~~

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Desktop (Qt)
     - Web (Panel)
   * - .. image:: images/views/desktop/spikeamplitude.png
          :width: 100%
     - .. image:: images/views/web/spikeamplitude.png
          :width: 100%

Spike Depth View
----------------

Check deppth of spikes across the recording time or in a histogram.

Controls
~~~~~~~~
- **select** : activate lasso selection to select individual spikes
- **split** or **ctrl+s** : split the selected spikes into a new unit (only if one unit is visible)

Screenshots
~~~~~~~~~~~

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Desktop (Qt)
     - Web (Panel)
   * - .. image:: images/views/desktop/spikedepth.png
          :width: 100%
     - .. image:: images/views/web/spikedepth.png
          :width: 100%

Curation View
-------------

The curation view shows the current status of the curation process and allows the user to manually visualize,
revert, and export the curation data.

Controls
~~~~~~~~
- **save in analyzer**: Save the current curation state in the analyzer.
- **export/download JSON**: Export the current curation state to a JSON file.
- **restore**: Restore the selected unit from the deleted units table.
- **unmerge**: Unmerge the selected merges from the merged units table.
- **submit to parent**: Submit the current curation state to the parent window (for use in web applications).
- **press 'ctrl+r'**: Restore the selected units from the deleted units table.
- **press 'ctrl+u'**: Unmerge the selected merges from the merged units table.
- **press 'ctrl+x'**: Unsplit the selected split groups from the split units table.

Screenshots
~~~~~~~~~~~

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Desktop (Qt)
     - Web (Panel)
   * - .. image:: images/views/desktop/curation.png
          :width: 100%
     - .. image:: images/views/web/curation.png
          :width: 100%

Metrics View
------------

View and explore unit metrics in a customizable grid of plots.

Screenshots
~~~~~~~~~~~

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Desktop (Qt)
     - Web (Panel)
   * - .. image:: images/views/desktop/metrics.png
          :width: 100%
     - .. image:: images/views/web/metrics.png
          :width: 100%

Spike list View
---------------

Show all spikes of the visible units. When spikes are selected, they are highlighted in the Spike Amplitude View and the ND SCatter View.
When a single spike is selected, the Trace and TraceMap Views are centered on it.

Controls
~~~~~~~~
* **↻ spikes**: refresh the spike list
* **clear**: clear the selected spikes
* **shift + arrow up/down** : select next/previous spike and make it visible alone

Screenshots
~~~~~~~~~~~

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Desktop (Qt)
     - Web (Panel)
   * - .. image:: images/views/desktop/spikelist.png
          :width: 100%
     - .. image:: images/views/web/spikelist.png
          :width: 100%

Amplitude Scalings View
-----------------------

Amplitude scalings measure the optimal scaling which should be applied to the template so that
it best matches each spike waveform.

Controls
~~~~~~~~
- **select** : activate lasso selection to select individual spikes
- **split** or **ctrl+s** : split the selected spikes into a new unit (only if one unit is visible)

*Screenshots not available for this view.*

Main Template View
------------------

Display average template on main channel.
If the `template_metrics` are computed, it also displayed the template signal
used to compute metrics (usually upsampled) and the trough/peak_before/peak_after
positions and widths.

- troughs are negative extrema and are displayed with a downward triangle symbol
- peaks are positive extrema and are displayed with an upward triangle symbol

Screenshots
~~~~~~~~~~~

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Desktop (Qt)
     - Web (Panel)
   * - .. image:: images/views/desktop/maintemplate.png
          :width: 100%
     - .. image:: images/views/web/maintemplate.png
          :width: 100%

