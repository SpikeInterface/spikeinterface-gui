from spikeinterface_gui.curation_tools import adding_group


def test_adding_group():
    original_groups = [[1, 2, 3], [4, 5, 6], [7, 8]]
    new_group_0 = [12, 10]
    new_group_1 = [1, 10]
    new_group_2 = [1, 10, 4]
    new_group_3 = [1, 10, 8]
    new_group_4 = [1, 4, 8]
    r0 = adding_group(original_groups, new_group_0)
    r1 = adding_group(original_groups, new_group_1)
    r2 = adding_group(original_groups, new_group_2)
    r3 = adding_group(original_groups, new_group_3)
    r4 = adding_group(original_groups, new_group_4)
    assert r0 == [[10, 12], [1, 2, 3], [4, 5, 6], [8, 7]]
    assert r1 == [[3, 1, 10, 2], [4, 5, 6], [8, 7]]
    assert r2 == [[1, 2, 3, 4, 5, 6, 10], [8, 7]]
    assert r3 == [[1, 2, 3, 7, 8, 10], [4, 5, 6]]
    assert r4 == [[1, 2, 3, 4, 5, 6, 7, 8]]
    print(f'{r0} \n {r1} \n {r2} \n {r3} \n {r4}')

