"""
A preset need 8 zones like this:

+-----------------+-----------------+
| [zone1   zone2] | [zone3   zone4] |
+-----------------+-----------------+
| [zone5   zone6] | [zone7   zone8] |
+-----------------+-----------------+

"""

_presets = {}
def get_layout_description(preset_name):
    if preset_name is None:
        preset_name = 'default'
    _presets[preset_name]
    return _presets[preset_name]


default_layout = dict(
    zone1=['curation', 'spikelist'],
    zone2=['unitlist', 'mergelist'],
    zone3=['trace', 'tracemap',  'spikeamplitude', 'spikedepth'],
    zone4=[],
    zone5=['probe'],
    zone6=['ndscatter', 'similarity'],
    zone7=['waveform', 'waveformheatmap', ],
    zone8=['correlogram', 'isi'],
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

# yep is for testing
yep_layout = dict(
    zone1=['curation', 'spikelist'],
    zone2=['unitlist', 'mergelist'],
    zone3=['trace', 'tracemap',  'spikeamplitude'],
    zone4=['similarity'],
    zone5=['probe'],
    zone6=['ndscatter', ],
    zone7=['waveform', 'waveformheatmap', ],
    zone8=['correlogram', 'isi'],
)
_presets['yep'] = yep_layout
