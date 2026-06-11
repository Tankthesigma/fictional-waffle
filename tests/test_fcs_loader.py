from app.core.fcs_loader import _read_flow_data, load_fcs_file


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
