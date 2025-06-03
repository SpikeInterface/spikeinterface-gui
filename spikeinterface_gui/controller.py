import time

import numpy as np

import json


from spikeinterface.widgets.utils import get_unit_colors
from spikeinterface import compute_sparsity
from spikeinterface.core import get_template_extremum_channel
import spikeinterface.postprocessing
import spikeinterface.qualitymetrics
from spikeinterface.core.sorting_tools import spike_vector_to_indices
from spikeinterface.core.core_tools import check_json
from spikeinterface.widgets.utils import make_units_table_from_analyzer

from .curation_tools import adding_group, default_label_definitions, empty_curation_data

spike_dtype =[('sample_index', 'int64'), ('unit_index', 'int64'), 
    ('channel_index', 'int64'), ('segment_index', 'int64'),
    ('visible', 'bool'), ('selected', 'bool'), ('rand_selected', 'bool')]


_default_main_settings = dict(
    max_visible_units=10,
    color_mode='color_by_unit',
)

# TODO handle return_scaled
from spikeinterface.widgets.sorting_summary import _default_displayed_unit_properties


class Controller():
    def __init__(self, analyzer=None, backend="qt", parent=None, verbose=False, save_on_compute=False,
                 curation=False, curation_data=None, label_definitions=None, with_traces=True,
                 displayed_unit_properties=None,
                 extra_unit_properties=None, skip_extensions=None):
        
        self.views = []
        skip_extensions = skip_extensions if skip_extensions is not None else []
        self.skip_extensions = skip_extensions
        self.backend = backend
        if self.backend == "qt":
            from .backend_qt import SignalHandler
            self.signal_handler = SignalHandler(self, parent=parent)

        elif self.backend == "panel":
            from .backend_panel import SignalHandler
            self.signal_handler = SignalHandler(self, parent=parent)

        self.with_traces = with_traces

        self.analyzer = analyzer
        assert self.analyzer.get_extension("random_spikes") is not None
        
        self.return_scaled = True
        self.save_on_compute = save_on_compute

        self.verbose = verbose
        t0 = time.perf_counter()


        self.main_settings = _default_main_settings.copy()



        self.num_channels = self.analyzer.get_num_channels()
        # this now private and shoudl be acess using function
        self._visible_unit_ids = [self.unit_ids[0]]

        # sparsity
        if self.analyzer.sparsity is None:
            self.external_sparsity = compute_sparsity(self.analyzer, method="radius",radius_um=90.)
            self.analyzer_sparsity = None
        else:
            self.external_sparsity = None
            self.analyzer_sparsity = self.analyzer.sparsity

        # Mandatory extensions: computation forced
        if verbose:
            print('\tLoading templates')
        temp_ext = self.analyzer.get_extension("templates")
        if temp_ext is None:
            temp_ext = self.analyzer.compute_one_extension("templates")
        self.nbefore, self.nafter = temp_ext.nbefore, temp_ext.nafter

        self.templates_average = temp_ext.get_templates(operator='average')
        self.templates_std = temp_ext.get_templates(operator='std')

        if verbose:
            print('\tLoading unit_locations')
        ext = analyzer.get_extension('unit_locations')
        if ext is None:
            print('Force compute "unit_locations" is needed')
            ext = analyzer.compute_one_extension('unit_locations')
        # only 2D
        self.unit_positions = ext.get_data()[:, :2]

        # Optional extensions : can be None or skipped
        if verbose:
            print('\tLoading noise_levels')
        ext = analyzer.get_extension('noise_levels')
        if ext is None and self.has_extension('recording'):
            print('Force compute "noise_levels" is needed')
            ext = analyzer.compute_one_extension('noise_levels')
        self.noise_levels = ext.get_data() if ext is not None else None

        if "quality_metrics" in skip_extensions:
            if self.verbose:
                print('\tSkipping quality_metrics')
            self.metrics = None
        else:
            if verbose:
                print('\tLoading quality_metrics')
            qm_ext = analyzer.get_extension('quality_metrics')
            if qm_ext is not None:
                self.metrics = qm_ext.get_data()
            else:
                self.metrics = None

        if "spike_amplitudes" in skip_extensions:
            if self.verbose:
                print('\tSkipping spike_amplitudes')
            self.spike_amplitudes = None
        else:
            if verbose:
                print('\tLoading spike_amplitudes')
            sa_ext = analyzer.get_extension('spike_amplitudes')
            if sa_ext is not None:
                self.spike_amplitudes = sa_ext.get_data()
            else:
                self.spike_amplitudes = None

        if "spike_locations" in skip_extensions:
            if self.verbose:
                print('\tSkipping spike_locations')
            self.spike_depths = None
        else:
            if verbose:
                print('\tLoading spike_locations')
            sl_ext = analyzer.get_extension('spike_locations')
            if sl_ext is not None:
                self.spike_depths = sl_ext.get_data()["y"]
            else:
                self.spike_depths = None

        if "correlograms" in skip_extensions:
            if self.verbose:
                print('\tSkipping correlograms')
            self.correlograms = None
            self.correlograms_bins = None
        else:
            if verbose:
                print('\tLoading correlograms')
            ccg_ext = analyzer.get_extension('correlograms')
            if ccg_ext is not None:
                self.correlograms, self.correlograms_bins = ccg_ext.get_data()
            else:
                self.correlograms, self.correlograms_bins = None, None

        if "isi_histograms" in skip_extensions:
            if self.verbose:
                print('\tSkipping isi_histograms')
            self.isi_histograms = None
            self.isi_bins = None
        else:
            if verbose:
                print('\tLoading isi_histograms')
            isi_ext = analyzer.get_extension('isi_histograms')
            if isi_ext is not None:
                self.isi_histograms, self.isi_bins = isi_ext.get_data()
            else:
                self.isi_histograms, self.isi_bins = None, None

        self._similarity_by_method = {}
        if "template_similarity" in skip_extensions:
            if self.verbose:
                print('\tSkipping template_similarity')
        else:
            if verbose:
                print('\tLoading template_similarity')
            ts_ext = analyzer.get_extension('template_similarity')
            if ts_ext is not None:
                method = ts_ext.params["method"]
                self._similarity_by_method[method] = ts_ext.get_data()
            else:
                if len(self.unit_ids) <= 64 and len(self.channel_ids) <= 64:
                    # precompute similarity when low channel/units count
                    method = 'l1'
                    ts_ext = analyzer.compute_one_extension('template_similarity', method=method, save=save_on_compute)
                self._similarity_by_method[method] = ts_ext.get_data()

        if "waveforms" in skip_extensions:
            if self.verbose:
                print('\tSkipping waveforms')
            self.waveforms_ext = None
        else:
            if verbose:
                print('\tLoading waveforms')
            wf_ext = analyzer.get_extension('waveforms')
            if wf_ext is not None:
                self.waveforms_ext = wf_ext
            else:
                self.waveforms_ext = None
        self._pc_projections = None
        if "principal_components" in skip_extensions:
            if self.verbose:
                print('\tSkipping principal_components')
            self.pc_ext = None
        else:
            if verbose:
                print('\tLoading principal_components')
            pc_ext = analyzer.get_extension('principal_components')
            self.pc_ext = pc_ext

        self._potential_merges = None

        t1 = time.perf_counter()
        if verbose:
            print('Loading extensions took', t1 - t0)

        t0 = time.perf_counter()

        self._extremum_channel = get_template_extremum_channel(self.analyzer, peak_sign='neg', outputs='index')

        # some direct attribute
        self.num_segments = self.analyzer.get_num_segments()
        self.sampling_frequency = self.analyzer.sampling_frequency

        # spikeinterface handle colors in matplotlib style tuple values in range (0,1)
        self.refresh_colors()

        # at init, we set the visible channels as the sparsity of the first unit
        self.visible_channel_inds = self.analyzer_sparsity.unit_id_to_channel_indices[self.unit_ids[0]].astype("int64")

        t0 = time.perf_counter()
        
        # make internal spike vector
        unit_ids = self.analyzer.unit_ids
        num_seg = self.analyzer.get_num_segments()
        self.num_spikes = self.analyzer.sorting.count_num_spikes_per_unit(outputs="dict")
        # print("self.num_spikes", self.num_spikes)

        spike_vector = self.analyzer.sorting.to_spike_vector(concatenated=True, extremum_channel_inds=self._extremum_channel)
        # spike_vector = self.analyzer.sorting.to_spike_vector(concatenated=True)
        
        self.random_spikes_indices = self.analyzer.get_extension("random_spikes").get_data()

        self.spikes = np.zeros(spike_vector.size, dtype=spike_dtype)        
        self.spikes['sample_index'] = spike_vector['sample_index']
        self.spikes['unit_index'] = spike_vector['unit_index']
        self.spikes['segment_index'] = spike_vector['segment_index']
        self.spikes['channel_index'] = spike_vector['channel_index']
        self.spikes['rand_selected'][:] = False
        self.spikes['rand_selected'][self.random_spikes_indices] = True

        # self.num_spikes = self.analyzer.sorting.count_num_spikes_per_unit(outputs="dict")
        seg_limits = np.searchsorted(self.spikes["segment_index"], np.arange(num_seg + 1))
        self.segment_slices = {seg_index: slice(seg_limits[seg_index], seg_limits[seg_index + 1]) for seg_index in range(num_seg)}
        
        spike_vector2 = self.analyzer.sorting.to_spike_vector(concatenated=False)
        # this is dict of list because per segment spike_indices[segment_index][unit_id]
        spike_indices = spike_vector_to_indices(spike_vector2, unit_ids)
        # this is flatten
        spike_per_seg = [s.size for s in spike_vector2]
        # dict[unit_id] -> all indices for this unit across segments
        self._spike_index_by_units = {}
        # dict[seg_index][unit_id] -> all indices for this unit for one segment
        self._spike_index_by_segment_and_units = spike_indices
        for unit_id in unit_ids:
            inds = []
            for seg_ind in range(num_seg):
                inds.append(spike_indices[seg_ind][unit_id] + int(np.sum(spike_per_seg[:seg_ind])))
            self._spike_index_by_units[unit_id] = np.concatenate(inds)

        t1 = time.perf_counter()
        if verbose:
            print('Gathering all spikes took', t1 - t0)

        self._spike_visible_indices = np.array([], dtype='int64')
        self._spike_selected_indices = np.array([], dtype='int64')
        self.update_visible_spikes()

        self._traces_cached = {}

        self.units_table = make_units_table_from_analyzer(analyzer, extra_properties=extra_unit_properties)
        if displayed_unit_properties is None:
            displayed_unit_properties = list(_default_displayed_unit_properties)
        if extra_unit_properties is not None:
            displayed_unit_properties += list(extra_unit_properties.keys())
        displayed_unit_properties = [v for v in displayed_unit_properties if v in self.units_table.columns]
        self.displayed_unit_properties = displayed_unit_properties

        # set default time info
        self.time_info = dict(
            time_by_seg=np.array([0] * self.num_segments, dtype="float64"),
            segment_index=0
        )

        self.curation = curation
        # TODO: Reload the dictionary if it already exists
        if self.curation:
            # rules:
            #  * if curation_data already exists in folder, then it is reloaded and has precedance
            #  * if not, then use curation_data argument input
            #  * otherwise create an empty one

            if self.analyzer.format == "binary_folder":
                json_file = self.analyzer.folder / "spikeinterface_gui" / "curation_data.json"
                if json_file.exists():
                    with open(json_file, "r") as f:
                        curation_data = json.load(f)
            elif self.analyzer.format == "zarr":
                import zarr
                zarr_root = zarr.open(self.analyzer.folder, mode='r')
                if "spikeinterface_gui" in zarr_root.keys() and "curation_data" in zarr_root["spikeinterface_gui"].attrs.keys():
                    curation_data = zarr_root["spikeinterface_gui"].attrs["curation_data"]

            if curation_data is None:
                self.curation_data = empty_curation_data.copy()
            else:
                self.curation_data = curation_data

            self.has_default_quality_labels = False
            if "label_definitions" not in self.curation_data:
                if label_definitions is not None:
                    self.curation_data["label_definitions"] = label_definitions
                else:
                    self.curation_data["label_definitions"] = default_label_definitions.copy()

            if "quality" in self.curation_data["label_definitions"]:
                curation_dict_quality_labels = self.curation_data["label_definitions"]["quality"]["label_options"]
                default_quality_labels = default_label_definitions["quality"]["label_options"]

                if set(curation_dict_quality_labels) == set(default_quality_labels):
                    if self.verbose:
                        print('Curation quality labels are the default ones')
                    self.has_default_quality_labels = True


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
        return self.analyzer.channel_ids

    @property
    def unit_ids(self):
        return self.analyzer.unit_ids

    def get_time(self):
        """
        Returns selected time and segment index
        """
        seg_index = self.time_info['segment_index']
        time_by_seg = self.time_info['time_by_seg']
        time = time_by_seg[seg_index]
        return time, seg_index

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
    
    def get_information_txt(self):
        nseg = self.analyzer.get_num_segments()
        nchan = self.analyzer.get_num_channels()
        nunits = self.analyzer.get_num_units()
        txt = f"{nchan} channels - {nunits} units - {nseg} segments - {self.analyzer.format}\n"
        txt += f"Loaded {len(self.analyzer.extensions)} extensions"

        return txt

    def refresh_colors(self):
        if self.backend == "qt":
            self._cached_qcolors = {}
        elif self.backend == "panel":
            pass

        if self.main_settings['color_mode'] == 'color_by_unit':
            self.colors = get_unit_colors(self.analyzer.sorting, color_engine='matplotlib', map_name='gist_ncar', 
                                        shuffle=True, seed=42)
        elif  self.main_settings['color_mode'] == 'color_only_visible':
            unit_colors = get_unit_colors(self.analyzer.sorting, color_engine='matplotlib', map_name='gist_ncar', 
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

    def get_spike_indices(self, unit_id, seg_index=None):
        if seg_index is None:
            # dict[unit_id] -> all indices for this unit across segments
            return self._spike_index_by_units[unit_id]
        else:
            # dict[seg_index][unit_id] -> all indices for this unit for one segment
            return self._spike_index_by_segment_and_units[seg_index][unit_id]

    def get_num_samples(self, segment_index):
        return self.analyzer.get_num_samples(segment_index=segment_index)
    
    def get_traces(self, trace_source='preprocessed', **kargs):
        # assert trace_source in ['preprocessed', 'raw']
        assert trace_source in ['preprocessed']

        cache_key = (kargs.get("segment_index", None), kargs.get("start_frame", None), kargs.get("end_frame", None))
        if cache_key in self._traces_cached:
            return self._traces_cached[cache_key]
        
        if len(self._traces_cached) > 4:
            self._traces_cached.pop(list(self._traces_cached.keys())[0])
        
        if trace_source == 'preprocessed':
            rec = self.analyzer.recording
        elif trace_source == 'raw':
            raise NotImplemented
            # TODO get with parent recording the non process recording
        kargs['return_scaled'] = self.return_scaled
        traces = rec.get_traces(**kargs)
        # put in cache for next call
        self._traces_cached[cache_key] = traces
        return traces
    
    def get_contact_location(self):
        location = self.analyzer.get_channel_locations()
        return location
    
    def get_waveform_sweep(self):
        return self.nbefore, self.nafter
        
    def get_waveforms_range(self):
        return np.nanmin(self.templates_average), np.nanmax(self.templates_average)
    
    def get_waveforms(self, unit_id):
        wfs = self.waveforms_ext.get_waveforms_one_unit(unit_id, force_dense=False)
        if self.analyzer.sparsity is None:
            # dense waveforms
            chan_inds = np.arange(self.analyzer.recording.get_num_channels(), dtype='int64')
        else:
            # sparse waveforms
            chan_inds = self.analyzer.sparsity.unit_id_to_channel_indices[unit_id]
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
        return self.analyzer.get_probegroup()

    def set_channel_visibility(self, visible_channel_inds):
        self.visible_channel_inds = np.array(visible_channel_inds, copy=True)

    def has_extension(self, extension_name):
        if extension_name == 'recording':
            return self.analyzer.has_recording() or self.analyzer.has_temporary_recording()
        else:
            # extension needs to be loaded
            if extension_name in self.skip_extensions:
                return False
            else:
                return extension_name in self.analyzer.extensions

    def handle_metrics(self):
        return self.metrics is not None

    def get_all_pcs(self):

        if self._pc_projections is None and self.pc_ext is not None:
            self._pc_projections, self._pc_indices = self.pc_ext.get_some_projections(
                channel_ids=self.analyzer.channel_ids,
                unit_ids=self.analyzer.unit_ids
            )

            return self._pc_indices, self._pc_projections
        else:
            return None, None

    def get_sparsity_mask(self):
        if self.external_sparsity is not None:
            return self.external_sparsity.mask
        else:
            return self.analyzer_sparsity.mask

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
        ext = self.analyzer.compute_one_extension('unit_locations', save=self.save_on_compute, method=method, **method_kwargs)
        # 2D only
        self.unit_positions = ext.get_data()[:, :2]

    def get_correlograms(self):
        return self.correlograms, self.correlograms_bins

    def compute_correlograms(self, window_ms, bin_ms):
        ext = self.analyzer.compute("correlograms", save=self.save_on_compute, window_ms=window_ms, bin_ms=bin_ms)
        self.correlograms, self.correlograms_bins = ext.get_data()
        return self.correlograms, self.correlograms_bins
    
    def get_isi_histograms(self):
        return self.isi_histograms, self.isi_bins

    def compute_isi_histograms(self, window_ms, bin_ms):
        ext = self.analyzer.compute("isi_histograms", save=self.save_on_compute, window_ms=window_ms, bin_ms=bin_ms)
        self.isi_histograms, self.isi_bins = ext.get_data()
        return self.isi_histograms, self.isi_bins

    def get_units_table(self):
        return self.units_table

    def compute_auto_merge(self, **params):
        
        from spikeinterface.curation import compute_merge_unit_groups

        merge_unit_groups, extra = compute_merge_unit_groups(
            self.analyzer,
            extra_outputs=True,
            resolve_graph=False
        )

        return merge_unit_groups, extra
    
    def curation_can_be_saved(self):
        return self.analyzer.format != "memory"

    def construct_final_curation(self):
        d = dict()
        d["format_version"] = "1"
        d["unit_ids"] = self.unit_ids.tolist()
        d.update(self.curation_data.copy())
        return d

    def save_curation_in_analyzer(self):
        if self.analyzer.format == "memory":
            pass
        elif self.analyzer.format == "binary_folder":
            folder = self.analyzer.folder / "spikeinterface_gui"
            folder.mkdir(exist_ok=True, parents=True)
            json_file = folder / f"curation_data.json"
            with json_file.open("w") as f:
                json.dump(check_json(self.construct_final_curation()), f, indent=4)
        elif self.analyzer.format == "zarr":
            import zarr
            zarr_root = zarr.open(self.analyzer.folder, mode='r+')
            if "spikeinterface_gui" not in zarr_root.keys():
                sigui_group = zarr_root.create_group("spikeinterface_gui", overwrite=True)
            sigui_group = zarr_root["spikeinterface_gui"]
            sigui_group.attrs["curation_data"] = check_json(self.construct_final_curation())

    def make_manual_delete_if_possible(self, removed_unit_ids):
        """
        Check if a unit_ids can be removed.

        If unit are already deleted or in a merge group then the delete operation is skipped.
        """
        if not self.curation:
            return

        all_merged_units = sum(self.curation_data["merge_unit_groups"], [])
        for unit_id in removed_unit_ids:
            if unit_id in self.curation_data["removed_units"]:
                continue
            # TODO: check if unit is already in a merge group
            if unit_id in all_merged_units:
                continue
            self.curation_data["removed_units"].append(unit_id)
            if self.verbose:
                print(f"Unit {unit_id} is removed from the curation data")
    
    def make_manual_restore(self, restore_unit_ids):
        """
        pop unit_ids from the removed_units list which is a restore.
        """
        if not self.curation:
            return

        for unit_id in restore_unit_ids:
            if unit_id in self.curation_data["removed_units"]:
                if self.verbose:
                    print(f"Unit {unit_id} is restored from the curation data")
                self.curation_data["removed_units"].remove(unit_id)

    def make_manual_merge_if_possible(self, merge_unit_ids):
        """
        Check if the a list of unit_ids can be added as a new merge to the curation_data.

        If some unit_ids are already in the removed list then the merge is skipped.

        If unit_ids are already is some other merge then the connectivity graph is resolved groups can be
        eventually merged.

        """
        if not self.curation:
            return False

        if len(merge_unit_ids) < 2:
            return False

        for unit_id in merge_unit_ids:
            if unit_id in self.curation_data["removed_units"]:
                return False
        merged_groups = adding_group(self.curation_data["merge_unit_groups"], merge_unit_ids)
        self.curation_data["merge_unit_groups"] = merged_groups
        if self.verbose:
            print(f"Merged unit group: {merge_unit_ids}")
        return True
    
    def make_manual_restore_merge(self, merge_group_indices):
        if not self.curation:
            return
        merge_groups_to_remove = [self.curation_data["merge_unit_groups"][merge_group_index] for merge_group_index in merge_group_indices]
        for merge_group in merge_groups_to_remove:
            if self.verbose:
                print(f"Unmerged merge group {merge_group}")
            self.curation_data["merge_unit_groups"].remove(merge_group)

    def get_curation_label_definitions(self):
        # give only label definition with exclusive
        label_definitions = {}
        for k, lbl_def in self.curation_data["label_definitions"].items():
            if lbl_def['exclusive']:
                label_definitions[k] = lbl_def.copy()
        return label_definitions

    def find_unit_in_manual_labels(self, unit_id):
        for ix, lbl in enumerate(self.curation_data["manual_labels"]):
            if lbl["unit_id"] == unit_id:
                    return ix

    def get_unit_label(self, unit_id, category):
        ix = self.find_unit_in_manual_labels(unit_id)
        if ix is None:
            return
        lbl = self.curation_data["manual_labels"][ix]
        if category in lbl:
            labels = lbl[category]
            return labels[0]

    def set_label_to_unit(self, unit_id, category, label):
        if label is None:
            self.remove_category_from_unit(unit_id, category)
            return

        ix = self.find_unit_in_manual_labels(unit_id)
        if ix is not None:
            lbl = self.curation_data["manual_labels"][ix]
            if category in lbl:
                lbl[category] = [label]
            else:
                lbl[category] = [label]
        else:
            lbl = {"unit_id": unit_id, category:[label]}
            self.curation_data["manual_labels"].append(lbl)
        if self.verbose:
            print(f"Set label {category} to {label} for unit {unit_id}")

    def remove_category_from_unit(self, unit_id, category):
        ix = self.find_unit_in_manual_labels(unit_id)
        if ix is None:
            return
        lbl = self.curation_data["manual_labels"][ix]
        if category in lbl:
            lbl.pop(category)
            if len(lbl) == 1:
                # only unit_id in keys then no more labels, then remove then entry
                self.curation_data["manual_labels"].pop(ix)
                if self.verbose:
                    print(f"Remove label {category} for unit {unit_id}")
