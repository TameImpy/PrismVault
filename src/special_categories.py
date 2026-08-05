"""Recognition of GDPR Article 9 special-category audience requests (issue #164).

The Assistant used to send these requests to the audience team by accident: it
found no segments, fell through its generic "I don't know" rule, and that rule
happens to point at the audience team. Nothing distinguished "I don't have this"
from "this is special category data", so a differently worded request for the
same thing could have come back with segments.

This module makes the distinction explicit and deterministic. `detect_special_category`
is the gate; `SPECIAL_CATEGORY_MESSAGE` is what the user gets instead of segments;
`SPECIAL_CATEGORY_PROMPT_RULE` carries the same rule into the model's system prompt
so wordings the term list misses still land on the same message rather than on the
generic fallback.

Four deliberate boundaries, because over-blocking legitimate queries is a real cost:

1. **Conditions, not lifestyles.** "Hearing loss" and "diabetes" are health data
   about a person. "Health conscious foodies", "gym members" and "gluten free"
   are content-affinity segments the catalogue actually sells. Only the former
   trip the gate.
2. **Naming an advertiser is not naming an audience.** Charities are named after
   the thing they fight, so "segments for Cancer Research UK" is a brief about a
   client, not a request to target people by diagnosis. `_ORGANISATION_NAMES`
   removes the organisation before matching; the rest of the request is still
   scanned, so "cancer patients for Cancer Research UK" is blocked.
3. **Terms are qualified wherever the bare word has an innocent reading here.**
   "Christian Dior" is a fashion brief, "Brexit anniversary" is an editorial
   topic, "South Asian cooking" is a cuisine, and "over the counter medication
   buyers" is a shopper segment. Halal and kosher are absent for the same reason.
4. **Pregnancy is not in the term list**, even though it is health data, because
   the catalogue sells Pregnancy Fans / Conception & Early Pregnancy segments
   today. Blocking it would withdraw a live product on an engineering decision.
   That is a commercial and legal call, not one to slip in here — see
   LESSONS_LEARNED.md.

Where a proxy is tight enough that the request is really about the condition, it
stays blocked even when it looks commercially ordinary: "audiences for a hearing
aid brand" is #164's own example wearing a client's hat.

`test_special_categories.py` sweeps the whole segment catalogue through the gate
and fails if any sellable segment trips it, and pins both directions — realistic
phrasings that must block and advertiser briefs that must not — so the term list
cannot drift either way unnoticed.
"""

import re

# The exact wording agreed in the QA debrief (decision D10, issue #154). It names
# why the request is restricted rather than reading as a dead end.
SPECIAL_CATEGORY_MESSAGE = (
    "I'm afraid the audiences you're asking about may fall into more sensitive "
    "categories that we have to be more careful about — things like health, "
    "ethnicity or beliefs. Please get in touch with the audience team at "
    "dl-audience-ads@immediate.co.uk to talk through this and what other options "
    "might work."
)

