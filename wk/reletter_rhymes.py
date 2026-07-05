#!/usr/bin/env python3
"""Reletter rhyme labels and print the original and new labels."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


DEFAULT_INPUT = Path(__file__).with_name("letters_to_change.txt")


def label_number(label: str) -> int:
    """Convert a, ..., z, aa, ab, ... to a one-based number."""
    number = 0
    for character in label:
        number = number * 26 + ord(character) - ord("a") + 1
    return number


def label_from_number(number: int) -> str:
    """Convert a one-based number to a, ..., z, aa, ab, ... form."""
    characters: list[str] = []
    while number:
        number, remainder = divmod(number - 1, 26)
        characters.append(chr(ord("a") + remainder))
    return "".join(reversed(characters))


def following(label: str) -> str:
    return label_from_number(label_number(label) + 1)


def assign(
    mapping: dict[str, str], active: set[str], source: str, target: str
) -> None:
    """Assign target, pushing a current owner and any ensuing collisions."""
    owner = next(
        (
            key
            for key, value in mapping.items()
            if key in active and key != source and value == target
        ),
        None,
    )
    mapping[source] = target
    if owner is not None:
        assign(mapping, active, owner, following(target))


def reletter(
    labels: list[str], first_new_letter: str, window: int = 5
) -> list[str]:
    mapping: dict[str, str] = {}
    previous_occurrence: dict[str, int] = {}
    used: set[str] = set()
    active: set[str] = set()
    result: list[str] = []
    first_change = True

    for line_number, source in enumerate(labels, 1):
        mapping.setdefault(source, source)
        if source not in active:
            # A label is not free merely because its previous owner has since
            # moved: once emitted anywhere above, it cannot be reused.
            while mapping[source] in used:
                mapping[source] = following(mapping[source])
            active.add(source)

        previous = previous_occurrence.get(source)
        if (
            previous is not None
            and line_number - previous > window
        ):
            if first_change:
                target = first_new_letter
                first_change = False
            else:
                target = first_new_letter
                while target in used:
                    target = following(target)
            assign(mapping, active, source, target)

        new_label = mapping[source]
        result.append(new_label)
        used.add(new_label)
        previous_occurrence[source] = line_number

    return result


def read_labels(path: Path) -> list[str]:
    labels = path.read_text(encoding="utf-8").splitlines()
    for number, label in enumerate(labels, 1):
        if not label.isascii() or not label.isalpha() or not label.islower():
            raise ValueError(
                f"line {number}: expected a lowercase ASCII label, got {label!r}"
            )
    return labels


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reletter every recurrence outside the line window and emit "
            "tab-separated original and new labels."
        )
    )
    parser.add_argument(
        "first_new_letter",
        help="first label to use for a rewrite (for example: k)",
    )
    parser.add_argument(
        "input", nargs="?", type=Path, default=DEFAULT_INPUT,
        help="default: wk/letters_to_change.txt",
    )
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--window", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = arguments()
    if args.window < 0:
        raise ValueError("--window must be non-negative")
    if (
        not args.first_new_letter.isascii()
        or not args.first_new_letter.isalpha()
        or not args.first_new_letter.islower()
    ):
        raise ValueError("first_new_letter must be a lowercase ASCII label")

    original = read_labels(args.input)
    changed = reletter(original, args.first_new_letter, args.window)
    text = "".join(f"{old}\t{new}\n" for old, new in zip(original, changed))

    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
