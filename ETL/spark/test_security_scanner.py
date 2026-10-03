import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from security_scanner import inspect_file, scan_with_yara

CLEAN_RESULT = {"status": "CLEAN", "signature": None}
INFECTED_RESULT = {"status": "INFECTED", "signature": "Eicar-Test-Signature"}
ERROR_RESULT = {"status": "ERROR", "signature": None, "error": "connection refused"}

YARA_CLEAN = {"status": "CLEAN", "matches": []}
YARA_MATCH = {"status": "MATCH", "matches": ["EICAR_Test_String"]}


class SecurityScannerTests(unittest.TestCase):
    # -- Layer 1: basic checks (ClamAV + YARA mocked CLEAN so these test
    #    only the metadata logic, with no real network/Docker dependency) --

    @patch("security_scanner.scan_with_yara", return_value=YARA_CLEAN)
    @patch("security_scanner.scan_with_clamav", return_value=CLEAN_RESULT)
    def test_accepts_expected_document_type(self, mock_clamav, mock_yara):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notice.html"
            path.write_text("<h1>Notice</h1>", encoding="utf-8")

            result = inspect_file(path)

            self.assertTrue(result["accepted"])
            self.assertEqual(result["extension"], "html")
            self.assertEqual(result["findings"], [])
            self.assertEqual(result["verdict"], "SAFE")
            self.assertEqual(len(result["sha256"]), 64)
            mock_clamav.assert_called_once()
            mock_yara.assert_called_once()

    @patch("security_scanner.scan_with_yara", return_value=YARA_CLEAN)
    @patch("security_scanner.scan_with_clamav", return_value=CLEAN_RESULT)
    def test_rejects_suspicious_extension(self, mock_clamav, mock_yara):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.exe"
            path.write_bytes(b"binary")

            result = inspect_file(path)

            self.assertFalse(result["accepted"])
            self.assertIn("suspicious_extension", result["findings"])
            self.assertIn("unexpected_extension", result["findings"])
            self.assertEqual(result["verdict"], "SUSPICIOUS")

    # -- Layer 2: ClamAV content scanning (mocked - no live ClamAV needed) --

    @patch("security_scanner.scan_with_yara", return_value=YARA_CLEAN)
    @patch("security_scanner.scan_with_clamav", return_value=INFECTED_RESULT)
    def test_rejects_clamav_detected_threat(self, mock_clamav, mock_yara):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invoice.pdf"
            path.write_bytes(b"harmless-looking bytes, ClamAV mocked as FOUND")

            result = inspect_file(path)

            self.assertFalse(result["accepted"])
            self.assertEqual(result["verdict"], "INFECTED")
            self.assertTrue(any(f.startswith("clamav_infected") for f in result["findings"]))

    @patch("security_scanner.scan_with_yara", return_value=YARA_CLEAN)
    @patch("security_scanner.scan_with_clamav", return_value=ERROR_RESULT)
    def test_unknown_when_clamav_unavailable(self, mock_clamav, mock_yara):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notice.html"
            path.write_text("<h1>Notice</h1>", encoding="utf-8")

            result = inspect_file(path)

            # A ClamAV outage must NOT be silently treated as clean.
            self.assertFalse(result["accepted"])
            self.assertEqual(result["verdict"], "UNKNOWN")
            self.assertIn("clamav_unavailable", result["findings"])

    # -- Layer 3: YARA pattern scanning --

    def test_yara_clean_on_harmless_content(self):
        result = scan_with_yara(b"This is a harmless test file.")
        self.assertEqual(result["status"], "CLEAN")

    def test_yara_matches_exe_header(self):
        result = scan_with_yara(b"MZ\x90\x00\x03\x00\x00\x00 fake exe bytes")
        self.assertEqual(result["status"], "MATCH")
        self.assertIn("Windows_Executable_Header", result["matches"])

    @patch("security_scanner.scan_with_yara", return_value=YARA_MATCH)
    @patch("security_scanner.scan_with_clamav", return_value=CLEAN_RESULT)
    def test_rejected_when_yara_matches_even_if_clamav_clean(self, mock_clamav, mock_yara):
        # Proves the point of having two independent scanners: one
        # catching something the other missed still blocks the file.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notice.html"
            path.write_text("<h1>Notice</h1>", encoding="utf-8")

            result = inspect_file(path)

            self.assertFalse(result["accepted"])
            self.assertEqual(result["verdict"], "INFECTED")
            self.assertTrue(any(f.startswith("yara_match") for f in result["findings"]))


if __name__ == "__main__":
    unittest.main()