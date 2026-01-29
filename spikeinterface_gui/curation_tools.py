import numpy as np


default_label_definitions = {
    "quality": {
        "label_options": ["good", "noise", "MUA"],
        "exclusive": True
    },
}


empty_curation_data = {
    "format_version": "2",
    "manual_labels": [],
    "merges": [],
    "splits": [],
    "removed": []
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


def cast_unit_dtypes_in_curation(curation_data, unit_ids_dtype):
    """Cast unit ids in curation data to the correct dtype."""
    if "unit_ids" in curation_data:
        curation_data["unit_ids"] = [unit_ids_dtype(uid) for uid in curation_data["unit_ids"]]

    if "merges" in curation_data:
        for merge in curation_data["merges"]:
            merge["unit_ids"] = [unit_ids_dtype(uid) for uid in merge["unit_ids"]]
            new_unit_id = merge.get("new_unit_id", None)
            if new_unit_id is not None:
                merge["new_unit_id"] = unit_ids_dtype(new_unit_id)

    if "splits" in curation_data:
        for split in curation_data["splits"]:
            split["unit_id"] = unit_ids_dtype(split["unit_id"])
            new_unit_ids = split.get("new_unit_ids", None)
            if new_unit_ids is not None:
                split["new_unit_ids"] = [unit_ids_dtype(uid) for uid in new_unit_ids]

    if "removed" in curation_data:
        curation_data["removed"] = [unit_ids_dtype(uid) for uid in curation_data["removed"]]

    if "manual_labels" in curation_data:
        for label_entry in curation_data["manual_labels"]:
            label_entry["unit_id"] = unit_ids_dtype(label_entry["unit_id"])

    return curation_data