import shutil
from pathlib import Path

from spikeinterface.core.testing_tools import generate_recording, generate_sorting
from spikeinterface import WaveformExtractor, extract_waveforms
from spikeinterface.extractors import toy_example, read_mearec
from spikeinterface.toolkit import compute_principal_components, compute_spike_amplitudes, compute_quality_metrics


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
    #~ recording, sorting = read_mearec('/home/samuel.garcia/ephy_testing_data/mearec/mearec_test_10s.h5')
    
    
    we = extract_waveforms(recording, sorting, test_folder / 'waveforms', max_spikes_per_unit=25, return_scaled=False)
    
    pc = compute_principal_components(we, n_components=5, mode='by_channel_local', whiten=True, dtype='float32')
    metrics = compute_quality_metrics(we, load_if_exists=False,  metric_names=None)
    amplitudes = compute_spike_amplitudes(we,load_if_exists=False)
    


    
if __name__ == '__main__':
    from pathlib import Path

    test_folder = Path('my_dataset')
    
    folder = test_folder / 'waveforms'
    
    clean_all(test_folder)
    make_one_folder(test_folder)
    
    we = WaveformExtractor.load_from_folder(folder)
    print(we)
    
    pc = we.load_extension('principal_components')
    print(pc)
    
    sac = we.load_extension('spike_amplitudes')
    print(sac._amplitudes)

    qmc = we.load_extension('quality_metrics')
    print(qmc._metrics)
    
