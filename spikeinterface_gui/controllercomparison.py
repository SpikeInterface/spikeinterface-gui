import time

import numpy as np
import pandas as pd


from spikeinterface import compute_sparsity
from spikeinterface.core import get_template_extremum_channel
from spikeinterface.core.recording_tools import get_rec_attributes, do_recording_attributes_match
from spikeinterface.comparison import compare_two_sorters
from spikeinterface.widgets.utils import make_units_table_from_analyzer
from spikeinterface.widgets.sorting_summary import _default_displayed_unit_properties

from .controller import Controller, spike_dtype, _default_main_settings


# extensions that cannot be shared/concatenated between the two analyzers
_comparison_skip_extensions = ["principal_components", "correlograms", "isi_histograms", "template_similarity"]


class ControllerComparison(Controller):
    """
    Controller for comparison mode.

    Two SortingAnalyzer are virtually concatenated into a single unit_id namespace so that
    all the standard views can be reused. On top of that a `compare_two_sorters` comparison
    is computed and exposed through `get_agreement_scores()` / `get_matching()` /
    `get_venn_unit_ids()`.

    `Controller.__init__` is deliberately not called: this `__init__` establishes the same
    attribute contract (`spikes`, `unit_ids`, `templates_average`, `unit_positions`, ...) from
    the two analyzers, and `self.analyzer` is set to `analyzer1` so that every recording/probe
    facing method of the base class keeps working (only analyzer1's recording is used, the
    channels are shared).
    """

    def __init__(
        self, analyzer1=None, analyzer2=None,
        analyzer1_name="1", analyzer2_name="2",
        backend="qt", parent=None, verbose=False, with_traces=True,
        displayed_unit_properties=None,
        extra_unit_properties=None, skip_extensions=None, disable_save_settings_button=False,
        user_main_settings=None,
    ):
        self.views = []
        skip_extensions = list(skip_extensions) if skip_extensions is not None else []
        skip_extensions.extend(_comparison_skip_extensions)
        self.skip_extensions = sorted(set(skip_extensions))

        self.backend = backend
        self.disable_save_settings_button = disable_save_settings_button
        # curation is not possible in comparison mode
        self.curation = False
        # this is not to have a popup when closing
        self.current_curation_saved = True
        self.external_data = None
        self.events = None
        self.save_on_compute = False

        if self.backend == "qt":
            from .backend_qt import SignalHandler
            self.signal_handler = SignalHandler(self, parent=parent)

        elif self.backend == "panel":
            from .backend_panel import SignalHandler
            self.signal_handler = SignalHandler(self, parent=parent)

        self.with_traces = with_traces

        self.analyzer1 = analyzer1
        self.analyzer2 = analyzer2
        self.analyzer1_name = analyzer1_name
        self.analyzer2_name = analyzer2_name
        # the base class methods that touch the recording/probe/format use self.analyzer
        self.analyzer = analyzer1
        assert self.analyzer1.get_extension("random_spikes") is not None
        assert self.analyzer2.get_extension("random_spikes") is not None

        assert self.analyzer1.return_in_uV == self.analyzer2.return_in_uV
        self.return_in_uV = self.analyzer1.return_in_uV

        # check recording attributes match
        recording1 = None
        recording2 = None
        self.use_recordings = False

        try:
            recording1 = self.analyzer1.recording
        except:
            pass
        try:
            recording2 = self.analyzer2.recording
        except:
            pass
        if recording1 is not None and recording2 is not None:
            match, diff = do_recording_attributes_match(
                recording1, get_rec_attributes(recording2)
            )
            if match:
                self.use_recordings = True

        self.verbose = verbose
        t0 = time.perf_counter()

        self.main_settings = _default_main_settings.copy()
        if user_main_settings is not None:
            self.main_settings.update(user_main_settings)

        self.num_channels = self.analyzer1.get_num_channels()

        # the combined unit_id namespace and the mappings back to the original ids.
        # computed once: unit_ids is read inside loops all over the views.
        self._make_unit_id_mappings()

        # this now private and should be access using function
        self._visible_unit_ids = [self.unit_ids[0]]

        # sparsity1
        if self.analyzer1.sparsity is None:
            self.external_sparsity1 = compute_sparsity(self.analyzer1, method="radius", radius_um=90.)
            self.analyzer_sparsity1 = None
        else:
            self.external_sparsity1 = None
            self.analyzer_sparsity1 = self.analyzer1.sparsity
        # sparsity2
        if self.analyzer2.sparsity is None:
            self.external_sparsity2 = compute_sparsity(self.analyzer2, method="radius", radius_um=90.)
            self.analyzer_sparsity2 = None
        else:
            self.external_sparsity2 = None
            self.analyzer_sparsity2 = self.analyzer2.sparsity

        if verbose:
            print("Comparing spike sorting outputs")
        t0 = time.perf_counter()
        self.comp = compare_two_sorters(self.analyzer1.sorting, self.analyzer2.sorting,
                                        sorting1_name=self.analyzer1_name, sorting2_name=self.analyzer2_name)
        if verbose:
            print("Comparing took", time.perf_counter() - t0)
        # agreement threshold shared by all the comparison views
        self._agreement_threshold = self.comp.match_score
        self._matching_cache = {}
        self._ordered_agreement_scores = None

        # spikes
        t0 = time.perf_counter()
        if verbose:
            print('Gathering all spikes')
        self._extremum_channel1 = get_template_extremum_channel(
            self.analyzer1, mode="extremum", peak_sign='both', outputs='index')
        self._extremum_channel2 = get_template_extremum_channel(
            self.analyzer2, mode="extremum", peak_sign='both', outputs='index')
        self._extremum_channel = {}
        for unit_id in self.unit_ids:
            if self.get_analyzer_index(unit_id) == 1:
                extremum_channels = self._extremum_channel1
            else:
                extremum_channels = self._extremum_channel2
            self._extremum_channel[unit_id] = extremum_channels[self.get_original_unit_id(unit_id)]

        spike_vector1 = self.analyzer1.sorting.to_spike_vector(concatenated=True, extremum_channel_inds=self._extremum_channel1)
        spike_vector2 = self.analyzer2.sorting.to_spike_vector(concatenated=True, extremum_channel_inds=self._extremum_channel2)

        random_spikes_indices1 = self.analyzer1.get_extension("random_spikes").get_data()
        random_spikes_indices2 = self.analyzer2.get_extension("random_spikes").get_data()

        # align=True is required for np.searchsorted (and therefore trace views) to be fast.
        self.spikes = np.zeros(spike_vector1.size + spike_vector2.size, dtype=np.dtype(spike_dtype, align=True))
        self.spikes['sample_index'] = np.concatenate([spike_vector1['sample_index'], spike_vector2['sample_index']])
        self.spikes['unit_index'] = np.concatenate([spike_vector1['unit_index'], spike_vector2['unit_index'] + self._num_units1])
        self.spikes['segment_index'] = np.concatenate([spike_vector1['segment_index'], spike_vector2['segment_index']])
        self.spikes['channel_index'] = np.concatenate([spike_vector1['channel_index'], spike_vector2['channel_index']])
        self.spikes['rand_selected'][:] = False
        self.spikes['rand_selected'][random_spikes_indices1] = True
        self.spikes['rand_selected'][random_spikes_indices2 + spike_vector1.size] = True

        # sort spikes by segment then sample, so that the base class bookkeeping applies
        num_seg = self.analyzer1.get_num_segments()
        self.spike_order = np.lexsort((self.spikes['sample_index'], self.spikes['segment_index']))
        self.spikes = self.spikes[self.spike_order]

        self._build_spike_indices(num_seg)

        t1 = time.perf_counter()
        if verbose:
            print('Gathering all spikes took', t1 - t0)

        if verbose:
            print('Loading extensions')
        # Mandatory extensions: computation forced
        if verbose:
            print('\tLoading templates')
        temp_ext1 = self.analyzer1.get_extension("templates")
        temp_ext2 = self.analyzer2.get_extension("templates")
        assert temp_ext1 is not None and temp_ext2 is not None, "Both analyzers should have 'templates' extension"
        self.nbefore, self.nafter = temp_ext1.nbefore, temp_ext1.nafter

        self.templates_average = np.vstack([temp_ext1.get_templates(operator='average'), temp_ext2.get_templates(operator='average')])

        if 'std' in temp_ext1.params['operators'] and 'std' in temp_ext2.params['operators']:
            self.templates_std = np.vstack([temp_ext1.get_templates(operator='std'), temp_ext2.get_templates(operator='std')])
        else:
            self.templates_std = None

        if verbose:
            print('\tLoading unit_locations')
        ext1 = self.analyzer1.get_extension('unit_locations')
        ext2 = self.analyzer2.get_extension('unit_locations')
        assert ext1 is not None and ext2 is not None, "Both analyzers should have 'unit_locations' extension"
        self.unit_positions = np.vstack([ext1.get_data()[:, :2], ext2.get_data()[:, :2]])

        # Optional extensions : can be None or skipped
        if verbose:
            print('\tLoading noise_levels')
        ext1 = self.analyzer1.get_extension('noise_levels')
        if ext1 is None and self.has_extension('recording'):
            print('Force compute "noise_levels" is needed')
            ext1 = self.analyzer1.compute_one_extension('noise_levels')
        self.noise_levels = ext1.get_data() if ext1 is not None else None

        if "quality_metrics" in self.skip_extensions:
            if self.verbose:
                print('\tSkipping quality_metrics')
            self.metrics = None
        else:
            if verbose:
                print('\tLoading quality_metrics')
            qm_ext1 = self.analyzer1.get_extension('quality_metrics')
            qm_ext2 = self.analyzer2.get_extension('quality_metrics')
            if qm_ext1 is not None and qm_ext2 is not None:
                self.metrics = pd.concat([qm_ext1.get_data(), qm_ext2.get_data()])
                self.metrics.index = self.unit_ids
            else:
                self.metrics = None

        if "spike_amplitudes" in self.skip_extensions:
            if self.verbose:
                print('\tSkipping spike_amplitudes')
            self.spike_amplitudes = None
        else:
            if verbose:
                print('\tLoading spike_amplitudes')
            sa_ext1 = self.analyzer1.get_extension('spike_amplitudes')
            sa_ext2 = self.analyzer2.get_extension('spike_amplitudes')
            if sa_ext1 is not None and sa_ext2 is not None:
                self.spike_amplitudes = np.concatenate([sa_ext1.get_data(), sa_ext2.get_data()])[self.spike_order]
            else:
                self.spike_amplitudes = None

        if "spike_locations" in self.skip_extensions:
            if self.verbose:
                print('\tSkipping spike_locations')
            self.spike_depths = None
        else:
            if verbose:
                print('\tLoading spike_locations')
            sl_ext1 = self.analyzer1.get_extension('spike_locations')
            sl_ext2 = self.analyzer2.get_extension('spike_locations')
            if sl_ext1 is not None and sl_ext2 is not None:
                self.spike_depths = np.concatenate([sl_ext1.get_data()["y"], sl_ext2.get_data()["y"]])[self.spike_order]
            else:
                self.spike_depths = None

        # Correlograms, ISIs and template_similarity cannot be concatenated: always skipped
        self.correlograms, self.correlograms_bins = None, None
        self.isi_histograms, self.isi_bins = None, None
        self._similarity_by_method = {}

        if "waveforms" in self.skip_extensions:
            if self.verbose:
                print('\tSkipping waveforms')
            self.waveforms_ext1, self.waveforms_ext2 = None, None
        else:
            if verbose:
                print('\tLoading waveforms')
            wf_ext1 = self.analyzer1.get_extension('waveforms')
            wf_ext2 = self.analyzer2.get_extension('waveforms')
            if wf_ext1 is not None and wf_ext2 is not None:
                self.waveforms_ext1 = wf_ext1
                self.waveforms_ext2 = wf_ext2
            else:
                self.waveforms_ext1, self.waveforms_ext2 = None, None
        self.waveforms_ext = self.waveforms_ext1

        # valid_unit_periods, keyed by the combined unit ids. Only used when both
        # analyzers have it, like the other optional per-unit extensions above.
        if self.analyzer1.has_extension("valid_unit_periods") and self.analyzer2.has_extension("valid_unit_periods"):
            valid_periods1 = self.analyzer1.get_extension("valid_unit_periods").get_data(outputs="by_unit")
            valid_periods2 = self.analyzer2.get_extension("valid_unit_periods").get_data(outputs="by_unit")
            self.valid_periods = {}
            for unit_id in self.unit_ids:
                valid_periods = valid_periods1 if self.get_analyzer_index(unit_id) == 1 else valid_periods2
                self.valid_periods[unit_id] = valid_periods[self.get_original_unit_id(unit_id)]
        else:
            self.valid_periods = None

        # principal_components is always skipped: the two analyzers have unrelated PC spaces
        self._pc_projections = None
        self._pc_indices = None
        self.pc_ext = None

        self._potential_merges = None

        t1 = time.perf_counter()
        if verbose:
            print('Loading extensions took', t1 - t0)

        t0 = time.perf_counter()

        # some direct attribute
        self.num_segments = self.analyzer1.get_num_segments()
        self.sampling_frequency = self.analyzer1.sampling_frequency
        num_spikes1 = self.analyzer1.sorting.count_num_spikes_per_unit(outputs="dict")
        num_spikes2 = self.analyzer2.sorting.count_num_spikes_per_unit(outputs="dict")
        self.num_spikes = {}
        for unit_id in self.unit_ids:
            num_spikes = num_spikes1 if self.get_analyzer_index(unit_id) == 1 else num_spikes2
            self.num_spikes[unit_id] = num_spikes[self.get_original_unit_id(unit_id)]

        # spikeinterface handle colors in matplotlib style tuple values in range (0,1)
        self.refresh_colors()

        # at init, we set the visible channels as the sparsity of the first unit
        self.visible_channel_inds = np.flatnonzero(self.get_sparsity_mask()[0])

        self._spike_visible_indices = np.array([], dtype='int64')
        self._spike_selected_indices = np.array([], dtype='int64')
        self.update_visible_spikes()

        self._traces_cached = {}

        unit_tables = []
        for analyzer in [self.analyzer1, self.analyzer2]:
            unit_table = make_units_table_from_analyzer(analyzer)
            unit_tables.append(unit_table)
        self.units_table = pd.concat(unit_tables, ignore_index=True)
        self.units_table.index = self.unit_ids
        if displayed_unit_properties is None:
            displayed_unit_properties = list(_default_displayed_unit_properties)
        if extra_unit_properties is not None:
            displayed_unit_properties += list(extra_unit_properties.keys())
        displayed_unit_properties = [v for v in displayed_unit_properties if v in self.units_table.columns]
        self.displayed_unit_properties = displayed_unit_properties

        # set default time info
        self.update_time_info()

    ## combined unit_id namespace ##

    def _make_unit_id_mappings(self):
        """
        Build the combined unit_ids and the mappings between combined and original ids.

        Integer unit ids are offset, other ids are suffixed with the analyzer name.
        """
        unit_ids1 = np.asarray(self.analyzer1.unit_ids)
        unit_ids2 = np.asarray(self.analyzer2.unit_ids)
        self._num_units1 = unit_ids1.size

        if unit_ids1.dtype.kind == "i" and unit_ids2.dtype.kind == "i":
            self._unit_ids = np.concatenate((unit_ids1, unit_ids2 + max(unit_ids1) + 1))
        else:
            self._unit_ids = np.array(
                [f"{unit_id}_{self.analyzer1_name}" for unit_id in unit_ids1]
                + [f"{unit_id}_{self.analyzer2_name}" for unit_id in unit_ids2]
            )

        original_unit_ids = list(unit_ids1) + list(unit_ids2)
        analyzer_indices = [1] * unit_ids1.size + [2] * unit_ids2.size
        self._original_unit_id_by_id = dict(zip(self._unit_ids, original_unit_ids))
        self._analyzer_index_by_id = dict(zip(self._unit_ids, analyzer_indices))
        # (analyzer_index, original_unit_id) -> combined unit_id
        self._combined_unit_id_by_original = {
            (analyzer_index, original_unit_id): unit_id
            for analyzer_index, original_unit_id, unit_id in zip(analyzer_indices, original_unit_ids, self._unit_ids)
        }

    @property
    def unit_ids(self):
        return self._unit_ids

    @property
    def unit_ids1(self):
        return self._unit_ids[:self._num_units1]

    @property
    def unit_ids2(self):
        return self._unit_ids[self._num_units1:]

    def get_original_unit_id(self, unit_id):
        """Get the unit id in its own analyzer, given a combined unit_id"""
        return self._original_unit_id_by_id[unit_id]

    def get_analyzer_index(self, unit_id):
        """Get 1 or 2, telling which analyzer a combined unit_id belongs to"""
        return self._analyzer_index_by_id[unit_id]

    def get_combined_unit_id(self, analyzer_index, original_unit_id):
        """Inverse of get_original_unit_id: (1 or 2, original unit id) -> combined unit_id"""
        return self._combined_unit_id_by_original[(analyzer_index, original_unit_id)]

    def get_analyzer_name(self, analyzer_index):
        return self.analyzer1_name if analyzer_index == 1 else self.analyzer2_name

    ## comparison zone ##

    @property
    def agreement_threshold(self):
        return self._agreement_threshold

    def set_agreement_threshold(self, threshold):
        """Set the agreement threshold shared by all the comparison views"""
        self._agreement_threshold = float(threshold)

    def get_agreement_scores(self, ordered=False):
        """
        Agreement scores as a DataFrame indexed by the *original* unit ids of
        analyzer1 (rows) and analyzer2 (columns).

        When `ordered` is True the diagonalized ordering of the comparison is returned.
        """
        if not ordered:
            return self.comp.agreement_scores
        if self._ordered_agreement_scores is None:
            self._ordered_agreement_scores = self.comp.get_ordered_agreement_scores()
        return self._ordered_agreement_scores

    def get_matching(self, threshold=None):
        """
        One-to-one (hungarian) matching at the given agreement threshold.

        Returns (match_12, match_21), two pandas Series indexed by the original unit ids.
        Unmatched units hold a sentinel that depends on the unit id dtype, use
        `is_unmatched()` to test it.
        """
        from spikeinterface.comparison.comparisontools import make_hungarian_match

        if threshold is None:
            threshold = self._agreement_threshold
        threshold = float(threshold)
        if threshold not in self._matching_cache:
            self._matching_cache[threshold] = make_hungarian_match(self.comp.agreement_scores, threshold)
        return self._matching_cache[threshold]

    def get_best_matching(self, threshold=None):
        """
        Best (not necessarily one-to-one) matching at the given agreement threshold.

        Returns (best_match_12, best_match_21), same convention as `get_matching`.
        """
        from spikeinterface.comparison.comparisontools import make_best_match

        if threshold is None:
            threshold = self._agreement_threshold
        return make_best_match(self.comp.agreement_scores, float(threshold))

    @staticmethod
    def is_unmatched(original_unit_id):
        """
        Test the unmatched sentinel of a match Series.

        spikeinterface uses -1 for integer unit ids and "" for string/object unit ids.
        """
        if isinstance(original_unit_id, str):
            return original_unit_id == ""
        return original_unit_id == -1

    def get_venn_unit_ids(self, threshold=None):
        """
        Split the units in the 3 regions of the comparison Venn diagram.

        Returns a dict with combined unit_ids:
          * "matched" : list of (unit_id1, unit_id2) pairs agreeing above the threshold
          * "only1" : units of analyzer1 with no match
          * "only2" : units of analyzer2 with no match
        """
        match_12, _ = self.get_matching(threshold=threshold)

        matched = []
        only1 = []
        matched_original2 = set()
        for original_unit_id1 in match_12.index:
            original_unit_id2 = match_12[original_unit_id1]
            unit_id1 = self.get_combined_unit_id(1, original_unit_id1)
            if self.is_unmatched(original_unit_id2):
                only1.append(unit_id1)
            else:
                matched.append((unit_id1, self.get_combined_unit_id(2, original_unit_id2)))
                matched_original2.add(original_unit_id2)

        only2 = [
            self.get_combined_unit_id(2, original_unit_id2)
            for original_unit_id2 in self.analyzer2.unit_ids
            if original_unit_id2 not in matched_original2
        ]

        return dict(matched=matched, only1=only1, only2=only2)

    ## overrides of the single analyzer behavior ##

    def has_extension(self, extension_name):
        if extension_name == 'recording':
            return self.use_recordings
        elif extension_name == 'comparison':
            return True
        else:
            return Controller.has_extension(self, extension_name)

    def get_information_txt(self):
        nseg = self.analyzer1.get_num_segments()
        nchan = self.analyzer1.get_num_channels()
        txt = f"{nchan} channels - {nseg} segments\n"
        txt += f"{self.analyzer1_name}: {len(self.unit_ids1)} units - "
        txt += f"{self.analyzer2_name}: {len(self.unit_ids2)} units\n"
        venn = self.get_venn_unit_ids()
        txt += f"{len(venn['matched'])} matched pairs at agreement >= {self.agreement_threshold:.2f}"
        return txt

    def get_waveforms(self, unit_id, force_dense=False):
        if self.get_analyzer_index(unit_id) == 1:
            analyzer, waveforms_ext = self.analyzer1, self.waveforms_ext1
        else:
            analyzer, waveforms_ext = self.analyzer2, self.waveforms_ext2
        original_unit_id = self.get_original_unit_id(unit_id)
        wfs = waveforms_ext.get_waveforms_one_unit(original_unit_id, force_dense=force_dense)
        if analyzer.sparsity is None or force_dense:
            # dense waveforms
            chan_inds = np.arange(analyzer.get_num_channels(), dtype='int64')
        else:
            # sparse waveforms
            chan_inds = analyzer.sparsity.unit_id_to_channel_indices[original_unit_id]
        return wfs, chan_inds

    def get_sparsity_mask(self):
        masks = []
        for external_sparsity, analyzer_sparsity in (
            (self.external_sparsity1, self.analyzer_sparsity1),
            (self.external_sparsity2, self.analyzer_sparsity2),
        ):
            masks.append(external_sparsity.mask if external_sparsity is not None else analyzer_sparsity.mask)
        return np.vstack(masks)

    def get_all_pcs(self):
        # the two analyzers have unrelated PC spaces, they cannot be concatenated
        return None, None

    def get_template_upsampling_factor(self):
        # template_metrics of the two analyzers are not merged: no upsampling in comparison mode
        return 1

    def get_upsampled_templates(self, unit_id):
        # same 3-tuple contract as the base class, without the upsampled part
        unit_index = list(self.unit_ids).index(unit_id)
        chan_ind = self.get_extremum_channel(unit_id)
        template = self.templates_average[unit_index, :, chan_ind]
        return template, None, None

    def compute_unit_positions(self, method, method_kwargs):
        unit_positions = []
        for analyzer in (self.analyzer1, self.analyzer2):
            ext = analyzer.compute_one_extension(
                'unit_locations', save=self.save_on_compute, method=method, **method_kwargs
            )
            unit_positions.append(ext.get_data()[:, :2])
        self.unit_positions = np.vstack(unit_positions)

    def compute_similarity(self, method='l1'):
        raise NotImplementedError("template_similarity cannot be computed in comparison mode")

    def compute_correlograms(self, window_ms, bin_ms):
        raise NotImplementedError("correlograms cannot be computed in comparison mode")

    def compute_isi_histograms(self, window_ms, bin_ms):
        raise NotImplementedError("isi_histograms cannot be computed in comparison mode")

    def compute_auto_merge(self, **params):
        raise NotImplementedError("auto merge is not available in comparison mode")
