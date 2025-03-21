"""
A preset need 6 zones with list:
    * upper_right
    * bottom_right
    * upper_left
    * bottom_left
    * upper_sidebar
    * bottom_sidebar

+----------------+-------------+--------------+
| [upper_sidebar   upper_left] | upper_right  |
+----------------+-------------+              |
| [bottom_sidebar bottom_left] | bottom_right |
+----------------+-------------+--------------+

"""

_presets = {}
def get_layout_description(preset_name):
    if preset_name is None:
        preset_name = 'default'
    _presets[preset_name]
    return _presets[preset_name]


# default is legacy layout we can change it later
default_layout = dict(
    upper_right=['trace', 'tracemap', 'waveform', 'waveformheatmap', 'isi', 'correlogram', 'spikeamplitude'],
    bottom_right=[],
    upper_left=['unitlist', 'mergelist'],
    bottom_left=['ndscatter', 'similarity'],
    upper_sidebar=['curation', 'spikelist'],
    bottom_sidebar=['probe'],
)
_presets['default'] = default_layout


yep_layout = dict(
    upper_right=['trace', 'tracemap',  'correlogram', 'spikeamplitude'],
    bottom_right=['waveform', 'waveformheatmap', 'isi',],
    upper_left=['unitlist', 'mergelist'],
    bottom_left=['ndscatter', 'similarity'],
    upper_sidebar=['curation', 'spikelist'],
    bottom_sidebar=['probe'],
)
_presets['yep'] = yep_layout
