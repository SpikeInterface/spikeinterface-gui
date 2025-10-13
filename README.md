# spikeinterface-gui

GUI for the `SortingAnalyser` object from spikeinterface .

This is a cross platform interactive viewer to inspect the final results
and quality of any spike sorter supported by spikeinterface 
(kilosort, spykingcircus, tridesclous, mountainssort, yass, ironclust, herdingspikes, hdsort, klusta...)

This interactive GUI offer several views that dynamically refresh other views.
This allows us to very quickly check the strengths and weaknesses of any sorter output.

This can be used as a replacement of [phy](https://github.com/cortex-lab/phy).

This viewer has 2 modes:
  * **mode=desktop** : this a local desktop app using internaly Qt, fast and easy when the data is local
  * **mode=web** : this is a web app internally using Panel, usefull when the data is remote


![screenshot](screenshot.png)


## main usage

The main idea is make visible one or several unit and visualy inspect if they should be merge or remove.
For this visibility:
  * ctlr + double click on a unit in *probeview*
  * check the box visible in the *unitlist* 
  * double click on one unit in *unitlist* unit visible alone
  * move one of the roi in the *probeview*

Views can be reorganized by moving docks by clicking in the title bar of a docks.
Any dock (view) can be closed. And can be put back with right click in any title bar of any dock.

Every view has a **?** button which open the contextual help. **Theses inplace docs are the most important stuff to be read**. (but the contains typos)

When some units are visible, the related spike list can be refresh.
Then selecting spike per spike can also refersh some views.
This enable a very quick and convinient spike per spike jump on traces.

Channel visibility can be handled with one of the roi in the probeview.

Shortcuts: many shortcuts are available, please read the **?** button in each view.

## curation mode

By default this tools is a viewer only. But you can turn it into a tools for manual curation using,
the `curation=True` option.
This tools supoort the [curation format from spikeinterface](https://spikeinterface.readthedocs.io/en/latest/modules/curation.html#manual-curation).
This format enbale to:
  1. remove units
  2. merge units
  3. create manual labels

When this mode is activated a new view is added on top left to maintain the list of removal and merges.
The curation format can be exported to json.



## Launch

In order to use this viewer you will need to know a bit of [spikeinterface](https://spikeinterface.readthedocs.io/)

### Step 1 : create and compute SortingAnalyzer

You first need to is to get a `SortingAnalyzer` object with spikeinterface.

See help [here](https://spikeinterface.readthedocs.io)

Note that:
  * some extensions are mandatory (unit_location, templates, )
  * some extension are optional
  * the more extensions are computed the more view are displayed


Example:

```python
import spikeinterface.full as si
recording = si.read_XXXX('/path/to/my/recording')
recording_filtered = si.bandpass_filter(recording)
sorting = si.run_sorter('YYYYY', recording_filtered)


job_kwargs = dict(n_jobs=-1, progress_bar=True, chunk_duration="1s")

# make the SortingAnalyzer with necessary and some optional extensions
sorting_analyzer = si.create_sorting_analyzer(sorting, recording_filtered,
                                              format="binary_folder", folder="/my_sorting_analyzer",
                                              **job_kwargs)
sorting_analyzer.compute("random_spikes", method="uniform", max_spikes_per_unit=500)
sorting_analyzer.compute("waveforms", **job_kwargs)
sorting_analyzer.compute("templates", **job_kwargs)
sorting_analyzer.compute("noise_levels")
sorting_analyzer.compute("unit_locations", method="monopolar_triangulation")
sorting_analyzer.compute("isi_histograms")
sorting_analyzer.compute("correlograms", window_ms=100, bin_ms=5.)
sorting_analyzer.compute("principal_components", n_components=3, mode='by_channel_global', whiten=True, **job_kwargs)
sorting_analyzer.compute("quality_metrics", metric_names=["snr", "firing_rate"])
sorting_analyzer.compute("template_similarity")
sorting_analyzer.compute("spike_amplitudes", **job_kwargs)

```


### Step 2 : open the GUI

With python:

```python
from spikeinterface_gui import run_mainwindow
# reload the SortingAnalyzer
sorting_analyzer = si.load_sorting_analyzer("/my_sorting_analyzer")
# open and run the Qt app
run_mainwindow(sorting_analyzer, mode="desktop")
# open and run the Web app
run_mainwindow(sorting_analyzer, mode="web")
```

Or from spikeinterface:

```python
  import spikeinterface.widgets as sw
  sorting_analyzer = load_sorting_analyzer(test_folder / "sorting_analyzer")
  sw.plot_sorting_summary(sorting_analyzer, backend="spikeinterface_gui")
```


With the command line

```bash
sigui /path/for/my/sorting_analyzer
```


The command line support some otions like *--notraces* or *--curation* or *--mode*
```bash
sigui --mode=web --no-traces --curation /path/for/my/sorting_analyzer
```



## With curation mode


To open the viewer with curation mode use `curation=True`.

This mode is pretty new and was implemented under kind inducement of friends.
I hope that this could be a fair replacement of `phy`.


```python
from spikeinterface_gui import run_mainwindow
run_mainwindow(sorting_analyzer, curation=True)
```


```python
  from spikeinterface.widgets import plot_sorting_summary
  sw.plot_sorting_summary(sorting_analyzer, curation=True, backend="spikeinterface_gui")
```

The `curation_dict` can be saved inside the folder of the analyzer (for "binary_folder" or "zarr" format).
Then it is auto-reloaded when the gui is re-opened.



## Install

For beginners or Anaconda users please see our [installation tips](https://github.com/SpikeInterface/spikeinterface/tree/main/installation_tips)
where we provide a yaml for Mac/Windows/Linux to help properly install `spikeinterface` and `spikeinterface-gui` for you in a dedicated
conda environment.

In your environment, if you wish to use the Desktop version of the GUI, you can do:

```bash
pip install 'spikeinterface-gui[desktop]'
```

Note: this installs `PySide6`. You can use the `PyQt5` backend instead by uninstalling `PySide6` and then installing `PyQt5`.

If you wish to use the Web version of the GUI, you can do:

```bash
pip install 'spikeinterface-gui[web]'
```

From source:

```bash
git clone https://github.com/SpikeInterface/spikeinterface-gui.git
cd spikeinterface-gui
pip install .
```

You'll then need to install the appropriate backends yourself (`pyqtgraph` and `PySide6` or `PyQt5` for the desktop; `panel` and `bokeh` for web).

## Custom layout

You can create your own custom layout by specifying which views you'd like
to see, and where they go. The basic window layout supports eight "zones",
which are laid out as follows:

```
+---------------+--------------+
| zone1   zone2 | zone3  zone4 |
+               +              +
| zone5   zone6 | zone7  zone8 |
+---------------+--------------+
```

If a zone has free space below it or to the right of it, it will try to use it.
Stretching downwards takes precedence over stretching rightwards.
E.g. suppose your layout is only non-empty in zones 1, 4, 5, 6 and 7:

```
+---------------+--------------+
| zone1         |        zone4 |
+               +              +
| zone5   zone6 | zone7        |
+---------------+--------------+
```

Then zone1 will stretch right-wards to make a three-zone view. Zone4 will stretch
downwards to make a long two-zone view.

To specify your own layout, put the specification in a `.json` file. This should
be a list of zones, and which views should appear in which zones. An example:

**my_layout.json**
```
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
```

When you open spikeinterface-gui, you can then point to the `my_layout.json`
using the `--layout_file` flag:

```
sigui --layout_file=path/to/my_layout.json path/to/sorting_analyzer
```

Find a list of available views [in this file](https://github.com/SpikeInterface/spikeinterface-gui/blob/main/spikeinterface_gui/viewlist.py).



## Credits

Original author : Samuel Garcia, CNRS, Lyon, France

This work is a port of the old `tridesclous.gui` submodule on top of
[spikeinterface](https://github.com/SpikeInterface/spikeinterface).

Main authors and maintainers:

 * qt side : Samuel Garcia, CNRS, Lyon, France
 * web side : Alessio Paolo Buccino, Allen Institute for Neural Dynamics, Seattle, USA did


## Message from dictator

Contrary, to the spikeinterface package, for the developement of this viewer 
all good practices of coding are deliberately put aside  : no test, no CI, no auto formating, no doc, ... 
Feel free to contribute, it is an open wild zone. Code anarchist are very welcome.
So in this mess, persona non grata : pre-commit, black, pytest fixture, ...
