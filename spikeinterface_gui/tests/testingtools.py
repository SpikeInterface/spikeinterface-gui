import shutil
from pathlib import Path

from spikeinterface.core.testing_tools import generate_recording, generate_sorting
from spikeinterface import WaveformExtractor, extract_waveforms



def clean_all():
    folders = [test_folder]
    for folder in folders:
        if Path(folder).exists():
            shutil.rmtree(folder)

def make_one_folder():
    clean_all()
    
    durations = [60.]
    sampling_frequency = 30000.
    
    recording = generate_recording(num_channels=2, durations=durations, sampling_frequency=sampling_frequency)
    recording.annotate(is_filtered=True)
    recording = recording.save(folder=test_folder/'recording')
    
    sorting = generate_sorting(num_units=5, sampling_frequency=sampling_frequency, durations=durations)
    sorting = sorting.save(folder=test_folder/'sorting')
    
    we = extract_waveforms(recording, sorting, test_folder / 'waveforms', max_spikes_per_unit=500, return_scaled=False)
