import gc
import shutil
import time
from pathlib import Path

import numpy as np

import spikeinterface.full as si
import probeinterface


DATASETS_FOLDER = Path(__file__).parent / "datasets"

_job_kwargs = dict(n_jobs=-1, progress_bar=True, chunk_duration="1s")


def clean_all(test_folder):
    folder = Path(test_folder)
    if not folder.exists():
        return
    # Release lingering memmap handles (e.g. the binary_folder waveforms  extension)
    # before deleting. On NFS, unlinking a still-open file creates a ".nfs*" file, which
    # makes shutil.rmtree raise an error when it tries to rmdir the parent too quickly.
    for attempt in range(5):
        gc.collect() # force release of memmap handles
        try:
            shutil.rmtree(folder)
            return
        except OSError:
            if attempt < 4:
                # retry after a short delay, to give the OS time to release the file handles
                time.sleep(0.5)
    # don't let a failure here cause an otherwise-passing test to fail
    shutil.rmtree(folder, ignore_errors=True)


def get_dataset_folder(case="small", comparison=False, regenerate=False):
    """
    Folder of a test dataset in tests/datasets, generated if it does not exist yet.

    The main datasets contain "sorting_analyzer", the comparison ones
    "sorting_analyzer_1" and "sorting_analyzer_2".
    """
    if comparison:
        folder = DATASETS_FOLDER / f"comparison_{case}"
        # the last folder written: a folder without it is an interrupted build
        complete = (folder / "sorting_analyzer_2").is_dir()
    else:
        folder = DATASETS_FOLDER / case
        complete = (folder / "sorting_analyzer").is_dir()

    if regenerate or not complete:
        if comparison:
            make_comparison_analyzer_folders(folder, case=case, unit_dtype="int")
        else:
            make_analyzer_folder(folder, case=case, unit_dtype="str")
    return folder


def _generate_gt(durations, num_channels, num_units, seed):
    recording, sorting = si.generate_ground_truth_recording(
        durations=durations,
        num_channels=num_channels,
        num_units=num_units,
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
        seed=seed,
    )
    # The NumpySorting injected in the recording is flagged as not picklable, so the analyzer
    # would not save the recording and the trace views would be lost on reload. It pickles
    # fine and its spike vector is small.
    # shortcut: private flag, drop it if spikeinterface makes NumpySorting picklable again
    recording._kwargs["sorting"]._serializability["pickle"] = True
    return recording, sorting


def _create_analyzer(sorting, recording, folder, extensions):
    """extensions: list of (name or list of names, params), computed in order"""
    sorting_analyzer = si.create_sorting_analyzer(sorting, recording, format="binary_folder",
                                                  folder=folder, **_job_kwargs)
    for names, params in extensions:
        sorting_analyzer.compute(names, **params)
    return sorting_analyzer


