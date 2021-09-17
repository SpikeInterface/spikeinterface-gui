# spikeinterface-gui

GUI for spikeinterface objects withoput copy.

This is a corss platform, cross spike sorter viewer to inspect the final results
and quality of a sorting.

Contrary to other viewer(like  phy), this viewer skip the tedious and long step of
copying and reformating the entire dataset (filetred signal, waveform, PCA) to a particular
format. This view is built on top of spike interface object (Recording, Sorting, WaveformExtractor)
Theses objects are "lazy" and retrieve data on the fly.

This viewer internally use pyqtgraph.

## Launch

### Step 1 : extract waveforms

You first need to "extract waveform" with spikeinterface
See help [here](https://spikeinterface.readthedocs.io/en/latest/modules/core/plot_4_waveform_extractor.html#sphx-glr-modules-core-plot-4-waveform-extractor-py)

Note that:
  * not all waveform are extracted here (See max_spikes_per_unit)
  * this step is cached to a folder (and reloaded)
  * can be run in parralel

Example:

```python
from spikeinetrface.full as si
recording = si.read_XXXX('/path/to/my/recording')
recording_filtered = si.bandpass_filter(recording)
sorting = si.run_sorter('YYYYY', recording_filtered)
waveform_forlder = '/path/for/my/waveforms'
we = si.extract_waveforms(
    recording_filtered, sorting, waveform_folder,
    max_spikes_per_unit=500,
    ms_before=3., ms_after=4.,
    n_jobs=10, total_memory='500M',
    progress_bar=True,
)
```

### Step 2 : open the GUI

With python:

```python
import spikeinterface_gui
# This cerate a Qt app
app = spikeinterface_gui.mkQApp() 
# reload the waveform folder
we = WaveformExtractor.load_from_folder(waveform_forlder)
# create the mainwindow and show
win = spikeinterface_gui.MainWindow(we)
win.show()
# run the main Qt6 loop
app.exec_()
```

With the commend line

```
sigui /path/for/my/waveforms
```


## Install

You need first to install one this 3 packages (by order of preference):
  * `pip install PySide6`
  * `pip install PyQt6`
  * `pip install PyQt5`


From pypi:

```bash
pip install spikeinterface-gui
```

From sources:

```bash
git clone https://github.com/SpikeInterface/spikeinterface-gui.git
cd spikeinterface-gui
pip install .
```

## Author

Samuel Garcia, CNRS, Lyon, France

This work is a port of the old `tridesclous.gui` submodule o top of spikeinterface.
