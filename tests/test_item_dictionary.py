from doc2rag.tables.item_dictionary import normalize_item_name


def test_exact_match():
    name, score = normalize_item_name("BMI")
    assert name == "BMI"
    assert score == 1.0


def test_known_variant_match():
    name, score = normalize_item_name("LDL-C")
    assert name == "LDLコレステロール"
    assert score > 0.8


def test_unknown_item_falls_back_to_raw_name():
    name, score = normalize_item_name("謎の検査項目XYZ")
    assert name == "謎の検査項目XYZ"
    assert score == 0.0
