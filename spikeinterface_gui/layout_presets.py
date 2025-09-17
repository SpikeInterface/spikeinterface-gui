import json
from spikeinterface_gui.viewlist import possible_class_views

"""
A preset need 8 zones like this:

+-----------------+-----------------+
| [zone1   zone2] | [zone3 | [zone4 |
+-----------------+        |        +
| [zone5   zone6] | zone7] | zone8] |
+-----------------+-----------------+

"""
_presets = {}

def _check_valid_layout_dict(layout_dict):
    for key, class_views in layout_dict.items():
        if key not in [f"zone{a}" for a in range(1,9)]:
            raise KeyError(f"Key {key} in layout dictionary not equal to zone1, zone2, ... or zone8.")
        for class_view in class_views:
            list_of_possible_class_views = list(possible_class_views.keys())
            if class_view not in list_of_possible_class_views:
                raise KeyError(f"View '{class_view}' in layout dictionary not equal to a valid View. "\
                                "Valid views are {list_of_possible_class_views}")

def get_layout_description(preset_name, layout=None):
    if isinstance(layout, dict):
        _check_valid_layout_dict(layout)
        # If a layout_dict is provided, use it instead of the preset
        return layout
    elif isinstance(layout, str):
        if layout.endswith('json'):
            with open(layout) as layout_file:
                layout_dict = json.load(layout_file)
            return get_layout_description(None, layout=layout_dict)
    else:
        if preset_name is None:
            preset_name = 'default'
        return _presets[preset_name]


default_layout = dict(
    zone1=['curation', 'spikelist'],
    zone2=['unitlist', 'mergelist'],
    zone3=['trace', 'tracemap',  'spikeamplitude', 'spikedepth', 'rateview'],
    zone4=[],
    zone5=['probe'],
    zone6=['ndscatter', 'similarity'],
    zone7=['waveform', 'waveformheatmap', ],
    zone8=['correlogram', 'isi', 'mainsettings'],
)
_presets['default'] = default_layout


# legacy layout for nostalgic people like me
legacy_layout = dict(
    zone1=['curation', 'spikelist'],
    zone2=['unitlist', 'mergelist'],
    zone3=['trace', 'tracemap', 'waveform', 'waveformheatmap', 'isi', 'correlogram', 'spikeamplitude'],
    zone4=[],
    zone5=['probe'],
    zone6=['ndscatter', 'similarity'],
    zone7=[],
    zone8=[],
)
_presets['legacy'] = legacy_layout

unit_focus_layout = dict(
    zone1=['unitlist', 'mergelist', 'curation', 'spikelist'],
    zone2=[],
    zone3=['trace', 'tracemap',  'spikeamplitude', 'spikedepth'],
    zone4=[],
    zone5=['probe', 'mainsettings'],
    zone6=['ndscatter', 'similarity'],
    zone7=['waveform', 'waveformheatmap', ],
    zone8=['correlogram', 'isi'],
)
_presets['unit_focus'] = unit_focus_layout
