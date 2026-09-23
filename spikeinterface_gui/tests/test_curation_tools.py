from spikeinterface_gui.curation_tools import add_merge


def _as_sets(merges):
    # add_merge returns [{"unit_ids": [...]}, ...] with the group contents
    # de-duplicated via set(), so compare order-insensitively.
    return {frozenset(merge["unit_ids"]) for merge in merges}


def test_add_merge():
    # previous merges use the curation_data["merges"] format: list of
    # {"unit_ids": [...]} groups. Adding a new group transitively merges every
    # existing group that shares a unit with it.
    previous_merges = [
        {"unit_ids": [1, 2, 3]},
        {"unit_ids": [4, 5, 6]},
        {"unit_ids": [7, 8]},
    ]

    # disjoint new group -> kept as its own group, others untouched
    assert _as_sets(add_merge(previous_merges, [12, 10])) == {
        frozenset({10, 12}), frozenset({1, 2, 3}), frozenset({4, 5, 6}), frozenset({7, 8}),
    }
    # shares unit 1 -> folds into the {1,2,3} group
    assert _as_sets(add_merge(previous_merges, [1, 10])) == {
        frozenset({1, 2, 3, 10}), frozenset({4, 5, 6}), frozenset({7, 8}),
    }
    # bridges the {1,2,3} and {4,5,6} groups
    assert _as_sets(add_merge(previous_merges, [1, 10, 4])) == {
        frozenset({1, 2, 3, 4, 5, 6, 10}), frozenset({7, 8}),
    }
    # bridges the {1,2,3} and {7,8} groups
    assert _as_sets(add_merge(previous_merges, [1, 10, 8])) == {
        frozenset({1, 2, 3, 7, 8, 10}), frozenset({4, 5, 6}),
    }
    # bridges all three groups
    assert _as_sets(add_merge(previous_merges, [1, 4, 8])) == {
        frozenset({1, 2, 3, 4, 5, 6, 7, 8}),
    }


if __name__ == '__main__':
    test_add_merge()
