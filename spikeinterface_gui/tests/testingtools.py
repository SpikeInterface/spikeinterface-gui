import shutil
from pathlib import Path

from spikeinterface.core.testing_tools import generate_recording, generate_sorting
from spikeinterface import WaveformExtractor, extract_waveforms
from spikeinterface.extractors import toy_example, read_mearec


def clean_all(test_folder):
    folders = [test_folder]
    for folder in folders:
        if Path(folder).exists():
            shutil.rmtree(folder)

def make_one_folder(test_folder):
    clean_all(test_folder)
    
    durations = [60.]
    sampling_frequency = 30000.
    
    #~ recording = generate_recording(num_channels=2, durations=durations, sampling_frequency=sampling_frequency)
    #~ recording.annotate(is_filtered=True)
    #~ recording = recording.save(folder=test_folder/'recording')
    
    #~ sorting = generate_sorting(num_units=5, sampling_frequency=sampling_frequency, durations=durations)
    #~ sorting = sorting.save(folder=test_folder/'sorting')

    #~ recording, sorting = toy_example(duration=120, num_channels=4, num_units=10,
                #~ sampling_frequency=30000.0, num_segments=2,
                #~ average_peak_amplitude=-100, upsample_factor=13, seed=None)
    #~ recording = recording.save(folder=test_folder/'recording')
    #~ sorting = sorting.save(folder=test_folder/'sorting')
    
    
    recording, sorting = read_mearec('/home/samuel/ephy_testing_data/mearec/mearec_test_10s.h5')
    
    
    we = extract_waveforms(recording, sorting, test_folder / 'waveforms', max_spikes_per_unit=500, return_scaled=False)


    
if __name__ == '__main__':
    from pathlib import Path

    test_folder = Path('my_dataset')
    
    clean_all(test_folder)
    make_one_folder(test_folder)
    
    we = WaveformExtractor.load_from_folder(test_folder / 'waveforms')
    print(we)
    