# Terms are matched on word boundaries, case-insensitively, so "gay" does not fire
# on "Gaynor" and "hiv" does not fire on "chives". Multi-word phrases are preferred
# over bare words wherever the bare word has an innocent reading in this catalogue
# ("political podcast" must not fire; "political affiliation" must).
_SPECIAL_CATEGORY_TERMS = [
    (
        "health",
        [
            # Sensory and physical
            r"hearing loss", r"hearing impair\w*", r"hard of hearing", r"hearing aids?",
            r"hearing difficult\w+", r"trouble hearing", r"deaf",
            r"sight (?:loss|problems?|difficult\w+)", r"vision problems?",
            r"partially sighted", r"visually impaired",
            r"registered blind", r"wheelchair users?", r"mobility impair\w*",
            # Diagnoses and conditions
            r"disabilit\w+", r"disabled", r"diabet\w+", r"cancer", r"asthma",
            r"arthritis", r"dementia", r"alzheimer\w*", r"parkinson\w*",
            r"epilep\w+", r"multiple sclerosis", r"hiv",
            r"stroke survivors?", r"stroke patients?", r"had a stroke",
            r"heart (?:disease|condition)", r"blood pressure",
            r"chronic (?:illness|condition|pain)",
            r"long[- ]term (?:illness|condition)", r"medical condition",
            r"health condition", r"coeliac", r"celiac", r"crohn\w*",
            r"incontinence", r"obesity", r"menopaus\w+", r"infertility",
            r"ivf", r"fertility treatment\w*",
            r"eating disorders?", r"addiction", r"alcoholism",
            r"recovering alcoholics?", r"alcohol (?:addiction|dependenc\w+|misuse)",
            # Mental health and neurodivergence
            r"mental health", r"depression", r"antidepressants?",
            r"anxiety disorder", r"bipolar", r"schizophren\w+", r"adhd",
            r"autis\w+", r"neurodiver\w+", r"dyslexi\w+", r"dyspraxi\w+",
            # Care, treatment, diagnosis. Qualified rather than bare: "medication"
            # and "symptoms" alone block shopper segments an OTC brand legitimately
            # wants ("over the counter medication buyers"), which is a request about
            # a purchase, not about anyone's condition.
            r"diagnosed with", r"diagnosis", r"patients?", r"sufferers?",
            r"on medication", r"taking medication", r"prescription medicine",
            r"prescribed \w+", r"illnesse?s",
        ],
    ),
    (
        "racial or ethnic origin",
        [
            r"ethnicit\w+", r"ethnic (?:origin|background|group|minorit\w+)",
            r"minority ethnic", r"racial\w*", r"by race", r"race or ethnic\w*",
            r"bame", r"beme", r"multicultural", r"people of colou?r",
            r"black (?:audiences?|consumers?|households?|britons?|british"
            r"|readers?|families|communit\w+|women|men)",
            r"(?:south )?asian (?:audiences?|consumers?|households?|communit\w+"
            r"|families|readers?)",
            r"afro[- ]caribbean", r"hispanic", r"latino", r"caucasian",
            # "South Asian cooking" is a cuisine; "of Indian heritage" is an origin.
            r"(?:indian|asian|african|caribbean|chinese|jewish|irish|polish) heritage",
        ],
    ),
    (
        "religious or philosophical beliefs",
        [
            r"religion", r"religious\w*", r"faith groups?", r"muslims?", r"islamic",
            r"catholics?", r"protestants?", r"jewish", r"judaism",
            r"hindus?", r"sikhs?", r"buddhists?", r"atheists?",
            r"churchgoers?", r"(?:go(?:es|ing)?|went) to church",
            r"(?:attends?|attending) church", r"church attend\w*",
            r"mosques?", r"synagogues?",
            # Plural or qualified only: bare "christian" is a first name, and
            # "Christian Dior shoppers" is a fashion brief, not a faith one.
            r"christians", r"christian (?:audiences?|families|households|faith"
            r"|readers?|communit\w+|voters?)",
            # Halal and kosher are deliberately absent: in this catalogue they read
            # as dietary shopper segments, and the rule here is conditions and
            # identities, not the food someone buys.
        ],
    ),
    (
        "political opinions",
        [
            r"political (?:affiliation|belief\w*|opinion\w*|leaning\w*|view\w*|part(?:y|ies))",
            r"voting intention\w*", r"voters?",
            r"(?:who |people who |they )?vote (?:green|labour|conservative|reform|lib dem)",
            r"labour supporters?", r"conservative (?:voters?|supporters?)",
            r"tor(?:y|ies)", r"lib dem\w*", r"reform uk",
            # "Brexit" alone is an editorial topic here; only the vote is an opinion.
            r"brexit voters?", r"leave voters?", r"remain voters?",
            r"left[- ]wing", r"right[- ]wing",
        ],
    ),
    (
        "trade union membership",
        [r"trade unions?", r"union member\w*", r"unionised", r"unionized"],
    ),
    (
        "sex life or sexual orientation",
        [
            r"sexual (?:orientation|preference)", r"sexualit\w+", r"lgbt\w*",
            r"gay", r"lesbian", r"queer", r"bisexual", r"transgender",
            r"non[- ]binary", r"sex life",
        ],
    ),
    (
        "genetic or biometric data",
        [
            r"genetic\w*", r"genomic\w*", r"dna test\w*", r"biometric\w*",
            r"facial recognition", r"fingerprints?",
        ],
    ),
]

_CATEGORY_PATTERNS = [
    (category, re.compile(r"\b(?:%s)\b" % "|".join(terms), re.IGNORECASE))
    for category, terms in _SPECIAL_CATEGORY_TERMS
]

# Charities and campaigns are named after the thing they fight, and the advertiser
# is a first-class field in this product: "segments for Cancer Research UK" names an
# advertiser, not an audience. Organisation names are removed before matching so the
# condition inside them cannot trip the gate — while anything else in the request
# still can, which is why "cancer patients for Cancer Research UK" is still blocked.
_ORGANISATION_NAMES = re.compile(
    r"\b[\w'’-]+(?:\s+[\w'’-]+)?\s+"
    r"(?:research uk|society|association|foundation|trust|charity|appeal|institute)\b",
    re.IGNORECASE,
)

SPECIAL_CATEGORY_PROMPT_RULE = """
## Special category data (UK GDPR Article 9)

Some audience requests concern special category personal data: health or medical
conditions, racial or ethnic origin, religious or philosophical beliefs, political
opinions, trade union membership, sex life or sexual orientation, and genetic or
biometric data. Targeting on these requires a specific lawful condition that is
not in place here.

If a request concerns any of them, do NOT search for or list segments, and do NOT
use your general "I don't know" answer. Reply with exactly this message and nothing
else:

%s

This is different from not knowing the answer, so never present it as a gap in the
knowledge base. Ordinary lifestyle and interest audiences are not special category
data — content affinities such as healthy eating, fitness, gluten free or parenting
are fine to answer normally.
""" % SPECIAL_CATEGORY_MESSAGE


def _as_text(value):
    """Flatten a message `content` value to searchable text.

    OpenAI allows `content` to be a list of parts rather than a plain string
    (multi-part and vision messages). A list is truthy, so it would sail past a
    falsy-check and reach `re.search`, which raises TypeError on a non-string —
    a gate that crashes on an input shape is a gate that isn't applied. Flatten
    instead, so an unfamiliar shape is still scanned rather than skipped.
    """
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # A content part: {"type": "text", "text": "..."} — scan every value, so
        # a part keyed differently is still read rather than silently dropped.
        return " ".join(_as_text(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return " ".join(_as_text(v) for v in value)
    return str(value)


def detect_special_category(text):
    """Return the Article 9 category `text` concerns, or None.

    The return value is the category name (e.g. "health"), which callers use to
    prove the special-category path fired rather than the generic fallback.
    Accepts any message `content` shape, not only a string — see `_as_text`.
    """
    text = _ORGANISATION_NAMES.sub(" ", _as_text(text))
    if not text:
        return None
    for category, pattern in _CATEGORY_PATTERNS:
        if pattern.search(text):
            return category
    return None
