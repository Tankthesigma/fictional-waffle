from app.core.demo_data import build_demo_samples


def test_demo_samples_are_deterministic_labeled_and_local(tmp_path):
    first = build_demo_samples(tmp_path / "first", events_per_sample=200)
    second = build_demo_samples(tmp_path / "second", events_per_sample=200)

    assert [sample.sample_id for sample in first] == ["demo_control_1", "demo_control_2", "demo_treated_1", "demo_treated_2"]
    assert [sample.condition for sample in first] == ["control", "control", "treated", "treated"]
    assert first[0].events.equals(second[0].events)
    assert first[0].path.exists()
    assert first[0].event_count == 200

    fitc = next(channel for channel in first[0].channels if channel.raw_name == "FITC-A")
    pe = next(channel for channel in first[0].channels if channel.raw_name == "PE-A")
    assert fitc.label == "Demo Marker A FITC (FITC-A)"
    assert pe.label == "Demo Marker B PE (PE-A)"
