import numpy as np


default_label_definitions = {
    "quality": {
        "label_options": ["good", "noise", "MUA"],
        "exclusive": True
    },
}


empty_curation_data = {
    "manual_labels": [],
    "merges": [],
    "splits": [],
    "removes": []
}

def add_merge(previous_merges, new_merge_unit_ids):
    # this is to ensure that np.str_ types are rendered as str
    to_merge = [np.array(new_merge_unit_ids).tolist()]
    unchanged = []
    for c_prev in previous_merges:
        is_unaffected = True
        c_prev_unit_ids = c_prev["unit_ids"]
        for c_new in new_merge_unit_ids:
            if c_new in c_prev_unit_ids:
                is_unaffected = False
                to_merge.append(c_prev_unit_ids)
                break

        if is_unaffected:
            unchanged.append(c_prev_unit_ids)

    new_merge_units = [sum(to_merge, [])]
    new_merge_units.extend(unchanged)
    # Ensure the uniqueness
    new_merges = [{"unit_ids": list(set(gp))} for gp in new_merge_units]
    return new_merges
