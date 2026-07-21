"""Artefact I/O for the reactive alias table and the unmatched-brand log.

The alias table (``data/brand_aliases.csv``) is small, manually maintained,
and NOT pre-populated — entries are added in response to observed misses. The
unmatched log (``data/unmatched_brands.csv``) records queries that no-matched
or possible-matched, so the alias table can grow from real misses rather than
guesswork and to feed the entity-resolution limitations review.

The resolver itself stays pure; this module is the file-facing edge that loads
the alias dict and appends log rows.
"""

import csv
import os

from src.entity_resolution import normalise_name

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DEFAULT_ALIASES_PATH = os.path.join(DATA_DIR, "brand_aliases.csv")
DEFAULT_UNMATCHED_LOG_PATH = os.path.join(DATA_DIR, "unmatched_brands.csv")

LOG_FIELDNAMES = ["timestamp", "queried_brand", "status", "candidates"]


def load_aliases(path=None):
    # type: (str) -> dict
    """Load the alias table as ``{normalised_alias: canonical_name}``.

    Keys are normalised with the resolver's own ``normalise_name`` so lookups
    line up. Blank rows are skipped. Missing file → empty dict.
    """
    if path is None:
        path = DEFAULT_ALIASES_PATH
    if not os.path.exists(path):
        return {}

    aliases = {}
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            alias = (row.get("alias") or "").strip()
            canonical = (row.get("canonical") or "").strip()
            if not alias or not canonical:
                continue
            aliases[normalise_name(alias)] = canonical
    return aliases


def log_unmatched(queried_brand, status, candidates=None, path=None, timestamp=None):
    # type: (str, str, list, str, str) -> None
    """Append an unmatched / near-matched query to the growth log.

    ``timestamp`` is injectable for deterministic tests; it defaults to the
    current UTC time. Creates the file (with header) on first write.
    """
    if path is None:
        path = DEFAULT_UNMATCHED_LOG_PATH
    if timestamp is None:
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).isoformat()

    candidates_str = "; ".join(candidates or [])
    write_header = not os.path.exists(path)

    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow({
            "timestamp": timestamp,
            "queried_brand": queried_brand,
            "status": status,
            "candidates": candidates_str,
        })
