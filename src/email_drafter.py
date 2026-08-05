"""
Email drafter module. Converts an insights brief into a short sales pitch email
using GPT-4o-mini, optionally matching the user's writing style.
"""
from openai import OpenAI
import config
from src.provenance import format_provenance_block

EMAIL_DRAFT_MODEL = getattr(config, "EMAIL_DRAFT_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = """You are a sales email copywriter for a media company's commercial team. Your job is to write a short, compelling pitch email that gets a meeting booked with an advertiser.

Rules:
- Write 3-5 short paragraphs maximum
- Open with "Hi [Name]," as the greeting
- Hook their interest with 2-3 compelling data points from the brief — do NOT reproduce the entire brief
- End with a clear call-to-action to book a meeting or call
- Include a subject line on the first line in the format: Subject: <subject text>
- Be specific to the advertiser, topic, and KPI — avoid generic marketing language
- Keep the tone professional but warm and confident
- The email should feel like it was written by a knowledgeable human, not an AI"""

STYLE_SECTION = """

The user has provided sample emails they've previously sent. Match their writing style closely — their tone, sentence structure, greeting style, sign-off patterns, and level of formality. Here are their samples:

{samples}"""

USER_PROMPT_TEMPLATE = """Write a pitch email for the following:

**Advertiser:** {advertiser}
**Topic:** {topic}
**KPI:** {kpi}

Here is the full strategic insights brief to draw from (pick the most compelling 2-3 points, do NOT include everything):

{brief_content}"""


def draft_email(brief_content, topic, advertiser, kpi, writing_samples=None,
                provenance=None):
    """Generate a short sales pitch email from an insights brief.

    Args:
        brief_content: The full markdown insights brief.
        topic: The editorial topic.
        advertiser: The advertiser name.
        kpi: The campaign KPI.
        writing_samples: Optional list of sample email strings for style matching.
        provenance: Optional provenance entries from the brief run (#156).
            Appended verbatim beneath the drafted body, never handed to the
            model — the email quotes the brief's figures, so it has to carry
            the same account of where they came from, and a source line that
            passed through a copywriting prompt would be worth nothing.

    Returns:
        dict with 'subject' and 'body' keys.
    """
    system_prompt = SYSTEM_PROMPT
    if writing_samples:
        numbered = "\n\n".join(
            "--- Sample %d ---\n%s" % (i + 1, s) for i, s in enumerate(writing_samples)
        )
        system_prompt += STYLE_SECTION.format(samples=numbered)

    user_prompt = USER_PROMPT_TEMPLATE.format(
        advertiser=advertiser,
        topic=topic,
        kpi=kpi,
        brief_content=brief_content,
    )

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=EMAIL_DRAFT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=800,
    )

    raw = response.choices[0].message.content
    return _append_provenance(_parse_email(raw), provenance)


def _append_provenance(email, provenance):
    """Add the brief's source footer beneath the drafted body.

    Separated by a rule so it reads as a footnote to the pitch rather than part
    of it — the recipient of the pitch is not the reader this is for; the
    colleague checking a figure before it goes out is.
    """
    block = format_provenance_block(provenance)
    if not block:
        return email

    body = email["body"].rstrip()
    return {"subject": email["subject"], "body": "%s\n\n---\n%s" % (body, block)}


def _parse_email(raw):
    """Extract subject line and body from the LLM response."""
    lines = raw.strip().split("\n", 1)
    subject = ""
    body = raw.strip()

    if lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip()
        body = lines[1].strip() if len(lines) > 1 else ""

    return {"subject": subject, "body": body}
