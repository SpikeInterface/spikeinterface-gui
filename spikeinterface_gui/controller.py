from .base import ControllerBase
from .myqt import QT
from spikeinterface.widgets.utils import get_unit_colors

import numpy as np

spike_dtype =[('sample_index', 'int64'), ('unit_index', 'int64'), 
    ('channel_index', 'int64'), ('segment_index', 'int64'),
    ('visible', 'bool'), ('selected', 'bool')]

class  SpikeinterfaceController(ControllerBase):
    
    
    def __init__(self, waveform_extractor=None,parent=None):
        ControllerBase.__init__(self, parent=parent)
        
        self.we = waveform_extractor
        
        # TODO
        self.colors = get_unit_colors(self.we.sorting, map_name='Dark2', format='RGBA')
        self.qcolors = {}
        for unit_id, color in self.colors.items():
            r, g, b, a = color
            self.qcolors[unit_id] = QT.QColor(r*255, g*255, b*255)
        
        self.cluster_visible = {unit_id:True for unit_id in self.unit_ids}
        
        all_spikes = self.we.sorting.get_all_spike_trains(outputs='unit_index')
        
        num_spikes = np.sum(e[0].size for e in all_spikes)
        
        # make internal spike vector
        self.spikes = np.zeros(num_spikes, dtype=spike_dtype)
        pos = 0
        for i in range(self.we.recording.get_num_segments()):
            sample_index, unit_index = all_spikes[i]
            sl = slice(pos, pos+len(sample_index))
            self.spikes[sl]['sample_index'] = sample_index
            self.spikes[sl]['unit_index'] = unit_index
            #~ self.spikes[sl]['channel_index'] = 
            self.spikes[sl]['segment_index'] = i
            self.spikes[sl]['visible'] = True
            self.spikes[sl]['selected'] = False


    @property
    def channels_ids(self):
        return self.we.recording.channel_ids

    @property
    def unit_ids(self):
        return self.we.sorting.unit_ids
    
    
    def get_extremum_channel(self):
        pass
        

    def on_cluster_visibility_changed(self):
        #~ print('on_cluster_visibility_changed')
        self.update_visible_spikes()
        ControllerBase.on_cluster_visibility_changed(self)

    def update_visible_spikes(self):
        for unit_index, unit_id in enumerate(self.unit_ids):
            mask = self.spikes['unit_index'] == unit_index
            self.spikes['visible'][mask] = self.cluster_visible[unit_id]

