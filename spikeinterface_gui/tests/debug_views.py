import spikeinterface_gui as sigui
from spikeinterface_gui.tests.testingtools import clean_all, make_analyzer_folder



import spikeinterface.full as si



from pathlib import Path

test_folder = Path('my_dataset')


def debug_one_view():

    app = sigui.mkQApp()
    sorting_analyzer = si.load_sorting_analyzer(test_folder / "sorting_analyzer")
    
    
    controller = sigui.SpikeinterfaceController(sorting_analyzer)
    
    #~ controller.unit_visible_dict = {k: False for k in controller.unit_visible_dict}
    #~ controller.unit_visible_dict[list(controller.unit_visible_dict.keys())[0]] = True
    #~ controller.unit_visible_dict[list(controller.unit_visible_dict.keys())[1]] = True
    
    app = sigui.mkQApp()
    
    # view0 = sigui.UnitListView(controller=controller)
    # view0.show()
    #~ view = sigui.SpikeListView(controller=controller)
    #~ view = sigui.PairListView(controller=controller)
    #~ view = sigui.TraceView(controller=controller)
    #~ view = sigui.WaveformView(controller=controller)
    #~ view = sigui.WaveformHeatMapView(controller=controller)
    #~ view = sigui.ISIView(controller=controller)
    #~ view = sigui.CrossCorrelogramView(controller=controller)
    #~ view = sigui.ProbeView(controller=controller)
    # view = sigui.NDScatterView(controller=controller)
    #~ view = sigui.SimilarityView(controller=controller)
    # view = sigui.SpikeAmplitudeView(controller=controller)

    view = sigui.TraceMapView(controller=controller)
    
    view.show()
    app.exec()

    
if __name__ == '__main__':
    debug_one_view()
