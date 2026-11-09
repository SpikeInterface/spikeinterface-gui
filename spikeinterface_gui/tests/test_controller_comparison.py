import numpy as np
import pytest

import spikeinterface.full as si

from spikeinterface_gui.controllercomparison import ControllerComparison


@pytest.fixture(scope="module")
def controller(comparison_folder):
    analyzer1 = si.load_sorting_analyzer(comparison_folder / "sorting_analyzer_1")
    analyzer2 = si.load_sorting_analyzer(comparison_folder / "sorting_analyzer_2")
    return ControllerComparison(analyzer1, analyzer2, backend=None)


def test_get_spike_venn(controller):
    unit_id1, unit_id2 = controller.get_venn_unit_ids()['matched'][0]
    venn = controller.get_spike_venn(unit_id1, unit_id2)

    assert len(venn['matched1']) == len(venn['matched2']) > 0
    assert len(venn['matched1']) + len(venn['only1']) == controller.num_spikes[unit_id1]
    assert len(venn['matched2']) + len(venn['only2']) == controller.num_spikes[unit_id2]
    assert np.intersect1d(venn['matched1'], venn['only1']).size == 0
    assert np.intersect1d(venn['matched2'], venn['only2']).size == 0
    assert np.all(controller.spikes['unit_index'][venn['only2']] == list(controller.unit_ids).index(unit_id2))

    # waveforms only for the random spikes, and they are the right rows
    wfs, chan_inds, kept = controller.get_waveforms_for_spikes(unit_id1, venn['matched1'])
    assert wfs.shape[0] == kept.size
    assert np.all(np.isin(kept, controller.random_spikes_indices))
    all_wfs, _ = controller.get_waveforms(unit_id1)
    unit_inds = controller.get_spike_indices(unit_id1)
    random_inds = unit_inds[np.isin(unit_inds, controller.random_spikes_indices)]
    assert np.array_equal(wfs[0], all_wfs[np.flatnonzero(random_inds == kept[0])[0]])


def test_correlograms(controller):
    ccg, bins = controller.get_correlograms()
    num_units1 = len(controller.unit_ids1)
    acg1, _ = controller.analyzer1.get_extension('correlograms').get_data()
    acg2, _ = controller.analyzer2.get_extension('correlograms').get_data()
    assert np.array_equal(ccg[0, 0], acg1[0, 0])
    assert np.array_equal(ccg[num_units1, num_units1], acg2[0, 0])
    # the cross-sorter blocks are not computed
    assert not np.any(ccg[:num_units1, num_units1:])

