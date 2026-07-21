"""Tests for the alias-table + unmatched-log artefact I/O.

These cover the file-facing helpers: loading the reactive alias table into
the normalised dict the resolver expects, and appending unmatched /
near-matched queries to the growth log.
"""

import os
import csv
import tempfile

from src.alias_table import load_aliases, log_unmatched


def test_load_aliases_normalises_keys():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "brand_aliases.csv")
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["alias", "canonical"])
            writer.writeheader()
            writer.writerow({"alias": "Coke", "canonical": "Coca-Cola"})
            writer.writerow({"alias": "", "canonical": ""})  # blank row ignored

        aliases = load_aliases(path)

        # Keys are normalised so the resolver can look them up directly.
        assert aliases == {"coke": "Coca-Cola"}


def test_load_aliases_missing_file_returns_empty():
    assert load_aliases("/nonexistent/aliases.csv") == {}


def test_log_unmatched_appends_row():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "unmatched_brands.csv")

        log_unmatched("Weirdbrand", "no_match", [], path=path, timestamp="2026-07-21T10:00:00")
        log_unmatched("Virgin", "possible_match",
                      ["Virgin Media", "Virgin Atlantic"],
                      path=path, timestamp="2026-07-21T10:05:00")

        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))

        assert len(rows) == 2
        assert rows[0]["queried_brand"] == "Weirdbrand"
        assert rows[0]["status"] == "no_match"
        assert rows[1]["queried_brand"] == "Virgin"
        assert rows[1]["status"] == "possible_match"
        assert "Virgin Media" in rows[1]["candidates"]


def test_log_unmatched_creates_file_with_header():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "log.csv")

        log_unmatched("Foo", "no_match", [], path=path, timestamp="2026-07-21T00:00:00")

        assert os.path.exists(path)
        with open(path, newline="") as f:
            header = f.readline().strip()
        assert header == "timestamp,queried_brand,status,candidates"
