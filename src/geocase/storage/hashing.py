"""Checksum utilities for verifying materialized remote artifacts.

The storage layer downloads artifacts described by a manifest and must confirm
that the bytes on disk match the ``sha256`` (and optional ``byte_size``) the
manifest declared. The manifest *declares* the expected checksum; this module
*verifies* the actual bytes — see
``docs/contributing/manifests-and-storage.md`` (§"Why checksums matter").
"""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_SIZE = 65536


class ChecksumMismatchError(Exception):
    """Raised when a file's SHA-256 does not match the expected digest."""


class SizeMismatchError(Exception):
    """Raised when a file's byte size does not match the expected size."""


def sha256_file(path: Path) -> str:
    """Return the hex SHA-256 digest of *path*.

    This is the single implementation: ``scripts/generate_checksums.py`` imports
    it, so bundled fixtures and remote artifacts are hashed identically.
    """
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksum(path: Path, expected_sha256: str) -> None:
    """Verify that *path* hashes to *expected_sha256*.

    Raises:
        ChecksumMismatchError: If the digests differ.
    """
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise ChecksumMismatchError(
            f"Checksum mismatch for {path}: "
            f"expected {expected_sha256}, got {actual}"
        )


def verify_size(path: Path, expected_bytes: int) -> None:
    """Verify that *path* is exactly *expected_bytes* long.

    Raises:
        SizeMismatchError: If the sizes differ.
    """
    actual = Path(path).stat().st_size
    if actual != expected_bytes:
        raise SizeMismatchError(
            f"Size mismatch for {path}: "
            f"expected {expected_bytes} bytes, got {actual}"
        )
