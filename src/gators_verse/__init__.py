"""gators-verse: rhyme and stanza analysis of Galician poetry (GATORS, Galician Tool for Rhyme and Stanza).

- :func:`analyze` runs the whole analysis from the text: spelling
  normalization and meter with gama-verse (when installed), transcription
  with trasgo, and annotation. The ``gators-verse`` command calls it.
- :func:`transcribe` and :func:`annotate` are its last two steps, for input
  that already has its meter or transcription.
"""

__version__ = "1.0.0"

from .annotation import annotate  # noqa: E402
from .pipeline import analyze  # noqa: E402
from .transcription import transcribe  # noqa: E402

__all__ = ["analyze", "annotate", "transcribe"]
