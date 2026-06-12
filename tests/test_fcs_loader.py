import numpy as np

from app.core.fcs_loader import MAX_FCS_PARAMETERS, _events_to_dataframe, _extract_channel_names, _read_flow_data, load_fcs_file


def test_fcs_loader_invalid_file_handling(tmp_path):
    bad = tmp_path / "bad.fcs"
    bad.write_text("not an fcs file", encoding="utf-8")

    result = load_fcs_file(bad)

    assert result.sample is None
    assert result.errors


def test_fcs_loader_retries_offset_error(tmp_path):
    class FakeFlowData:
        calls = []

        def __init__(self, path, ignore_offset_error=False):
            self.calls.append(ignore_offset_error)
            if not ignore_offset_error:
                raise ValueError("reports a data offset that is off by 1. Set `ignore_offset_error=True`")

    loaded, warnings = _read_flow_data(FakeFlowData, tmp_path / "offset.fcs")

    assert isinstance(loaded, FakeFlowData)
    assert FakeFlowData.calls == [False, True]
    assert any("ignore_offset_error=True" in warning for warning in warnings)


def test_fcs_loader_retries_offset_discrepancy_flag(tmp_path):
    class FakeFlowData:
        calls = []

        def __init__(self, path, ignore_offset_error=False, ignore_offset_discrepancy=False):
            self.calls.append((ignore_offset_error, ignore_offset_discrepancy))
            if not ignore_offset_discrepancy:
                raise ValueError("has a discrepancy in the DATA start byte location")

    loaded, warnings = _read_flow_data(FakeFlowData, tmp_path / "offset.fcs")

    assert isinstance(loaded, FakeFlowData)
    assert FakeFlowData.calls == [(False, False), (True, False), (False, True)]
    assert any("ignore_offset_discrepancy=True" in warning for warning in warnings)


def test_event_dataframe_preserves_available_names_on_channel_mismatch():
    class FakeFlowData:
        events = np.array([[1.0, 2.0, 3.0]])

    frame, warnings = _events_to_dataframe(FakeFlowData(), 1, ["FSC-A", "SSC-A"])

    assert frame.columns.tolist() == ["FSC-A", "SSC-A", "Channel 3"]
    assert frame.iloc[0].tolist() == [1.0, 2.0, 3.0]
    assert any("missing names were filled" in warning for warning in warnings)


def test_event_dataframe_uses_data_shape_for_flat_arrays_with_bad_metadata():
    class FakeFlowData:
        events = np.array([1.0, 2.0, 3.0, 4.0])

    frame, warnings = _events_to_dataframe(FakeFlowData(), 2, ["FSC-A", "SSC-A", "FITC-A"])

    assert frame.shape == (2, 2)
    assert frame.columns.tolist() == ["FSC-A", "SSC-A"]
    assert any("extra metadata names were ignored" in warning for warning in warnings)


def test_extract_channel_names_uses_par_keyword_fallback():
    class FakeFlowData:
        channels = None

    names = _extract_channel_names(
        FakeFlowData(),
        {"$PAR": "3", "$P1N": "FSC-A", "$P2N": "SSC-A", "$P3N": "FITC-A"},
    )

    assert names == ["FSC-A", "SSC-A", "FITC-A"]


def test_extract_channel_names_caps_unreasonable_par_keyword():
    class FakeFlowData:
        channels = None

    names = _extract_channel_names(FakeFlowData(), {"$PAR": str(MAX_FCS_PARAMETERS + 10_000), "$P1N": "FSC-A"})

    assert len(names) == MAX_FCS_PARAMETERS
    assert names[0] == "FSC-A"
    assert names[-1] == f"Channel {MAX_FCS_PARAMETERS}"