def make_analyzer_folder(test_folder, case="small", unit_dtype="str"):
    test_folder = Path(test_folder)
    clean_all(test_folder)

    if case ==  'small':
        num_probe = 1
        durations = [300.0, 100.0]
        num_channels = 32
        num_units = 16
    elif case ==  'medium-split':
        num_probe = 1
        durations = [600.0,]
        num_channels = 128
        num_units = 100
    elif case == 'big':
        num_probe = 1
        durations = [3600.0]
        num_channels = 380
        num_units = 400
    elif case == 'multiprobe':
        num_probe = 2
        durations = [300.0,]
        num_channels = 32
        num_units = 16
    else:
        raise ValueError(f"Wrong dataset type {case}")

    recordings = []
    sortings = []
    probes = []
    for i in range(num_probe):
        recording, sorting = _generate_gt(durations, num_channels, num_units, seed=2205 + i)

        if num_probe > 1:
            probe = recording.get_probe()
            probe.move([i*200, 0])
            recording = recording.set_probe(probe)

            recordings.append(recording)
            sortings.append(sorting)
            probes.append(probe.copy())

        if 'split' in case:
            # create an intermediate analyzer to make a simulated split
            analyzer_pre_split = si.create_sorting_analyzer(sorting, recording)
            analyzer_pre_split.compute(["random_spikes", "templates", "spike_amplitudes"])

            sorting, split_units = si.split_sorting_by_amplitudes(
                analyzer_pre_split,
                min_snr=10,
                splitting_probability=0.2
            )

        sorting.set_property(key='my_own_property', values=np.array([f"yep{i}" for i in range(sorting.unit_ids.size)]))

    if num_probe > 1:
        recording = si.aggregate_channels(recordings)
        probegroup = probeinterface.ProbeGroup()
        count = 0
        for probe in probes:
            n = probe.get_contact_count()
            probe.device_channel_indices = np.arange(count, count+n)
            probe.set_contact_ids(probe.device_channel_indices.astype('S'))
            probegroup.add_probe(probe)
            count += n
        recording = recording.set_probegroup(probegroup)

        sorting = si.aggregate_units(sortings)

    sorting = sorting.rename_units(sorting.unit_ids.astype(unit_dtype))

    _create_analyzer(sorting, recording, test_folder / "sorting_analyzer", [
        ("random_spikes", dict(method="uniform", max_spikes_per_unit=500)),
        ("waveforms", _job_kwargs),
        ("templates", _job_kwargs),
        ("noise_levels", _job_kwargs),
        ("unit_locations", {}),
        ("isi_histograms", dict(window_ms=50., bin_ms=1., method="numba")),
        ("correlograms", dict(window_ms=50., bin_ms=1.)),
        ("template_similarity", dict(method="l1")),
        ("principal_components", dict(n_components=3, mode='by_channel_global', whiten=True, **_job_kwargs)),
        (["spike_amplitudes", "spike_locations"], _job_kwargs),
        ("quality_metrics", dict(metric_names=["snr", "firing_rate"])),
        ("template_metrics", {}),
    ])


def make_comparison_analyzer_folders(test_folder, case="small", unit_dtype="str",
                                     fraction_shared=0.7, fraction_dropped_spikes=0.1):
    """
    Two analyzer folders to compare, in test_folder / "sorting_analyzer_1" and "_2".

    One ground truth sorting is split in three: `fraction_shared` of the units go to both
    sortings, and half of the rest goes to each one only. So the comparison has units in
    the three regions of the Venn diagram.

    To add some variability, `fraction_dropped_spikes` of the spikes of the second sorting
    are then dropped at random. The shared units therefore agree strongly but not
    perfectly, which is closer to a real comparison than an agreement of exactly 1.
    """
    test_folder = Path(test_folder)
    clean_all(test_folder)

    if case == 'small':
        durations = [300.0, 100.0]
        num_channels = 32
        num_units = 30
    elif case == 'medium':
        durations = [600.0,]
        num_channels = 128
        num_units = 100
    else:
        raise ValueError(f"Wrong dataset type {case}")

    recording, sorting = _generate_gt(durations, num_channels, num_units, seed=2205)

    rng = np.random.default_rng(seed=2205)

    # split the units: shared / only in sorting1 / only in sorting2
    shuffled_unit_ids = sorting.unit_ids.copy()
    rng.shuffle(shuffled_unit_ids)
    num_shared = int(fraction_shared * num_units)
    num_only = (num_units - num_shared) // 2
    shared_unit_ids = set(shuffled_unit_ids[:num_shared])
    only1_unit_ids = set(shuffled_unit_ids[num_shared:num_shared + num_only])
    only2_unit_ids = set(shuffled_unit_ids[num_shared + num_only:num_shared + 2 * num_only])

    # keep the original unit order, so that the unit ids of both analyzers stay sorted
    sorting1 = sorting.select_units([u for u in sorting.unit_ids if u in shared_unit_ids | only1_unit_ids])
    sorting2 = sorting.select_units([u for u in sorting.unit_ids if u in shared_unit_ids | only2_unit_ids])

    # drop some spikes of sorting2, so that the shared units do not agree perfectly
    spikes2 = sorting2.to_spike_vector()
    keep = rng.random(spikes2.size) >= fraction_dropped_spikes
    sorting2 = si.NumpySorting(spikes2[keep], sorting2.sampling_frequency, sorting2.unit_ids)

    folders = []
    for i, sorting_i in enumerate([sorting1, sorting2]):
        sorting_i = sorting_i.rename_units(sorting_i.unit_ids.astype(unit_dtype))
        sorting_i.set_property(key='my_own_property',
                               values=np.array([f"yep{i}" for i in range(sorting_i.unit_ids.size)]))

        folder = test_folder / f"sorting_analyzer_{i + 1}"
        _create_analyzer(sorting_i, recording, folder, [
            ("random_spikes", dict(method="uniform", max_spikes_per_unit=500)),
            ("waveforms", _job_kwargs),
            ("templates", _job_kwargs),
            ("noise_levels", _job_kwargs),
            ("unit_locations", {}),
            ("quality_metrics", dict(metric_names=["snr", "firing_rate"])),
            ("template_metrics", {}),
            (["spike_amplitudes", "spike_locations", "amplitude_scalings"], _job_kwargs),
            ("correlograms", {}),
        ])
        folders.append(folder)

    return folders


