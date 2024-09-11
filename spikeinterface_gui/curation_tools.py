


default_label_definitions = {
    "quality": {
        "label_options": ["good", "noise", "MUA", "artifact"],
        "exclusive": True
    },
}


empty_curation_data = {
    "manual_labels": [],
    "merge_unit_groups": [],
    "removed_units": []
}

def adding_group(previous_groups, new_group):
    to_merge = [new_group.copy()]
    unchanged = []
    for c_prev in previous_groups:
        is_unaffected = True

        for c_new in new_group:
            if c_new in c_prev:
                is_unaffected = False
                to_merge.append(c_prev)
                break

        if is_unaffected:
            unchanged.append(c_prev)
    new_merge_group = [sum(to_merge, [])]
    new_merge_group.extend(unchanged)
    # Ensure the unicity
    new_merge_group = [list(set(gp)) for gp in new_merge_group]
    return new_merge_group
