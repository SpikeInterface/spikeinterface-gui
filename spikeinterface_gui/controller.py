import time

from .base import ControllerBase
from .myqt import QT

from spikeinterface.widgets.utils import get_unit_colors
from spikeinterface.toolkit import (get_template_extremum_channel, get_template_channel_sparsity,
    compute_correlograms, compute_unit_centers_of_mass, compute_num_spikes, WaveformPrincipalComponent,
    compute_template_similarity)

import numpy as np

spike_dtype =[('sample_index', 'int64'), ('unit_index', 'int64'), 
    ('channel_index', 'int64'), ('segment_index', 'int64'),
    ('visible', 'bool'), ('selected', 'bool'), ('included_in_pc', 'bool')]


_MAX_SPIKE_PER_UNIT_WARNING = 5000

class  SpikeinterfaceController(ControllerBase):
    def __init__(self, waveform_extractor=None,parent=None, verbose=False):
        ControllerBase.__init__(self, parent=parent)
        
        self.we = waveform_extractor
        
        max_spikes_per_unit = self.we._params['max_spikes_per_unit']
        if  max_spikes_per_unit > _MAX_SPIKE_PER_UNIT_WARNING:
            print(f'You have {max_spikes_per_unit} in your WaveformExtractor, the display can be slow')
            print(f'You should re run the WaveformExtractor with max_spikes_per_unit=500')
        
        
        if (self.we.folder / 'PCA').is_dir():
            self.pc = WaveformPrincipalComponent.load_from_folder(self.we.folder)
        else:
            self.pc = None
        
        
        # some direct attribute
        self.num_segments = self.we.recording.get_num_segments()
        self.sampling_frequency = self.we.recording.get_sampling_frequency()
        
        
        self.colors = get_unit_colors(self.we.sorting)
        self.qcolors = {}
        for unit_id, color in self.colors.items():
            r, g, b, a = color
            self.qcolors[unit_id] = QT.QColor(r*255, g*255, b*255)
        
        self.unit_visible_dict = {unit_id:False for unit_id in self.unit_ids}
        self.unit_visible_dict[self.unit_ids[0]] = True
        
        if verbose:
            t0 = time.perf_counter()
            print('Gather all spikes')
        
        all_spikes = self.we.sorting.get_all_spike_trains(outputs='unit_index')
        
        num_spikes = np.sum(e[0].size for e in all_spikes)
        
        # make internal spike vector
        self.spikes = np.zeros(num_spikes, dtype=spike_dtype)
        pos = 0
        for segment_index in range(self.num_segments):
            sample_index, unit_index = all_spikes[segment_index]
            sl = slice(pos, pos+len(sample_index))
            self.spikes[sl]['sample_index'] = sample_index
            self.spikes[sl]['unit_index'] = unit_index
            #~ self.spikes[sl]['channel_index'] = 
            self.spikes[sl]['segment_index'] = segment_index
            self.spikes[sl]['visible'] = True
            self.spikes[sl]['selected'] = False
            self.spikes[sl]['included_in_pc'] = False
        
        # create boolean vector of wich spike have been selected by WaveformExtractor
        for segment_index in range(self.num_segments):
            for unit_index, unit_id in enumerate(self.unit_ids):
                global_inds, = np.nonzero((self.spikes['unit_index'] == unit_index) & (self.spikes['segment_index'] == segment_index))
                sampled_index = self.we.get_sampled_indices(unit_id)
                local_inds = sampled_index[sampled_index['segment_index'] == segment_index]['spike_index']
                self.spikes['included_in_pc'][global_inds[local_inds]] = True
        
        if verbose:
            t1 = time.perf_counter()
            print('Gather all spikes', t1 - t0)
            
            t0 = time.perf_counter()
            print('Get template average/std')
        
        # extremum channel
        self.templates_average = self.we.get_all_templates(unit_ids=None, mode='average')
        self.templates_std = self.we.get_all_templates(unit_ids=None, mode='std')

        if verbose:
            t1 = time.perf_counter()
            print('Get template average/std', t1 - t0)
            
            t0 = time.perf_counter()
            print('Sparsity and extremum')

        
        # self.compute_sparsity(method='threshold', threshold=2.5)
        self.compute_sparsity(method='radius', radius_um=90.)
        self._extremum_channel = get_template_extremum_channel(self.we, peak_sign='neg', outputs='index')
        
        for unit_index, unit_id in enumerate(self.unit_ids):
            mask = self.spikes['unit_index'] == unit_index
            self.spikes['channel_index'][mask] = self._extremum_channel[unit_id]

        if verbose:
            t1 = time.perf_counter()
            print('Sparsity and extremum', t1 - t0)
            
            t0 = time.perf_counter()
            print('Unit posistion')

        
        self.visible_channel_inds = np.arange(self.we.recording.get_num_channels(), dtype='int64')
        
        coms = compute_unit_centers_of_mass(self.we, peak_sign='neg', num_channels=10)
        self.unit_positions = np.vstack([coms[u] for u in self.unit_ids])

        if verbose:
            t1 = time.perf_counter()
            print('Unit posistion', t1 - t0)
            
        self.num_spikes = compute_num_spikes(self.we)

        # precompute index for each unit
        self._spike_index_by_units = {}
        for unit_index, unit_id in enumerate(self.unit_ids):
            ind,  = np.nonzero(self.spikes['unit_index'] == unit_index)
            self._spike_index_by_units[unit_id] = ind
        
        self.update_visible_spikes()
        
        self._similarity_by_method = {}
        if len(self.unit_ids) <= 64 and len(self.channel_ids) <= 64:
            # precompute similarity when low channel/units countt
            self.get_similarity(method='cosine_similarity')
        
    @property
    def channel_ids(self):
        return self.we.recording.channel_ids

    @property
    def unit_ids(self):
        return self.we.sorting.unit_ids
    
    def get_extremum_channel(self, unit_id):
        chan_ind = self._extremum_channel[unit_id]
        return chan_ind

    def update_visible_spikes(self):
        #~ print('update_visible_spikes')
        #~ t0 = time.perf_counter()
        for unit_index, unit_id in enumerate(self.unit_ids):
            #~ mask = self.spikes['unit_index'] == unit_index
            #~ self.spikes['visible'][mask] = self.unit_visible_dict[unit_id]
            ind = self._spike_index_by_units[unit_id]
            self.spikes['visible'][ind] = self.unit_visible_dict[unit_id]
        #~ t1 = time.perf_counter()
        #~ print('update_visible_spikes', t1-t0, self.spikes.size)
    
    def get_num_samples(self, segment_index):
        return self.we.recording.get_num_samples(segment_index=segment_index)
    
    def get_traces(self, trace_source='preprocessed', **kargs):
        # assert trace_source in ['preprocessed', 'raw']
        assert trace_source in ['preprocessed']
        
        if trace_source == 'preprocessed':
            rec = self.we.recording
        elif trace_source == 'raw':
            raise NotImplemented
            # TODO get with parent recording the non process recording
            pass
        kargs['return_scaled'] = self.we.return_scaled
        traces = rec.get_traces(**kargs)
        return traces

    def get_contact_location(self):
        location = self.we.recording.get_channel_locations()
        return location
    
    def get_waveform_sweep(self):
        return self.we.nbefore, self.we.nafter
        
    def get_waveforms_range(self):
        return np.nanmin(self.templates_average), np.nanmax(self.templates_average)
    
    def get_waveforms(self, unit_id):
        return self.we.get_waveforms(unit_id)
    
    def get_common_sparse_channels(self, unit_ids):
        unit_indexes = [list(self.unit_ids).index(u) for u in unit_ids]
        chan_inds, = np.nonzero(self.sparsity_mask[unit_indexes, :].sum(axis=0))
        return chan_inds
    
    def detect_high_similarity(self, threshold=0.9):
        return
    
    def compute_correlograms(self, window_ms, bin_ms, symmetrize):
        correlograms, bins = compute_correlograms(self.we.sorting, window_ms=window_ms, bin_ms=bin_ms, symmetrize=symmetrize)
        return correlograms, bins
    
    def get_probe(self):
        return self.we.recording.get_probe()
        
    def set_channel_visibility(self, visible_channel_inds):
        self.visible_channel_inds = np.array(visible_channel_inds, copy=True)
        
    def handle_principal_components(self):
        return self.pc is not None
        
    def get_all_pcs(self):
        pc_unit_index, pcs = self.pc.get_all_components(outputs='index')
        return pc_unit_index, pcs
    
    def get_similarity(self, method='cosine_similarity', force_compute=True):
        similarity = self._similarity_by_method.get(method, None)
        if similarity is None:
            if force_compute:
                similarity = compute_template_similarity(self.we, method=method)
                self._similarity_by_method[method] = similarity
            else:
                return
        return similarity
    
    def compute_sparsity(self, method='best_channels', num_channels=10, radius_um=90, threshold=2.5):
        sparsity_dict = get_template_channel_sparsity(self.we, method=method,
                               peak_sign='both', 
                               num_channels=num_channels, radius_um=radius_um, threshold=threshold,
                               outputs='index')
        
        self.sparsity_mask = np.zeros((self.unit_ids.size, self.channel_ids.size), dtype='bool')
        for unit_index, unit_id in enumerate(self.unit_ids):
            chan_inds = sparsity_dict[unit_id]
            self.sparsity_mask[unit_index, chan_inds] = True
    
    def get_sparsity_mask(self):
        return self.sparsity_mask


