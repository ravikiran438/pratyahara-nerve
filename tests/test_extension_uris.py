# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Lock-in tests for NERVE's published extension URIs."""

from __future__ import annotations


def test_nerve_core_extension_uri():
    from nerve.types import NERVE_EXTENSION_URI
    assert NERVE_EXTENSION_URI == (
        "https://ravikiran438.github.io/pratyahara-nerve/v1"
    )


def test_yathartha_extension_uri():
    from nerve.extensions.yathartha import EXTENSION_URI
    assert EXTENSION_URI == (
        "https://github.com/ravikiran438/pratyahara-nerve/"
        "extensions/yathartha/v1"
    )
