import shutil
from pathlib import Path

import spikeinterface.full as si


def clean_all(test_folder):
    folders = [test_folder]
    for folder in folders:
        if Path(folder).exists():
            shutil.rmtree(folder)

def make_one_folder(test_folder):
    clean_all(test_folder)
    
    recording, sorting = si.generate_ground_truth_recording(
        durations=[300.0, 100.0],
        sampling_frequency=30000.0,
        num_channels=30,
        num_units=15,
        generate_sorting_kwargs=dict(firing_rates=3.0, refractory_period_ms=4.0),
        generate_unit_locations_kwargs=dict(
            margin_um=5.0,
            minimum_z=5.0,
            maximum_z=20.0,
        ),
        generate_templates_kwargs=dict(
            unit_params_range=dict(
                alpha=(9_000.0, 12_000.0),
            )
        ),
        noise_kwargs=dict(noise_level=5.0, strategy="tile_pregenerated"),
        seed=2205,
    )
    
    job_kwargs = dict(n_jobs=-1, progress_bar=True, chunk_duration="1s")
    sorting_result = si.start_sorting_result(sorting, recording, format="binary_folder", folder=test_folder / "sorting_result")
    sorting_result.select_random_spikes()
    sorting_result.compute("waveforms", **job_kwargs)
    sorting_result.compute("templates")
    sorting_result.compute("noise_levels")
    sorting_result.compute("principal_components", n_components=3, mode='by_channel_global', whiten=True, **job_kwargs)
    sorting_result.compute("quality_metrics", metric_names=["snr", "firing_rate"])
    sorting_result.compute("spike_amplitudes", **job_kwargs)


    
if __name__ == '__main__':
    from pathlib import Path

    test_folder = Path('my_dataset')
    
    folder = test_folder / 'sorting_result'
    
    clean_all(test_folder)
    make_one_folder(test_folder)
    
    sorting_result = si.load_sorting_result(folder)
    print(sorting_result)



    nlq = sorting_result.get_extension('noise_levels')
    print(nlq.get_data())
    
    pc = sorting_result.get_extension('principal_components')
    print(pc.get_data())
    
    sac = sorting_result.get_extension('spike_amplitudes')
    print(sac.get_data())

    qmc = sorting_result.get_extension('quality_metrics')
    print(qmc.get_data())
    
