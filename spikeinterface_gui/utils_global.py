import numpy as np

# Functions for the layout

def fill_unnecessary_space(layout_zone, shift):

    # First, move the right hand column leftwards if the left-hand column is missing
    if len(layout_zone[f'zone{1+shift}']) == 0 and len(layout_zone[f'zone{5+shift}']) == 0:
        layout_zone[f'zone{1+shift}'] = layout_zone[f'zone{2+shift}']
        layout_zone[f'zone{5+shift}'] = layout_zone[f'zone{6+shift}']
        layout_zone[f'zone{2+shift}'] = []
        layout_zone[f'zone{6+shift}'] = []

    # And move the bottom-left zone to the top-left, if the top-left is missing
    # These steps reduce the number of layouts we have to consider
    if len(layout_zone[f'zone{1+shift}']) == 0:
        layout_zone[f'zone{1+shift}'] = layout_zone[f'zone{5+shift}']
        layout_zone[f'zone{5+shift}'] = []

    return layout_zone


def get_present_zones_in_half_of_layout(layout_zone, shift):
    """
    Check which zones in layout_zone are 
    """
    half_dict = {key: value for key, value in layout_zone.items() if key in [f'zone{1+shift}', f'zone{2+shift}', f'zone{5+shift}', f'zone{6+shift}']}
    is_present = [views is not None and len(views) > 0 for views in half_dict.values()]
    present_zones = set(np.array(list(half_dict.keys()))[np.array(is_present)])
    return present_zones