import time

import numpy as np
import pandas as pd


from spikeinterface.widgets.utils import get_some_colors
from spikeinterface import compute_sparsity
from spikeinterface.core import get_template_extremum_channel
from spikeinterface.core.sorting_tools import spike_vector_to_indices
from spikeinterface.core.recording_tools import get_rec_attributes, do_recording_attributes_match
from spikeinterface.comparison import compare_two_sorters
from spikeinterface.widgets.utils import make_units_table_from_analyzer


spike_dtype =[('sample_index', 'int64'), ('unit_index', 'int64'), 
    ('channel_index', 'int64'), ('segment_index', 'int64'),
    ('visible', 'bool'), ('selected', 'bool'), ('rand_selected', 'bool')]


_default_main_settings = dict(
    max_visible_units=10,
    color_mode='color_by_unit',
    use_times=False
)

from spikeinterface.widgets.sorting_summary import _default_displayed_unit_properties
        


class ControllerComparison():
    def __init__(
        self, analyzer1=None, analyzer2=None, 
        analyzer1_name="1", analyzer2_name="2",
        backend="qt", parent=None, verbose=False, with_traces=True,
        displayed_unit_properties=None,
        extra_unit_properties=None, skip_extensions=None, disable_save_settings_button=False
    ):
        self.views = []
        skip_extensions = skip_extensions if skip_extensions is not None else []

        self.skip_extensions = skip_extensions
        self.skip_extensions.extend(["principal_components", "correlograms", "isi_histograms", "template_similarity"])
        self.skip_extensions = list(set(self.skip_extensions))
        self.backend = backend
        self.disable_save_settings_button = disable_save_settings_button
        self.curation = False
        # this is not to have a popup when closing
        self.current_curation_saved = True

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

        self.num_channels = self.analyzer1.get_num_channels()
        # this now private and shoudl be acess using function
        self._visible_unit_ids = [self.unit_ids[0]]

        # sparsity1
        if self.analyzer1.sparsity is None:
            self.external_sparsity1 = compute_sparsity(self.analyzer1, method="radius",radius_um=90.)
            self.analyzer_sparsity1 = None
        else:
            self.external_sparsity1 = None
            self.analyzer_sparsity1 = self.analyzer1.sparsity
        # sparsity2
        if self.analyzer2.sparsity is None:
            self.external_sparsity2 = compute_sparsity(self.analyzer2, method="radius",radius_um=90.)
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

        # spikes
        t0 = time.perf_counter()
        if verbose:
            print('Gathering all spikes')
        self._extremum_channel1 = get_template_extremum_channel(self.analyzer1, peak_sign='neg', outputs='index')
        self._extremum_channel2 = get_template_extremum_channel(self.analyzer2, peak_sign='neg', outputs='index')
        self._extremum_channel = {}
        for unit_id in self.unit_ids:
            if unit_id in self.unit_ids1:
                extremum_channels = self._extremum_channel1
            else:
                extremum_channels = self._extremum_channel2
            self._extremum_channel[unit_id] = extremum_channels[self.get_original_unit_id(unit_id)]

        spike_vector1 = self.analyzer1.sorting.to_spike_vector(concatenated=True, extremum_channel_inds=self._extremum_channel1)
        spike_vector2 = self.analyzer2.sorting.to_spike_vector(concatenated=True, extremum_channel_inds=self._extremum_channel2)

        random_spikes_indices1 = self.analyzer1.get_extension("random_spikes").get_data()
        random_spikes_indices2 = self.analyzer2.get_extension("random_spikes").get_data()

        self.spikes = np.zeros(spike_vector1.size + spike_vector2.size, dtype=spike_dtype)
        self.spikes['sample_index'] = np.concatenate([spike_vector1['sample_index'], spike_vector2['sample_index']])
        self.spikes['unit_index'] = np.concatenate([spike_vector1['unit_index'], spike_vector2['unit_index'] + self.analyzer1.get_num_units()])
        self.spikes['segment_index'] = np.concatenate([spike_vector1['segment_index'], spike_vector2['segment_index']])
        self.spikes['channel_index'] = np.concatenate([spike_vector1['channel_index'], spike_vector2['channel_index']])
        self.spikes['rand_selected'][:] = False
        self.spikes['rand_selected'][random_spikes_indices1] = True
        self.spikes['rand_selected'][random_spikes_indices2 + spike_vector1.size] = True

        # sort spikes
        num_seg = self.analyzer1.get_num_segments()
        self.spike_order = np.argsort(self.spikes['sample_index'], kind='stable')
        self.spikes = self.spikes[self.spike_order]

        seg_limits = np.searchsorted(self.spikes["segment_index"], np.arange(num_seg + 1))
        self.segment_slices = {segment_index: slice(seg_limits[segment_index], seg_limits[segment_index + 1]) for segment_index in range(num_seg)}
        
        spike_vector2 = []
        for segment_index in range(num_seg):
            seg_slice = self.segment_slices[segment_index]
            spike_vector2.append(self.spikes[seg_slice])
        self.final_spike_samples = [segment_spike_vector[-1][0] for segment_spike_vector in spike_vector2]
        # this is dict of list because per segment spike_indices[segment_index][unit_id]
        spike_indices_abs = spike_vector_to_indices(spike_vector2, self.unit_ids, absolute_index=True)
        spike_indices = spike_vector_to_indices(spike_vector2, self.unit_ids)
        # this is flatten
        spike_per_seg = [s.size for s in spike_vector2]
        # dict[unit_id] -> all indices for this unit across segments
        self._spike_index_by_units = {}
        # dict[segment_index][unit_id] -> all indices for this unit for one segment
        self._spike_index_by_segment_and_units = spike_indices_abs
        for unit_id in self.unit_ids:
            inds = []
            for seg_ind in range(num_seg):
                inds.append(spike_indices[seg_ind][unit_id] + int(np.sum(spike_per_seg[:seg_ind])))
            self._spike_index_by_units[unit_id] = np.concatenate(inds)

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

        if 'std' in temp_ext1.params['operators']:
            self.templates_std = np.vstack([temp_ext1.get_templates(operator='std'), temp_ext2.get_templates(operator='std')])
        else:
            self.templates_std = None

        if verbose:
            print('\tLoading unit_locations')
        ext1 =self.analyzer1.get_extension('unit_locations')
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

        # Correlograms, ISIs are skipped
        self.correlograms, self.correlograms_bins = None, None
        self.isi_histograms, self.isi_bins = None, None

        self._similarity_by_method = {}
        # if "template_similarity" in self.skip_extensions:
        #     if self.verbose:
        #         print('\tSkipping template_similarity')
        # else:
        #     if verbose:
        #         print('\tLoading template_similarity')
        #     ts_ext = analyzer.get_extension('template_similarity')
        #     if ts_ext is not None:
        #         method = ts_ext.params["method"]
        #         self._similarity_by_method[method] = ts_ext.get_data()
        #     else:
        #         if len(self.unit_ids) <= 64 and len(self.channel_ids) <= 64:
        #             # precompute similarity when low channel/units count
        #             method = 'l1'
        #             ts_ext = analyzer.compute_one_extension('template_similarity', method=method, save=save_on_compute)
        #             self._similarity_by_method[method] = ts_ext.get_data()

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

        self._pc_projections = None
        if "principal_components" in self.skip_extensions:
            if self.verbose:
                print('\tSkipping principal_components')
            self.pc_ext1, self.pc_ext2 = None, None
        else:
            if verbose:
                print('\tLoading principal_components')
            pc_ext1 = self.analyzer1.get_extension('principal_components')
            pc_ext2 = self.analyzer2.get_extension('principal_components')
            if pc_ext1 is not None and pc_ext2 is not None:
                self.pc_ext1 = pc_ext1
                self.pc_ext2 = pc_ext2
            else:
                self.pc_ext1, self.pc_ext2 = None, None

        self._potential_merges = None

        t1 = time.perf_counter()
        if verbose:
            print('Loading extensions took', t1 - t0)

        t0 = time.perf_counter()

        # some direct attribute
        self.num_segments =self.analyzer1.get_num_segments()
        self.sampling_frequency =self.analyzer1.sampling_frequency
        self.num_spikes =self.analyzer1.sorting.count_num_spikes_per_unit(outputs="dict")

        # spikeinterface handle colors in matplotlib style tuple values in range (0,1)
        self.refresh_colors()


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

    def check_is_view_possible(self, view_name):
        from .viewlist import possible_class_views
        view_class = possible_class_views[view_name]
        if view_class._depend_on is not None:
            depencies_ok = all(self.has_extension(k) for k in view_class._depend_on)
            if not depencies_ok:
                if self.verbose:
                    print(view_name, 'does not have all dependencies', view_class._depend_on)                
                return False
        return True

    def declare_a_view(self, new_view):
        assert new_view not in self.views, 'view already declared {}'.format(self)
        self.views.append(new_view)
        self.signal_handler.connect_view(new_view)
        
    @property
    def channel_ids(self):
        return self.analyzer1.channel_ids

    @property
    def unit_ids1(self):
        return self.unit_ids[:self.analyzer1.get_num_units()]

    @property
    def unit_ids2(self):
        return self.unit_ids[self.analyzer1.get_num_units():]

    def get_original_unit_id(self, unit_id):
        """Get original unit id from analyzer1 or analyzer2 given combined unit_id"""
        unit_index = list(self.unit_ids).index(unit_id)
        if unit_index < self.analyzer1.get_num_units():
            return self.analyzer1.unit_ids[unit_index]
        else:
            return self.analyzer2.unit_ids[unit_index - self.analyzer1.get_num_units()]

    @property
    def unit_ids(self):
        if isinstance(self.analyzer1.unit_ids[0], np.integer) and isinstance(self.analyzer2.unit_ids[0], np.integer):
            return np.concatenate((self.analyzer1.unit_ids, self.analyzer2.unit_ids + max(self.analyzer1.unit_ids) + 1))
        else:
            analyzer1_ids = [str(uid) + f"_{self.analyzer1_name}" for uid in self.analyzer1.unit_ids]
            analyzer2_ids = [str(uid) + f"_{self.analyzer2_name}" for uid in self.analyzer2.unit_ids]
            return np.array(analyzer1_ids + analyzer2_ids)

    def get_time(self):
        """
        Returns selected time and segment index
        """
        segment_index = self.time_info['segment_index']
        time_by_seg = self.time_info['time_by_seg']
        time = time_by_seg[segment_index]
        return time, segment_index

    def set_time(self, time=None, segment_index=None):
        """
        Set selected time and segment index.
        If time is None, then the current time is used.
        If segment_index is None, then the current segment index is used.
        """
        if segment_index is not None:
            self.time_info['segment_index'] = segment_index
        else:
            segment_index = self.time_info['segment_index']
        if time is not None:
            self.time_info['time_by_seg'][segment_index] = time

    def update_time_info(self):
        # set default time info
        if self.main_settings["use_times"] and self.has_extension("recording"):
            time_by_seg=np.array(
                [
                   self.analyzer1.recording.get_start_time(segment_index) for segment_index in range(self.num_segments)
                ],
                dtype="float64"
            )
        else:
            time_by_seg=np.array([0] * self.num_segments, dtype="float64")
        if not hasattr(self, 'time_info'):
            self.time_info = dict(
                time_by_seg=time_by_seg,
                segment_index=0
            )
        else:
            self.time_info['time_by_seg'] = time_by_seg

    def get_t_start_t_stop(self):
        segment_index = self.time_info["segment_index"]
        if self.main_settings["use_times"] and self.has_extension("recording"):
            t_start =self.analyzer1.recording.get_start_time(segment_index=segment_index)
            t_stop =self.analyzer1.recording.get_end_time(segment_index=segment_index)
            return t_start, t_stop
        else:
            return 0, self.get_num_samples(segment_index) / self.sampling_frequency

    def get_times_chunk(self, segment_index, t1, t2):
        ind1, ind2 = self.get_chunk_indices(t1, t2, segment_index)
        if self.main_settings["use_times"]:
            recording =self.analyzer1.recording
            times_chunk = recording.get_times(segment_index=segment_index)[ind1:ind2]
        else:
            times_chunk = np.arange(ind2 - ind1, dtype='float64') / self.sampling_frequency + max(t1, 0)
        return times_chunk

    def get_chunk_indices(self, t1, t2, segment_index):
        if self.main_settings["use_times"]:
            recording =self.analyzer1.recording
            ind1, ind2 = recording.time_to_sample_index([t1, t2], segment_index=segment_index)
        else:
            t_start = 0.0
            sr = self.sampling_frequency
            ind1 = int((t1 - t_start) * sr)
            ind2 = int((t2 - t_start) * sr)

        ind1 = max(0, ind1)
        ind2 = min(self.get_num_samples(segment_index), ind2)
        return ind1, ind2

    def sample_index_to_time(self, sample_index):
        segment_index = self.time_info["segment_index"]
        if self.main_settings["use_times"] and self.has_extension("recording"):
            time =self.analyzer1.recording.sample_index_to_time(sample_index, segment_index=segment_index)
            return time
        else:
            return sample_index / self.sampling_frequency

    def time_to_sample_index(self, time):
        segment_index = self.time_info["segment_index"]
        if self.main_settings["use_times"] and self.has_extension("recording"):
            time =self.analyzer1.recording.time_to_sample_index(time, segment_index=segment_index)
            return time
        else:
            return int(time * self.sampling_frequency)

    def get_information_txt(self):
        nseg =self.analyzer1.get_num_segments()
        nchan =self.analyzer1.get_num_channels()
        nunits = len(self.unit_ids)
        txt = f"{nchan} channels - {nunits} units - {nseg} segments - {self.analyzer1.format}\n"
        txt += f"Loaded {len(self.analyzer1.extensions)} extensions"

        return txt

    def refresh_colors(self):
        if self.backend == "qt":
            self._cached_qcolors = {}
        elif self.backend == "panel":
            pass

        if self.main_settings['color_mode'] == 'color_by_unit':
            self.colors = get_some_colors(self.unit_ids, color_engine='matplotlib', map_name='gist_ncar', 
                                          shuffle=True, seed=42)
        elif  self.main_settings['color_mode'] == 'color_only_visible':
            unit_colors = get_some_colors(self.unit_ids, color_engine='matplotlib', map_name='gist_ncar',
                                          shuffle=True, seed=42)
            self.colors = {unit_id: (0.3, 0.3, 0.3, 1.) for unit_id in self.unit_ids}
            for unit_id in self.get_visible_unit_ids():
                self.colors[unit_id] = unit_colors[unit_id]
        elif  self.main_settings['color_mode'] == 'color_by_visibility':
            self.colors = {unit_id: (0.3, 0.3, 0.3, 1.) for unit_id in self.unit_ids}
            import matplotlib.pyplot as plt
            cmap = plt.colormaps['tab10']
            for i, unit_id in enumerate(self.get_visible_unit_ids()):
                self.colors[unit_id] = cmap(i)


    def get_unit_color(self, unit_id):
        # scalar unit_id -> color html or QtColor
        return self.colors[unit_id]
    
    def get_spike_colors(self, unit_indices):
        # array[unit_ind] ->  array[color html or QtColor]
        colors = np.zeros((unit_indices.size, 4), dtype="uint8")
        unit_inds = np.unique(unit_indices)
        for unit_ind in unit_inds:
            unit_id = self.unit_ids[unit_ind]
            mask = unit_indices == unit_ind
            colors[mask] = np.array(self.get_unit_color(unit_id)) * 255
        return colors

    
    def get_extremum_channel(self, unit_id):
        chan_ind = self._extremum_channel[unit_id]
        return chan_ind
    
    # unit visibility zone
    def set_visible_unit_ids(self, visible_unit_ids):
        """Make visible some units, all other off"""
        lim = self.main_settings['max_visible_units']
        if len(visible_unit_ids) > lim:
            visible_unit_ids = visible_unit_ids[:lim]
        self._visible_unit_ids = list(visible_unit_ids)

    def get_visible_unit_ids(self):
        """Get list of visible unit_ids"""
        return self._visible_unit_ids

    def get_visible_unit_indices(self):
        """Get list of indicies of visible units"""
        unit_ids = list(self.unit_ids)
        visible_unit_indices = [unit_ids.index(u) for u in self._visible_unit_ids]
        return visible_unit_indices

    def set_all_unit_visibility_off(self):
        """As in the name"""
        self._visible_unit_ids = []

    def iter_visible_units(self):
        """For looping over unit_ind and unit_id"""
        visible_unit_indices = self.get_visible_unit_indices()
        visible_unit_ids = self._visible_unit_ids
        return zip(visible_unit_indices, visible_unit_ids)
    
    def set_unit_visibility(self, unit_id, state):
        """Change the visibility of on unit, other are unchanged"""
        if state and not(unit_id in self._visible_unit_ids):
            self._visible_unit_ids.append(unit_id)
        elif not state and unit_id in self._visible_unit_ids:
            self._visible_unit_ids.remove(unit_id)
    
    def get_unit_visibility(self, unit_id):
        """Get thethe visibility of on unit"""
        return unit_id in self._visible_unit_ids

    def get_units_visibility_mask(self):
        """Get bool mask of visibility"""
        mask = np.zeros(self.unit_ids.size, dtype='bool')
        mask[self.get_visible_unit_indices()] = True
        return mask
    
    def get_dict_unit_visible(self):
        """Construct the visibility dict keys are unit_ids, previous behavior"""
        dict_unit_visible = {u:False for u in self.unit_ids}
        for u in self.get_visible_unit_ids():
            dict_unit_visible[u] = True
        return dict_unit_visible
    ## end unit visibility zone

    def update_visible_spikes(self):
        inds = []
        for unit_index, unit_id in self.iter_visible_units():
            inds.append(self._spike_index_by_units[unit_id])
        
        if len(inds) > 0:
            inds = np.concatenate(inds)
            inds = np.sort(inds)
        else:
            inds = np.array([], dtype='int64')
        self._spike_visible_indices = inds
        
        self._spike_selected_indices = np.array([], dtype='int64')
    
    def get_indices_spike_visible(self):
        return self._spike_visible_indices

    def get_indices_spike_selected(self):
        return self._spike_selected_indices

    def set_indices_spike_selected(self, inds):
        self._spike_selected_indices = np.array(inds)
        # reset active split if needed
        if len(self._spike_selected_indices) == 1:
            # set time info 
            segment_index = self.spikes['segment_index'][self._spike_selected_indices[0]]
            sample_index = self.spikes['sample_index'][self._spike_selected_indices[0]]
            self.set_time(time=self.sample_index_to_time(sample_index), segment_index=segment_index)

    def get_spike_indices(self, unit_id, segment_index=None):
        if segment_index is None:
            # dict[unit_id] -> all indices for this unit across segments
            return self._spike_index_by_units[unit_id]
        else:
            # dict[segment_index][unit_id] -> all indices for this unit for one segment
            return self._spike_index_by_segment_and_units[segment_index][unit_id]

    def get_num_samples(self, segment_index):
        return self.analyzer1.get_num_samples(segment_index=segment_index)
    
    def get_traces(self, trace_source='preprocessed', **kargs):
        # assert trace_source in ['preprocessed', 'raw']
        assert trace_source in ['preprocessed']

        cache_key = (kargs.get("segment_index", None), kargs.get("start_frame", None), kargs.get("end_frame", None))
        if cache_key in self._traces_cached:
            return self._traces_cached[cache_key]
        else:
            # check if start_frame and end_frame are a subset interval of a cached one
            for cached_key in self._traces_cached.keys():
                cached_seg = cached_key[0]
                cached_start = cached_key[1]
                cached_end = cached_key[2]
                req_seg = kargs.get("segment_index", None)
                req_start = kargs.get("start_frame", None)
                req_end = kargs.get("end_frame", None)
                if cached_seg is not None and req_seg is not None:
                    if cached_seg != req_seg:
                        continue
                if cached_start is not None and cached_end is not None and req_start is not None and req_end is not None:
                    if req_start >= cached_start and req_end <= cached_end:
                        # subset found
                        traces = self._traces_cached[cached_key]
                        start_offset = req_start - cached_start
                        end_offset = req_end - cached_start
                        return traces[start_offset:end_offset, :]
        
        if len(self._traces_cached) > 4:
            self._traces_cached.pop(list(self._traces_cached.keys())[0])
        
        if trace_source == 'preprocessed':
            rec = self.analyzer1.recording
        elif trace_source == 'raw':
            raise NotImplementedError("Raw traces not implemented yet")
            # TODO get with parent recording the non process recording
        kargs['return_in_uV'] = self.return_in_uV
        traces = rec.get_traces(**kargs)
        # put in cache for next call
        self._traces_cached[cache_key] = traces
        return traces
    
    def get_contact_location(self):
        location = self.analyzer1.get_channel_locations()
        return location
    
    def get_waveform_sweep(self):
        return self.nbefore, self.nafter
        
    def get_waveforms_range(self):
        return np.nanmin(self.templates_average), np.nanmax(self.templates_average)
    
    def get_waveforms(self, unit_id, force_dense=False):
        if unit_id in self.unit_ids1:
            self.waveforms_ext = self.waveforms_ext1
            analyzer = self.analyzer1
        original_unit_id = self.get_original_unit_id(unit_id)
        wfs = self.waveforms_ext.get_waveforms_one_unit(original_unit_id, force_dense=force_dense)
        if analyzer.sparsity is None or force_dense:
            # dense waveforms
            chan_inds = np.arange(analyzer.get_num_channels(), dtype='int64')
        else:
            # sparse waveforms
            chan_inds = analyzer.sparsity.unit_id_to_channel_indices[unit_id]
        return wfs, chan_inds

    def get_common_sparse_channels(self, unit_ids):
        sparsity_mask = self.get_sparsity_mask()
        unit_indexes = [list(self.unit_ids).index(u) for u in unit_ids]
        chan_inds, = np.nonzero(sparsity_mask[unit_indexes, :].sum(axis=0))
        return chan_inds
    
    def get_intersect_sparse_channels(self, unit_ids):
        sparsity_mask = self.get_sparsity_mask()
        unit_indexes = [list(self.unit_ids).index(u) for u in unit_ids]
        chan_inds, = np.nonzero(sparsity_mask[unit_indexes, :].sum(axis=0) == len(unit_ids))
        return chan_inds
    
    def get_probegroup(self):
        return self.analyzer1.get_probegroup()

    def set_channel_visibility(self, visible_channel_inds):
        self.visible_channel_inds = np.array(visible_channel_inds, copy=True)

    def has_extension(self, extension_name):
        if extension_name == 'recording':
            return self.use_recordings
        elif extension_name == 'comparison':
            return True
        else:
            # extension needs to be loaded
            if extension_name in self.skip_extensions:
                return False
            else:
                return extension_name in self.analyzer1.extensions

    def handle_metrics(self):
        return self.metrics is not None

    def get_units_table(self):
        return self.units_table

    # TODO
    def get_all_pcs(self):
        return None, None
        # if self._pc_projections is None and (self.pc_ext1 is not None and self.pc_ext2 is not None):
        #     pc_indices = 
        #     for analyzer, pc_ext in zip([self.analyzer1, self.analyzer2], [self.pc_ext1, self.pc_ext2]):
        #         # make sure pcs are computed
        #         if pc_ext.get_data() is None:
        #             analyzer.compute_one_extension('principal_components', save=self.save_on_compute)
        #     self._pc_projections, self._pc_indices = self.pc_ext1.get_some_projections(
        #         channel_ids=self.analyzer1.channel_ids,
        #         unit_ids=self.analyzer1.unit_ids
        #     )

        #     return self._pc_indices, self._pc_projections
        # else:
        #     return None, None

    def get_sparsity_mask(self):
        if self.external_sparsity1 is not None:
            return np.vstack([self.external_sparsity1.mask, self.external_sparsity2.mask])
        else:
            return np.vstack([self.analyzer_sparsity1.mask, self.analyzer_sparsity2.mask])

    def get_similarity(self, method=None):
        if method is None and len(self._similarity_by_method) == 1:
            method = list(self._similarity_by_method.keys())[0]
        similarity = self._similarity_by_method.get(method, None)
        return similarity
    
    def compute_similarity(self, method='l1'):
        # have internal cache
        if method in self._similarity_by_method:
            return self._similarity_by_method[method]
        ext = self.analyzer.compute("template_similarity", method=method, save=self.save_on_compute)
        self._similarity_by_method[method] = ext.get_data()
        return self._similarity_by_method[method]

    def compute_unit_positions(self, method, method_kwargs):
        unit_positions = np.zeros((len(self.unit_ids), 2), dtype='float32')
        for analyzer in [self.analyzer1, self.analyzer2]:
            ext = analyzer.get_extension('unit_locations')
            ext = analyzer.compute_one_extension('unit_locations', save=self.save_on_compute, method=method, **method_kwargs)
            unit_positions[:len(analyzer.unit_ids), :] = ext.get_data()[:, :2]
        self.unit_positions = unit_positions

    # def get_correlograms(self):
    #     return self.correlograms, self.correlograms_bins

    # def compute_correlograms(self, window_ms, bin_ms):
    #     ext = self.analyzer.compute("correlograms", save=self.save_on_compute, window_ms=window_ms, bin_ms=bin_ms)
    #     self.correlograms, self.correlograms_bins = ext.get_data()
    #     return self.correlograms, self.correlograms_bins
    
    # def get_isi_histograms(self):
    #     return self.isi_histograms, self.isi_bins

    # def compute_isi_histograms(self, window_ms, bin_ms):
    #     ext = self.analyzer.compute("isi_histograms", save=self.save_on_compute, window_ms=window_ms, bin_ms=bin_ms)
    #     self.isi_histograms, self.isi_bins = ext.get_data()
    #     return self.isi_histograms, self.isi_bins

    def get_units_table(self):
        return self.units_table

    def get_split_unit_ids(self):
        return []
