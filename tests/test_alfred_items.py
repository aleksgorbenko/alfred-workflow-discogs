from alfred_items import TYPE_ICONS, item


def test_item_omits_icon_by_default():
    assert "icon" not in item(title="Title")


def test_item_wraps_icon_path_in_alfred_icon_object():
    result = item(title="Title", icon="icons/icon_release.png")
    assert result["icon"] == {"path": "icons/icon_release.png"}


def test_type_icons_covers_all_search_result_types():
    assert set(TYPE_ICONS) == {"release", "master", "artist", "label"}


def test_item_omits_variables_by_default():
    assert "variables" not in item(title="Title")


def test_item_includes_variables_when_given():
    result = item(title="Title", variables={"DG_TYPE": "release", "DG_ID": "1"})
    assert result["variables"] == {"DG_TYPE": "release", "DG_ID": "1"}
