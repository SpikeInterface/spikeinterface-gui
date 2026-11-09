import spikeinterface.full as si

from spikeinterface_gui.controller import Controller


def test_controller(analyzer_folder):
    sorting_analyzer = si.load_sorting_analyzer(analyzer_folder / "sorting_analyzer")
    controller = Controller(sorting_analyzer, backend=None)

    # unit_ids mirror the analyzer
    assert list(controller.unit_ids) == list(controller.analyzer.unit_ids)

    # isi histograms were computed and are shaped consistently with the units
    isi_histograms, isi_bins = controller.get_isi_histograms()
    assert isi_histograms.shape[0] == controller.unit_ids.size
    assert isi_bins.shape[0] == isi_histograms.shape[1] + 1

