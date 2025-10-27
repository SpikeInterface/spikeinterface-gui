import numpy as np
from pathlib import Path
import os

def get_config_folder() -> Path:
    """Get the config folder for spikeinterface-gui settings files.

    Returns
    -------
    cache_folder : Path
        The path to the cache folder.
    """
    return Path(os.path.expanduser("~")) / ".config" / "spikeinterface_gui"

# Functions for the layout

def fill_unnecessary_space(layout_zone, shift):
    """
    Used when making layouts. In the zoning algorithm,
    certain layouts are equivalent to each other e.g.

    zone1 zone2                       .     .
    .     .        is equivalent to   zone5 zone6

    and
 
    .     zone2                       zone1 .
    .     zone6    is equivalent to   zone5 .

    This function moves zones left-wards and upwards in a way that preserves 
    the layouts and ensures that the top-left zone is non-zero.
    """

    # Move the right hand column leftwards if the left-hand column is missing
    if len(layout_zone[f'zone{1+shift}']) == 0 and len(layout_zone[f'zone{5+shift}']) == 0:
        layout_zone[f'zone{1+shift}'] = layout_zone[f'zone{2+shift}']
        layout_zone[f'zone{5+shift}'] = layout_zone[f'zone{6+shift}']
        layout_zone[f'zone{2+shift}'] = []
        layout_zone[f'zone{6+shift}'] = []

    # Move the bottom-left zone to the top-left, if the top-left is missing
    # These steps reduce the number of layouts we have to consider
    if len(layout_zone[f'zone{1+shift}']) == 0:
        layout_zone[f'zone{1+shift}'] = layout_zone[f'zone{5+shift}']
        layout_zone[f'zone{5+shift}'] = []

    return layout_zone


def get_present_zones_in_half_of_layout(layout_zone, shift):
    """
    Returns the zones which contain at least one view, for either:
        left-hand zones  1,2,5,6 (shift=0)
        right-hand zones 3,4,7,8 (shift=2)
    """
    zones_in_half = [f'zone{1+shift}', f'zone{2+shift}', f'zone{5+shift}', f'zone{6+shift}']
    half_dict = {key: value for key, value in layout_zone.items() if key in zones_in_half}
    is_present = [views is not None and len(views) > 0 for views in half_dict.values()]
    present_zones = set(np.array(list(half_dict.keys()))[np.array(is_present)])
    return present_zones
