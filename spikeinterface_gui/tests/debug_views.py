import PySide6
import spikeinterface_gui as sigui
from spikeinterface_gui.tests.testingtools import clean_all, make_one_folder



from spikeinterface import WaveformExtractor, extract_waveforms



from pathlib import Path

test_folder = Path('my_dataset')


def debug_one_view():

    app = sigui.mkQApp()
    we = WaveformExtractor.load_from_folder(test_folder / 'waveforms')
    
    
    controller = sigui.SpikeinterfaceController(we)
    
    #~ controller.unit_visible_dict = {k: False for k in controller.unit_visible_dict}
    #~ controller.unit_visible_dict[list(controller.unit_visible_dict.keys())[0]] = True
    #~ controller.unit_visible_dict[list(controller.unit_visible_dict.keys())[1]] = True
    
    app = sigui.mkQApp()
    
    view0 = sigui.UnitListView(controller=controller)
    view0.show()
    #~ view = sigui.SpikeListView(controller=controller)
    #~ view = sigui.PairListView(controller=controller)
    #~ view = sigui.TraceView(controller=controller)
    #~ view = sigui.WaveformView(controller=controller)
    #~ view = sigui.WaveformHeatMapView(controller=controller)
    #~ view = sigui.ISIView(controller=controller)
    #~ view = sigui.CrossCorrelogramView(controller=controller)
    #~ view = sigui.ProbeView(controller=controller)
    view = sigui.NDScatterView(controller=controller)
    
    
    
    view.show()
    app.exec_()

    
if __name__ == '__main__':
    debug_one_view()
