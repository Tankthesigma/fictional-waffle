from app.core.transform_settings import normalize_channel_overrides, override_rows, resolve_channel_transform


def test_channel_transform_override_wins_over_global_transform():
    overrides = {"channel_overrides": {"FL1-A": {"transform": "arcsinh", "cofactor": 42}}}

    setting = resolve_channel_transform("FL1-A", "raw", 150, overrides)
    fallback = resolve_channel_transform("FL2-A", "raw", 150, overrides)

    assert setting.transform == "arcsinh"
    assert setting.cofactor == 42.0
    assert setting.source == "channel"
    assert fallback.transform == "raw"
    assert fallback.source == "global"


def test_transform_overrides_ignore_bad_payloads():
    payload = {"channel_overrides": {"FL1-A": {"transform": "bad"}, "FL2-A": {"transform": "safe_log10", "cofactor": "nope"}}}

    assert normalize_channel_overrides(payload) == {"FL2-A": {"transform": "safe_log10", "cofactor": 150.0}}
    assert override_rows(payload) == [{"channel": "FL2-A", "transform": "safe_log10", "cofactor": 150.0}]
