"""gators-verse: rhyme and stanza analysis of Galician poetry (GATORS, Galician Tool for Rhyme and Stanza).

Two steps:

- :func:`transcribe` transcribes verse lines with trasgo.
- :func:`annotate` takes a table of verses with their transcription (and,
  optionally, their metre) and adds rhyme letters, verse, stanza and poem types.

The ``gators-verse`` command runs both, and uses gama-verse, when installed,
for spelling normalization and metre.
"""

__version__ = "0.1.0"

from .annotate import annotate  # noqa: E402
from .transcribe import transcribe  # noqa: E402

__all__ = ["annotate", "transcribe"]
