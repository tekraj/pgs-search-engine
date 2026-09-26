"""Spark Security Scanner - basic, harmless checks on a file before it
enters the pipeline (extension, size, filename, hash). This is NOT a
real virus scanner - it's a simple rule-based check for a university
project demo. Real malware scanning (ClamAV) is separate, later work.
"""

import hashlib

# Extensions we treat as risky to auto-run/auto-open.
SUSPICIOUS_EXTENSIONS = {
    "exe", "bat", "cmd", "com", "scr", "msi", "vbs", "js", "jar", "ps1", "sh"
}

# Extensions we expect to see routinely from the web crawler.
EXPECTED_EXTENSIONS = {
    "html", "htm", "pdf", "txt", "json", "png", "jpg", "jpeg", "gif", "docx", "csv"
}

MAX_SAFE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_FILENAME_LENGTH = 100


def get_extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()