from .base import ControllerBase

class  SpikeinterfaceController(ControllerBase):
    
    
    def __init__(self, waveform_extractor=None,parent=None):
        ControllerBase.__init__(self, parent=parent)
        
        self.we = waveform_extractor
        print(self.we)