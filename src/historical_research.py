import glob
import os
import re

import yaml

# Proprietary research catalogue. Markdown files with YAML frontmatter live
# here and are glob-loaded at runtime — dropping a new `.md` in the folder adds
# it to the catalogue with no code change (mirrors the skills/*.md pattern in
# src/web_search.py).
CATALOGUE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "historical_research")

# On a brief that matches no research file, the prompt placeholder carries this
# fallback so the model omits the Historical Research section entirely.
FALLBACK_TEXT = "No historical research matched this brief."


def load_catalogue(catalogue_dir=None):
    # type: (str) -> list
    """Glob-load every research file in the catalogue.

    Reuses the frontmatter-parsing pattern from ``src.web_search.load_skills``:
    split the leading YAML frontmatter from the markdown body, parse the
    frontmatter with ``yaml.safe_load``. Files without valid frontmatter are
    skipped. A missing/empty folder yields an empty list (graceful absence).

    Each returned dict carries the parsed ``meta`` frontmatter, the verbatim
    ``body``, and the file's vocabulary split by role: ``topics`` +
    ``match_keywords`` say what the research is about, ``audience_terms`` say
    who was surveyed. Only the first kind can admit a file (see
    ``get_relevant_research``), so a term named as an audience term is stripped
    out of ``topics``/``match_keywords`` wherever it also appears there — a
    mis-authored file cannot smuggle a demographic back in as a subject.
    ``meta`` keeps the frontmatter verbatim either way.
    """
    if catalogue_dir is None:
        catalogue_dir = CATALOGUE_DIR

    files = []
    for path in sorted(glob.glob(os.path.join(catalogue_dir, "*.md"))):
        with open(path) as f:
            raw = f.read()

        # Split YAML frontmatter from the markdown body.
        match = re.match(r"^---\n(.+?)\n---\n(.+)", raw, re.DOTALL)
        if not match:
            continue

        meta = yaml.safe_load(match.group(1)) or {}
        body = match.group(2).strip()

        topics = meta.get("topics") or []
        match_keywords = meta.get("match_keywords") or []
        audience_terms = meta.get("audience_terms") or []

        demographic = set(_normalise(t) for t in audience_terms)
        demographic.discard("")

        def subject_only(terms):
            return [t for t in terms if _normalise(t) not in demographic]

        files.append({
            "meta": meta,
            "body": body,
            "topics": subject_only(topics),
            "match_keywords": subject_only(match_keywords),
            "audience_terms": list(audience_terms),
            "file": os.path.basename(path),
        })

    return files


def _normalise(term):
    # type: (str) -> str
    """Lowercase and trim a catalogue term so the two roles compare like for like."""
    return (term or "").strip().lower()


def _find_matches(brief_text, needles):
    # type: (str, list) -> list
    """Return the needles that appear in ``brief_text`` on a word boundary.

    Word-boundary matching (not bare substring) keeps the gate honest: the
    keyword "rail" matches "rail" but not "email", and the phrase "city breaks"
    matches only when both words appear together. Deterministic — no LLM.
    """
    hits = []
    for needle in needles:
        needle = _normalise(needle)
        if not needle or needle in hits:
            continue  # de-dupe: a term can sit in both topics and match_keywords
        pattern = r"\b" + re.escape(needle) + r"\b"
        if re.search(pattern, brief_text):
            hits.append(needle)
    return hits


def get_relevant_research(topic, advertiser, client_brief, catalogue_dir=None):
    # type: (str, str, str, str) -> dict
    """Deterministic relevance gate over the research catalogue.

    Concatenates ``topic + advertiser + client_brief`` (lowercased) and tests it
    against each file's vocabulary. No LLM, no network — reproducible every run.

    Admission turns on subject relevance alone: a file is included only when the
    brief overlaps its ``topics``/``match_keywords``, which describe what the
    research is *about*. Its ``audience_terms`` — who was surveyed — can never
    admit a file on their own, because sharing a demographic is not a reason to
    include research on an unrelated subject (a hearing-aids brief aimed at
    over-55s was pulling in travel research; #157). Where the brief shares the
    demographic *as well*, those terms still ride along in ``matched_on``, so
    the hero card can show the full overlap without it having been the reason.

    Always returns a dict with ``relevant`` and ``prompt_text``. On a match it
    also carries verbatim frontmatter metadata (``title``, ``organisation``,
    ``fieldwork``, ``total_respondents``, ``matched_on``) for the hero card.
    """
    brief_text = " ".join([topic or "", advertiser or "", client_brief or ""]).lower()

    for f in load_catalogue(catalogue_dir):
        subject_hits = _find_matches(brief_text, f["topics"] + f["match_keywords"])
        if not subject_hits:
            continue  # no subject overlap — a shared demographic cannot stand in

        audience_hits = [
            hit for hit in _find_matches(brief_text, f["audience_terms"])
            if hit not in subject_hits
        ]
        matched_on = subject_hits + audience_hits

        meta = f["meta"]
        start = str(meta.get("fieldwork_start", "") or "")
        end = str(meta.get("fieldwork_end", "") or "")
        if start and end:
            fieldwork = "%s to %s" % (start, end)
        else:
            fieldwork = start or end
        return {
            "relevant": True,
            "prompt_text": f["body"],
            # Identifies the matched catalogue file so a downstream consumer
            # (the deck) can re-read the same body from load_catalogue()
            # rather than the body being shipped to the client and back.
            "file": f["file"],
            "title": meta.get("title", ""),
            "organisation": meta.get("organisation", ""),
            "fieldwork": fieldwork,
            "total_respondents": meta.get("total_respondents"),
            "matched_on": matched_on,
        }

    return {
        "relevant": False,
        "prompt_text": FALLBACK_TEXT,
    }


def load_research_body(research, catalogue_dir=None):
    # type: (dict, str) -> str
    """Return the verbatim body of the research file a brief matched.

    The deck download posts the matched-research payload back to the server
    with the body stripped out (only ``file`` identifies it), so the body is
    re-read here from the same catalogue the brief matched against. Returns ""
    when nothing matched, which is the signal to omit the section entirely.
    """
    if not research or not research.get("relevant"):
        return ""

    if research.get("prompt_text"):
        return research["prompt_text"]

    filename = research.get("file")
    if not filename:
        return ""

    for f in load_catalogue(catalogue_dir):
        if f["file"] == filename:
            return f["body"]
    return ""