def make_curation_dict(analyzer):
    unit_ids = analyzer.unit_ids.tolist()
    curation_dict = {
        "format_version": "2",
        "unit_ids": unit_ids,
        "label_definitions": {
            "quality":{
                "label_options": ["good", "noise", "MUA"],
                "exclusive": True,
            },
            "putative_type":{
                "label_options": ["excitatory", "inhibitory", "pyramidal", "mitral"],
                "exclusive": True,
            }
        },
        "manual_labels": [
            {'unit_id': unit_ids[1], "quality": ["MUA"]},
            {'unit_id': unit_ids[2], "putative_type": ["exitatory"]},
            {'unit_id': unit_ids[3], "quality": ["noise"], "putative_type": ["inhibitory"]},
        ],
        "merges": [{"unit_ids": unit_ids[:3]}, {"unit_ids": unit_ids[3:5]}],
        "removed": unit_ids[5:8],
    }
    return curation_dict


def prepare_analyzer_for_gui(analyzer, events=None, seed=None):
    """
    Add what the GUI scripts and tests exercise on top of the dataset, in memory only:
    a unit property, a time shift with a gap in the middle of each segment, and
    optionally random events.

    events: None | "times" | "samples", the format of the events dict to build.
    The "times" events include some outside of the recording, to test the filtering.

    Returns (extra_unit_properties, events_dict).
    """
    rng = np.random.default_rng(seed)
    n = analyzer.unit_ids.size
    analyzer.sorting.set_property(key='yep', values=np.array([f"yep{i}" for i in range(n)]))
    extra_unit_properties = dict(
        yop=np.array([f"yop{i}" for i in range(n)]),
        yip=np.array([f"yip{i}" for i in range(n)]),
    )

    for segment_index in range(analyzer.get_num_segments()):
        times = analyzer.recording.get_times(segment_index) + (segment_index + 1) * 100
        times[len(times) // 2:] += 5  # a gap in the middle
        analyzer.recording.set_times(times, segment_index=segment_index)

    events_dict = None
    if events == "times":
        events_dict = {"event1": {"times": []}, "event2": {"times": []}}
        for segment_index in range(analyzer.get_num_segments()):
            times = analyzer.recording.get_times(segment_index)
            events_dict["event1"]["times"].append(
                np.concatenate([rng.choice(times, 30), [times[0] - 10, times[-1] + 20]])
            )
            events_dict["event2"]["times"].append(
                np.concatenate([rng.choice(times, 50), [times[0] - 5, times[-1] + 15]])
            )
    elif events == "samples":
        events_dict = {"event1": {"samples": []}, "event2": {"samples": []}}
        for segment_index in range(analyzer.get_num_segments()):
            num_samples = analyzer.get_num_samples(segment_index)
            events_dict["event1"]["samples"].append(rng.choice(num_samples, 30))
            events_dict["event2"]["samples"].append(rng.choice(num_samples, 50))
    elif events is not None:
        raise ValueError(f"events must be None, 'times' or 'samples', not {events!r}")

    return extra_unit_properties, events_dict


def set_comparison_labels(analyzer1, analyzer2):
    """A "label" property on both analyzers, in memory only, for the comparison label views."""
    labels1 = ["good"] * (len(analyzer1.unit_ids) - 10) + ["noise"] * 10
    analyzer1.set_sorting_property("label", labels1, save=False)
    labels2 = ["noise"] * (len(analyzer2.unit_ids) - 10) + ["good"] * 10
    analyzer2.set_sorting_property("label", labels2, save=False)
