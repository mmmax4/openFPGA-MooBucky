#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Shared fail-fast checks for Analogue Pocket package generators."""

from pathlib import PurePath
from typing import Any, Mapping


MAX_BITSTREAM_FILENAME_LENGTH = 15
BITSTREAM_SUFFIX = ".rbf_r"


def validate_bitstream_filename(filename: str) -> None:
    """Reject bitstream names that the Pocket framework cannot resolve."""
    if not filename or PurePath(filename).name != filename:
        raise SystemExit("cores[].filename must be a plain bitstream filename")
    if not filename.endswith(BITSTREAM_SUFFIX):
        raise SystemExit(f"cores[].filename must end with {BITSTREAM_SUFFIX}")
    if len(filename) > MAX_BITSTREAM_FILENAME_LENGTH:
        raise SystemExit(
            "cores[].filename exceeds the Analogue Pocket 15-character "
            f"limit including .rbf_r: {filename!r} ({len(filename)} characters)"
        )


def validate_core_folder_identity(
    folder_name: str, core_manifest: Mapping[str, Any]
) -> None:
    """Require Cores/<folder> to equal metadata.author + metadata.shortname."""
    if not folder_name or PurePath(folder_name).name != folder_name or \
       "/" in folder_name or "\\" in folder_name:
        raise SystemExit("core folder identity must be a plain folder name")

    try:
        metadata = core_manifest["core"]["metadata"]
        author = metadata["author"]
        shortname = metadata["shortname"]
    except (KeyError, TypeError):
        raise SystemExit(
            "core.json must define core.metadata.author and "
            "core.metadata.shortname"
        ) from None

    for field_name, value in (("author", author), ("shortname", shortname)):
        if not isinstance(value, str) or not value or \
           "/" in value or "\\" in value:
            raise SystemExit(
                f"core.metadata.{field_name} must be a non-empty plain name"
            )

    expected = f"{author}.{shortname}"
    if folder_name != expected:
        raise SystemExit(
            "core folder identity mismatch: "
            f"Cores/{folder_name}/ != metadata.author + metadata.shortname "
            f"({expected!r})"
        )
