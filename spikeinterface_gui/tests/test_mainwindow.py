import PySide6
import spikeinterface_gui as sigui

from spikeinterface.core.testing_tools import generate_recording, generate_sorting
from spikeinterface import WaveformExtractor, extract_waveforms

import shutil
from pathlib import Path

test_folder = Path('my_dataset')


def _clean_all():
    folders = [test_folder]
    for folder in folders:
        if Path(folder).exists():
            shutil.rmtree(folder)
    
def setup_module():
    _clean_all()
    
    durations = [60.]
    sampling_frequency = 30000.
    
    recording = generate_recording(num_channels=2, durations=durations, sampling_frequency=sampling_frequency)
    recording.annotate(is_filtered=True)
    recording = recording.save(folder=test_folder/'recording')
    
    sorting = generate_sorting(num_units=5, sampling_frequency=sampling_frequency, durations=durations)
    sorting = sorting.save(folder=test_folder/'sorting')
    
    we = extract_waveforms(recording, sorting, test_folder / 'waveforms', max_spikes_per_unit=500, return_scaled=False)



def teardown_module():
    _clean_all()

def test_mainwindow(interactive=False):
    app = sigui.mkQApp()
    
    we = WaveformExtractor.load_from_folder(test_folder / 'waveforms')
    
    win = sigui.MainWindow(we)
    
    if interactive:
        win.show()
        app.exec_()
    else:
        # close thread properly
        win.close()

    
if __name__ == '__main__':
    
    #~ setup_module()
    
    
    test_mainwindow(interactive=True)
    
    