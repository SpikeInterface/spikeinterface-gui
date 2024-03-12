# spikeinterface-gui

GUI for spikeinterface objects without data copy.

This is a cross platform interactive viewer to inspect the final results
and quality of any spike sorter supported by spikeinterface 
(kilosort, spykingcircus, tridesclous, mountainssort, yass, ironclust, herdingspikes, hdsort, klusta...)

This interactive GUI offer several views that dynamically refresh other views.
This allows us to very quickly check the strengths and weaknesses of any sorter output.

Contrary to other viewers (like phy), this viewer skips the tedious and long step of
copying and reformatting the entire dataset (filtered signal + waveform + PCA) to a particular
format or folder organisation. This gui is built on top of spikeinterface objects
(Recording, Sorting, SortingAnalyzer)
These objects are "lazy" and retrieve data on the fly (no copy!).
And contrary to phy, this is a view only tool : no manual curation at the moment (split/merge/trash have to be done outside).

This viewer internally use Qt (with PySide6, PyQT6 or PyQt5) and pyqtgraph.
And so, this viewer is a local desktop app (old school!!).
There is a web based viewer [here](https://github.com/magland/sortingview).

![screenshot](screenshot.png)

## Important note

The actual `main` branch is using the new `SortingAnalyzer` object from spikeinterface which is not released yet.
You can expect some small bugs.
If you want visualize the old `WaveformExtractor` from spikeinterface<=0.100.1 you need to go back to version spikeinterface-gui=0.8.0.

## Launch

In order to use this viewer you will need to know a bit of [spikeinterface](https://spikeinterface.readthedocs.io/)

### Step 1 : extract waveforms

You first need to is to get a `SortingAnalyzer` object with spikeinterface.

See help [here](https://spikeinterface.readthedocs.io)

Note that:
  * not all waveform snippets are extracted (See `max_spikes_per_unit`) only some of them
  * this step is cached to a folder or zarr (and can be reloaded)
  * this step can be run in parallel (and so is quite fast)
  * optionally some extensionn can be computed (principal_components, spike_amplitudes, correlograms, ..)
    All extension will be rendered in an appropriated view.

  
Example:

```python
import spikeinterface.full as si
recording = si.read_XXXX('/path/to/my/recording')
recording_filtered = si.bandpass_filter(recording)
sorting = si.run_sorter('YYYYY', recording_filtered)


job_kwargs = dict(n_jobs=-1, progress_bar=True, chunk_duration="1s")

# make the SortingAnalyzer with some optional extensions
sorting_analyzer = si.create_sorting_analyzer(sorting, recording,
                                              format="binary_folder", folder="/my_sorting_analyzer",
                                              **job_kwargs)
sorting_analyzer.compute("random_spikes", method="uniform", max_spikes_per_unit=500)
sorting_analyzer.compute("waveforms", **job_kwargs)
sorting_analyzer.compute("templates")
sorting_analyzer.compute("noise_levels")
sorting_analyzer.compute("unit_locations", method="monopolar_triangulation")
sorting_analyzer.compute("isi_histograms")
sorting_analyzer.compute("correlograms", window_ms=100, bin_ms=5.)
sorting_analyzer.compute("principal_components", n_components=3, mode='by_channel_global', whiten=True, **job_kwargs)
sorting_analyzer.compute("quality_metrics", metric_names=["snr", "firing_rate"])
sorting_analyzer.compute("spike_amplitudes", **job_kwargs)

```

### Step 2 : open the GUI

With python:

```python
import spikeinterface_gui
# This creates a Qt app
app = spikeinterface_gui.mkQApp() 
# reload the SortingAnalyzer
sorting_analyzer = si.load_sorting_analyzer("/my_sorting_analyzer")
# create the mainwindow and show
win = spikeinterface_gui.MainWindow(sorting_analyzer)
win.show()
# run the main Qt6 loop
app.exec_()
```

Or simpler:

```python
  import spikeinterface.widgets as sw
  sorting_analyzer = load_sorting_analyzer(test_folder / "sorting_analyzer")
  sw.plot_sorting_summary(sorting_analyzer, backend="spikeinterface_gui")
```


With the command line

```bash
sigui /path/for/my/sorting_analyzer
```


## Install

For beginners or Anaconda users please see our [installation tips](https://github.com/SpikeInterface/spikeinterface/tree/main/installation_tips)
where we provide a yaml for Mac/Windows/Linux to help properly install `spikeinterface` and `spikeinterface-gui` for you in a dedicated
conda environment.

Otherwise, 

You need first to install **one** of these 3 packages (by order of preference):
  * `pip install PySide6` or
  * `pip install PyQt6` or
  * `pip install PyQt5`

From pypi:

```bash
pip install spikeinterface-gui
```

From source:

```bash
git clone https://github.com/SpikeInterface/spikeinterface-gui.git
cd spikeinterface-gui
pip install .
```

## Author

Samuel Garcia, CNRS, Lyon, France

This work is a port of the old `tridesclous.gui` submodule on top of
[spikeinterface](https://github.com/SpikeInterface/spikeinterface).
