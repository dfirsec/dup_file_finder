"""Checks the file signature of a file against a list of expected values."""

import json
import mimetypes
from pathlib import Path


class FileSignatureChecker:
    """File signature checker class."""

    def __init__(self: "FileSignatureChecker", filepath: str, extension: str) -> None:
        """Initialize class instance variables."""
        self.filepath = filepath
        self.extension = extension
        self.file_sigs = self.load_file_signatures()
        self.expected_signature, self.expected_offset = self.get_expected_signature()
        self.expected_mime = None

    def load_file_signatures(self: "FileSignatureChecker") -> dict:
        """Loads the file signatures."""
        file_sigs_path = Path(__file__).resolve().parent.joinpath("file_signatures.json")
        with open(file_sigs_path, encoding="utf-8") as json_file:
            return json.load(json_file)

    def read_file_signature(self: "FileSignatureChecker", filepath: str, expected_sig: bytes, offset: int) -> bool:
        """Reads the file signature at a given offset.

        Args:
            filepath (str): Path to the file to read.
            expected_sig (bytes): Expected file signature.
            offset (int): Offset to read the file signature from.

        Returns:
            bool: True if the file signature matches the expected value, False otherwise.
        """
        with open(filepath, "rb") as file:
            file.seek(offset)
            signature = file.read(len(expected_sig))

        # Compare the signature with the expected value
        return signature == expected_sig

    def check_file_signature(self: "FileSignatureChecker") -> bool | None:
        """Checks the file signature against a list of expected values.

        Returns:
            bool: True if the file signature matches any of the expected values, False otherwise.
        """
        if not self.expected_signature or self.expected_offset is None:
            return False
        return any(self.read_file_signature(self.filepath, sig, self.expected_offset) for sig in self.expected_signature)

    def get_expected_signature(self: "FileSignatureChecker") -> tuple:
        """Gets the expected file signature and offset for a given file extension.

        Returns:
            tuple | None: Tuple containing the expected file signature and offset,
            or None if the file extension is not recognized.
        """
        for item in self.file_sigs:
            if item["extension"] == self.extension:
                signatures = [bytes.fromhex(sig.replace(" ", "")) for sig in item["signature"]]
                offset = item.get("offset", 0)
                return signatures, offset
        return [], None

    def check_mime_type(self: "FileSignatureChecker") -> bool:
        """Checks the MIME type of a file against a list of expected values.

        Returns:
            bool: True if MIME type matches any of the expected values, False otherwise.
        """
        if self.expected_mime is None:
            self.expected_mime = mimetypes.guess_type(self.filepath)[0]
        return self.expected_mime == mimetypes.guess_type(self.filepath)[0]

    def check_file_extension(self: "FileSignatureChecker") -> bool:
        """Checks the file extension of a file against a list of expected values.

        Returns:
            bool: True if file extension matches any of the expected values, False otherwise.
        """
        return bool(self.expected_signature and self.expected_offset is not None)

    def check_file(self: "FileSignatureChecker") -> bool | str:
        """Checks the file signature, MIME type, and file extension of a file.

        Returns:
            str: Results of the file signature, MIME type, and file extension checks.
        """
        if not self.check_file_extension():
            return False
        return bool(self.check_file_signature() and self.check_mime_type())
