import pandas as pd
import base64

from app.core.channel_inference import summarize_channels
from app.core.gating import rectangle_gate
from app.core.report_pdf import export_pdf_report
from app.core.report_pptx import export_pptx_report
from app.models.sample import SampleRecord


def test_report_exports_create_files(tmp_path):
    frame = pd.DataFrame({"FSC-A": [1, 2], "SSC-A": [1, 2], "FL1-A": [10, 20]})
    sample = SampleRecord("s1", "s1.csv", path=tmp_path / "s1.csv", file_type="csv", events=frame)
    sample.channels = summarize_channels(frame)
    gate = rectangle_gate("g1", "main", "FSC-A", "SSC-A", 0, 3, 0, 3)
    stats = [{"gate_name": "main", "event_count": 2, "percent_total": 100.0}]
    image_path = tmp_path / "plot.png"
    image_path.write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="))

    pdf = export_pdf_report([sample], [], [gate], stats, tmp_path / "report.pdf", figure_paths=[image_path])
    pptx = export_pptx_report([sample], [], [gate], stats, tmp_path / "report.pptx", figure_paths=[image_path])

    assert pdf.exists()
    assert pdf.stat().st_size > 0
    assert pptx.exists()
    assert pptx.stat().st_size > 0
