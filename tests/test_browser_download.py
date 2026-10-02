import base64

from app.exports.browser_download import build_auto_download_html


def test_auto_download_html_contains_file_and_starts_download():
    file_bytes = b"sample export package"

    result = build_auto_download_html(
        file_bytes,
        "Timesheet Export.zip",
        "application/zip",
    )

    assert base64.b64encode(file_bytes).decode("ascii") in result
    assert 'download="Timesheet Export.zip"' in result
    assert 'new Blob([fileBytes], { type: "application/zip" })' in result
    assert "downloadLink.click()" in result


def test_auto_download_html_escapes_download_attribute():
    result = build_auto_download_html(b"data", 'A&B".zip')

    assert 'download="A&amp;B&quot;.zip"' in result
