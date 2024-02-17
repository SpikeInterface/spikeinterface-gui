import time

from .base import ControllerBase
from .myqt import QT

from spikeinterface.widgets.utils import get_unit_colors
from spikeinterface import compute_sparsity
from spikeinterface.core import get_template_extremum_channel
import spikeinterface.postprocessing
import spikeinterface.qualitymetrics
from spikeinterface.core.sorting_tools import spike_vector_to_indices

import numpy as np

spike_dtype =[('sample_index', 'int64'), ('unit_index', 'int64'), 
    ('channel_index', 'int64'), ('segment_index', 'int64'),
    ('visible', 'bool'), ('selected', 'bool'), ('included_in_pc', 'bool')]



# TODO spike_amplitudes data
# TODOmak compute more general case:
#    similarity
#    correlogram
#    unit_locations
#    isi_histograms
# TODO handle save=False for extension
# TODO handle recordingless
# TODO handle return_scaled


class  SpikeinterfaceController(ControllerBase):
    def __init__(self, analyzer=None,parent=None, verbose=False):
        ControllerBase.__init__(self, parent=parent)
        
        self.analyzer = analyzer
        assert self.analyzer.random_spikes_indices is not None
        
        self.return_scaled = True        

        if verbose:
            t0 = time.perf_counter()
            print('open/compute extensions')

        # sparsity
        if self.analyzer.sparsity is None:
            self.external_sparsity = compute_sparsity(self.analyzer, method="radius",radius_um=90.)
            self.analyzer_sparsity = None
        else:
            self.external_sparsity = None
            self.analyzer_sparsity = self.analyzer.sparsity


        # Mandatory extensions : computation forced            
        wf_ext = self.analyzer.get_extension('waveforms')
        if wf_ext is None:
           wf_ext = analyzer.compute_one_extension('waveforms')
        self.waveforms_ext = wf_ext
            
        ext = analyzer.get_extension('noise_levels')
        if ext is None:
            print('Force compute "noise_levels" is needed')
            ext = analyzer.compute_one_extension('noise_levels')
        self.noise_levels = ext.get_data()

        temp_ext = self.analyzer.get_extension("templates")
        if temp_ext is None:
            temp_ext = self.analyzer.compute_one_extension("templates")
        self.nbefore, self.nafter = temp_ext.nbefore, temp_ext.nafter

        self.templates_average = temp_ext.get_templates(operator='average')
        self.templates_std = temp_ext.get_templates(operator='std')

        ext = analyzer.get_extension('unit_locations')
        if ext is None:
            print('Force compute "unit_locations" is needed')
            ext = analyzer.compute_one_extension('unit_locations')
        # only 2D
        self.unit_positions = ext.get_data()[:, :2]

        # Non mandatory extensions :  can be None
        self.pc_ext = analyzer.get_extension('principal_components')
        self._pc_projections = None

        qm_ext = analyzer.get_extension('quality_metrics')
        if qm_ext is not None:
            self.metrics = qm_ext.get_data()
        else:
            self.metrics = None

        sa_ext = analyzer.get_extension('spike_amplitudes')
        if sa_ext is not None:
            self.spike_amplitudes = sa_ext.get_data()
        else:
            self.spike_amplitudes = None

        ccg_ext = analyzer.get_extension('correlograms')
        if ccg_ext is not None:
            self.correlograms, self.correlograms_bins = ccg_ext.get_data()
        else:
            self.correlograms, self.correlograms_bins = None, None

        isi_ext = analyzer.get_extension('isi_histograms')
        if isi_ext is not None:
            self.isi_histograms, self.isi_bins = isi_ext.get_data()
        else:
            self.isi_histograms, self.isi_bins = None, None

        self._similarity_by_method = {}
        ts_ext = analyzer.get_extension('template_similarity')
        if ts_ext is not None:
            method = ts_ext.params["method"]
            self._similarity_by_method[method] = ts_ext.get_data()
        else:
            if len(self.unit_ids) <= 64 and len(self.channel_ids) <= 64:
                # precompute similarity when low channel/units count
                method = 'cosine_similarity'
                ts_ext = analyzer.compute_one_extension('template_similarity', method=method)
                self._similarity_by_method[method] = ts_ext.get_data()


        if verbose:
            t1 = time.perf_counter()
            print('open extensions', t1 - t0)

            t0 = time.perf_counter()

        self._extremum_channel = get_template_extremum_channel(self.analyzer, peak_sign='neg', outputs='index')

        # some direct attribute
        self.num_segments = self.analyzer.recording.get_num_segments()
        self.sampling_frequency = self.analyzer.recording.get_sampling_frequency()


        self.colors = get_unit_colors(self.analyzer.sorting, color_engine='matplotlib', map_name='gist_ncar', 
                                      shuffle=True, seed=42)
        self.qcolors = {}
        for unit_id, color in self.colors.items():
            r, g, b, a = color
            self.qcolors[unit_id] = QT.QColor(int(r*255), int(g*255), int(b*255))

        self.unit_visible_dict = {unit_id:False for unit_id in self.unit_ids}
        self.unit_visible_dict[self.unit_ids[0]] = True
        

        if verbose:
            t0 = time.perf_counter()
            print('Gather all spikes')
        
        
        
        # make internal spike vector
        unit_ids = self.analyzer.unit_ids
        num_seg = self.analyzer.get_num_segments()
        self.num_spikes = self.analyzer.sorting.count_num_spikes_per_unit(outputs="dict")

        spike_vector = self.analyzer.sorting.to_spike_vector(concatenated=True, extremum_channel_inds=self._extremum_channel)
        
        self.spikes = np.zeros(spike_vector.size, dtype=spike_dtype)        
        self.spikes['sample_index'] = spike_vector['sample_index']
        self.spikes['unit_index'] = spike_vector['unit_index']
        self.spikes['segment_index'] = spike_vector['segment_index']
        self.spikes['channel_index'] = spike_vector['channel_index']
        self.spikes['included_in_pc'][:] = False
        self.spikes['included_in_pc'][self.analyzer.random_spikes_indices] = True

        self.num_spikes = self.analyzer.sorting.count_num_spikes_per_unit(outputs="dict")
        seg_limits = np.searchsorted(self.spikes["segment_index"], np.arange(num_seg + 1))
        self.segment_slices = {seg_index: slice(seg_limits[seg_index], seg_limits[seg_index + 1]) for seg_index in range(num_seg)}
        

        
        spike_vector2 = self.analyzer.sorting.to_spike_vector(concatenated=False)
        # this is dict of list because per segment spike_indices[unit_id][segment_index]
        spike_indices = spike_vector_to_indices(spike_vector2, unit_ids)
        # this is flatten
        self._spike_index_by_units = {}
        for unit_id in unit_ids:
            self._spike_index_by_units[unit_id] = np.concatenate([spike_indices[seg_ind][unit_id] for seg_ind in range(num_seg)])


        if verbose:
            t1 = time.perf_counter()
            print('Gather all spikes', t1 - t0)
            
            t0 = time.perf_counter()
            print('similarity')

        self.visible_channel_inds = np.arange(self.analyzer.recording.get_num_channels(), dtype='int64')

        self._spike_visible_indices = np.array([], dtype='int64')
        self._spike_selected_indices = np.array([], dtype='int64')
        self.update_visible_spikes()


        if verbose:
            t1 = time.perf_counter()
            print('similarity', t1 - t0)
            
            t0 = time.perf_counter()
            # print('')


        
    @property
    def channel_ids(self):
        return self.analyzer.recording.channel_ids

    @property
    def unit_ids(self):
        return self.analyzer.sorting.unit_ids
    
    def get_extremum_channel(self, unit_id):
        chan_ind = self._extremum_channel[unit_id]
        return chan_ind

    def update_visible_spikes(self):
        #~ print('update_visible_spikes')
        #~ t0 = time.perf_counter()
        
        inds = []
        for unit_index, unit_id in enumerate(self.unit_ids):
            #~ mask = self.spikes['unit_index'] == unit_index
            #~ self.spikes['visible'][mask] = self.unit_visible_dict[unit_id]
            ind = self._spike_index_by_units[unit_id]
            
            #~ self.spikes['visible'][ind] = self.unit_visible_dict[unit_id]
            if self.unit_visible_dict[unit_id]:
                inds.append(ind)
        
        if len(inds) > 0:
            inds = np.concatenate(inds)
            inds = np.sort(inds)
        else:
            inds = np.array([], dtype='int64')
        self._spike_visible_indices = inds
        
        self._spike_selected_indices = np.array([], dtype='int64')
        #~ t1 = time.perf_counter()
        #~ print('update_visible_spikes', t1-t0, self.spikes.size)
    
    def get_indices_spike_visible(self):
        return self._spike_visible_indices

    def get_indices_spike_selected(self):
        return self._spike_selected_indices
    
    def set_indices_spike_selected(self, inds):
        #~ self.controller.spikes['selected'][:] = False
        #~ self.controller.spikes['selected'][inds] = True
        self._spike_selected_indices = np.array(inds)

    def get_num_samples(self, segment_index):
        return self.analyzer.recording.get_num_samples(segment_index=segment_index)
    
    def get_traces(self, trace_source='preprocessed', **kargs):
        # assert trace_source in ['preprocessed', 'raw']
        assert trace_source in ['preprocessed']
        
        if trace_source == 'preprocessed':
            rec = self.analyzer.recording
        elif trace_source == 'raw':
            raise NotImplemented
            # TODO get with parent recording the non process recording
            pass
        kargs['return_scaled'] = self.return_scaled
        traces = rec.get_traces(**kargs)
        return traces
    
    def get_contact_location(self):
        location = self.analyzer.recording.get_channel_locations()
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
    
    def detect_high_similarity(self, threshold=0.9):
        return
    
    def get_probe(self):
        return self.analyzer.get_probe()
        
    def set_channel_visibility(self, visible_channel_inds):
        self.visible_channel_inds = np.array(visible_channel_inds, copy=True)

    def handle_metrics(self):
        return self.metrics is not None

    def handle_spike_amplitudes(self):
        return self.spike_amplitudes is not None
        
    def handle_principal_components(self):
        return self.pc_ext is not None
        
    def get_all_pcs(self):

        if self._pc_projections is None:
            self._pc_projections, self._pc_indices = self.pc_ext.get_some_projections(
                channel_ids=self.analyzer.channel_ids,
                unit_ids=self.analyzer.unit_ids
            )

        return self._pc_indices, self._pc_projections
    
    

    def get_sparsity_mask(self):
        if self.external_sparsity is not None:
            return self.external_sparsity.mask
        else:
            return self.analyzer_sparsity.mask

    def get_similarity(self, method='cosine_similarity'):
        similarity = self._similarity_by_method.get(method, None)
        return similarity
    
    def compute_similarity(self, method='cosine_similarity'):
        # have internal cache
        if method in self._similarity_by_method:
            return self._similarity_by_method[method]
        ext = self.analyzer.compute("template_similarity", method=method, save=False)
        self._similarity_by_method[method] = ext.get_data()
        return self._similarity_by_method[method]


    def compute_unit_positions(self, method, method_kwargs):
        ext = self.analyzer.compute_one_extension('unit_locations', save=False, method=method, **method_kwargs)
        # 2D only
        self.unit_positions = ext.get_data()[:, :2]

    def get_correlograms(self):
        return self.correlograms, self.correlograms_bins

    def compute_correlograms(self, window_ms, bin_ms):
        ext = self.analyzer.compute("correlograms", save=False, window_ms=window_ms, bin_ms=bin_ms)
        self.correlograms, self.correlograms_bins = ext.get_data()
        return self.correlograms, self.correlograms_bins
    
    def get_isi_histograms(self):
        return self.isi_histograms, self.isi_bins

    def compute_isi_histograms(self, window_ms, bin_ms):
        ext = self.analyzer.compute("isi_histograms", save=False, window_ms=window_ms, bin_ms=bin_ms)
        self.isi_histograms, self.isi_bins = ext.get_data()
        return self.isi_histograms, self.isi_bins
