import numpy as np

def get_size_top_row(initial_row, initial_col, is_zone_array, original_zone_array):
    
    if original_zone_array[initial_row][initial_col] == False:
        return 0,0

    num_rows = is_zone_array[initial_row][initial_col]*1
    num_cols = num_rows

    num_rows += (not is_zone_array[1][initial_col])*1

    if num_rows == 1:
        for zone in is_zone_array[0,1+initial_col:]:
            if zone == True:
                break
            num_cols += 1
    elif num_rows == 2:
        for zone1, zone2 in np.transpose(is_zone_array[:,1+initial_col:]):
            if zone1 == True or zone2 == True:
                break
            num_cols += 1

    is_zone_array[initial_row:initial_row+num_rows,initial_col:initial_col+num_cols] = True

    return num_rows, num_cols

def get_size_bottom_row(initial_row, initial_col, is_zone_array, original_zone_array):
    
    if original_zone_array[initial_row][initial_col] == False:
        return 0,0
    
    num_rows = is_zone_array[initial_row][initial_col]*1
    if num_rows == 0:
        return 0, 0
    num_cols = num_rows

    for zone in is_zone_array[1,1+initial_col:]:
        if zone == True:
            break
        else:
            num_cols += 1

    return num_rows, num_cols