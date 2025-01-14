import shutil
from pathlib import Path

import numpy as np

import spikeinterface.full as si
import probeinterface


def clean_all(test_folder):
    folders = [test_folder]
    for folder in folders:
        if Path(folder).exists():
            shutil.rmtree(folder)

def make_analyzer_folder(test_folder, num_probe=1):
    clean_all(test_folder)
    
    job_kwargs = dict(n_jobs=-1, progress_bar=True, chunk_duration="1s")

    recordings = []
    sortings = []
    probes = []
    for i in range(num_probe):
        recording, sorting = si.generate_ground_truth_recording(
            durations=[300.0, 100.0],
            num_channels=32,
            num_units=16,

            # durations=[3600.0 / 10.],
            # num_channels=380,
            # num_units=250,

            sampling_frequency=30000.0,
            
            generate_sorting_kwargs=dict(firing_rates=3.0, refractory_period_ms=4.0),
            generate_unit_locations_kwargs=dict(
                margin_um=5.0,
                minimum_z=5.0,
                maximum_z=20.0,
            ),
            generate_templates_kwargs=dict(
                unit_params=dict(
                    alpha=(100.0, 500.0),
                )
            ),
            noise_kwargs=dict(noise_levels=10.0, strategy="tile_pregenerated"),
            seed=2205+i,
        )

        if num_probe > 1:
            probe = recording.get_probe()
            probe.move([i*200, 0])
            recording = recording.set_probe(probe)
            
            recordings.append(recording)
            sortings.append(sorting)
            probes.append(probe.copy())
    
    if num_probe > 1:
        #
        recording = si.aggregate_channels(recordings)
        probegroup = probeinterface.ProbeGroup()
        count = 0
        for probe in probes:
            n = probe.get_contact_count()
            probe.device_channel_indices = np.arange(count, count+n)
            probe.set_contact_ids(probe.device_channel_indices.astype('S'))
            print(probe.contact_ids)
            probegroup.add_probe(probe)
            count += n
        recording = recording.set_probegroup(probegroup)

        sorting = si.aggregate_units(sortings)


    
    sorting_analyzer = si.create_sorting_analyzer(sorting, recording,
                                                  format="binary_folder",
                                                  folder=test_folder / "sorting_analyzer",
                                                #   format="zarr",
                                                #   folder=test_folder / "sorting_analyzer.zarr",
                                                  **job_kwargs)
    sorting_analyzer.compute("random_spikes", method="uniform", max_spikes_per_unit=500)
    sorting_analyzer.compute("waveforms", **job_kwargs)
    sorting_analyzer.compute("templates", **job_kwargs)
    sorting_analyzer.compute("noise_levels")
    sorting_analyzer.compute("unit_locations")
    ext = sorting_analyzer.compute("isi_histograms", window_ms=50., bin_ms=1., method="numba")
    sorting_analyzer.compute("correlograms", window_ms=50., bin_ms=1.)
    sorting_analyzer.compute("template_similarity")
    sorting_analyzer.compute("principal_components", n_components=3, mode='by_channel_global', whiten=True, **job_kwargs)
    sorting_analyzer.compute("quality_metrics", metric_names=["snr", "firing_rate"])
    sorting_analyzer.compute("spike_amplitudes", **job_kwargs)


    qm = sorting_analyzer.get_extension("quality_metrics").get_data()
    print(qm.index)
    print(qm.index.dtype)
    print(sorting_analyzer.unit_ids.dtype)
    
if __name__ == '__main__':
    from pathlib import Path

    test_folder = Path('my_dataset')
    
    folder = test_folder / 'sorting_analyzer'
    
    clean_all(test_folder)
    make_analyzer_folder(test_folder, num_probe=2)
    
    sorting_analyzer = si.load_sorting_analyzer(folder)
    print(sorting_analyzer)



    nlq = sorting_analyzer.get_extension('noise_levels')
    # print(nlq.get_data())
    
    pc = sorting_analyzer.get_extension('principal_components')
    # print(pc.get_data())
    
    sac = sorting_analyzer.get_extension('spike_amplitudes')
    # print(sac.get_data())

    qmc = sorting_analyzer.get_extension('quality_metrics')
    # print(qmc.get_data())
    
    qm = sorting_analyzer.get_extension("quality_metrics").get_data()
    print(qm.index)
    print(qm.index.dtype)
    print(sorting_analyzer.unit_ids.dtype)
