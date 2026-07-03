from __future__ import annotations

import unittest

from forensics import _validate_upload
from web_forensics import _validate_public_url


class SecurityGuardTests(unittest.TestCase):
    def test_url_blocks_private_targets(self) -> None:
        self.assertIn("IP", _validate_public_url("http://127.0.0.1/"))
        self.assertTrue(_validate_public_url("http://localhost/admin"))

    def test_url_blocks_credentials_and_non_standard_ports(self) -> None:
        self.assertIn("사용자", _validate_public_url("https://user:pass@example.com/"))
        self.assertIn("포트", _validate_public_url("https://example.com:8443/"))

    def test_upload_validation_rejects_signature_mismatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid PDF"):
            _validate_upload("evidence.pdf", b"not a pdf")
        with self.assertRaisesRegex(ValueError, "Invalid PNG"):
            _validate_upload("capture.png", b"not a png")
        with self.assertRaisesRegex(ValueError, "Invalid JPEG"):
            _validate_upload("scan.jpg", b"not a jpeg")

    def test_upload_validation_accepts_expected_signatures(self) -> None:
        _validate_upload("evidence.pdf", b"%PDF-1.7\n")
        _validate_upload("capture.png", b"\x89PNG\r\n\x1a\n")
        _validate_upload("scan.jpg", b"\xff\xd8\xff\xe0")


if __name__ == "__main__":
    unittest.main()
