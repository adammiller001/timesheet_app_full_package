import base64
import html
import json


def build_auto_download_html(
    file_bytes: bytes,
    file_name: str,
    mime_type: str = "application/octet-stream",
) -> str:
    """Build a small browser payload that immediately downloads file bytes."""
    encoded_file = base64.b64encode(file_bytes).decode("ascii")
    safe_file_name = html.escape(file_name, quote=True)
    js_file_name = json.dumps(file_name)
    js_mime_type = json.dumps(mime_type)

    return f"""
    <a id="automatic-export-download" download="{safe_file_name}" hidden></a>
    <script>
      const encodedFile = "{encoded_file}";
      const binaryFile = atob(encodedFile);
      const fileBytes = new Uint8Array(binaryFile.length);
      for (let index = 0; index < binaryFile.length; index += 1) {{
        fileBytes[index] = binaryFile.charCodeAt(index);
      }}

      const exportBlob = new Blob([fileBytes], {{ type: {js_mime_type} }});
      const exportUrl = URL.createObjectURL(exportBlob);
      const downloadLink = document.getElementById("automatic-export-download");
      downloadLink.href = exportUrl;
      downloadLink.download = {js_file_name};
      downloadLink.click();
      window.setTimeout(() => URL.revokeObjectURL(exportUrl), 1000);
    </script>
    """
