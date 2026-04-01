from openai import OpenAI

import config

SUMMARISER_PROMPT = """Summarise the following client brief into 2-3 concise sentences. Preserve key specifics: audience demographics, budget tier, timeline dates, campaign type, creative requirements, and stated objectives. Do not add information that is not in the original brief. If the input is already very short, return it largely unchanged.

Client brief:
{raw_brief}"""


def summarise_brief(raw_text):
    # type: (str) -> str
    """Summarise a client brief into 2-3 sentences via GPT-4o.

    Returns a fallback string if input is empty or whitespace-only.
    """
    if not raw_text or not raw_text.strip():
        return "No client brief provided."

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=config.CHAT_MODEL,
        messages=[
            {"role": "system", "content": "You are a concise summariser. Produce only the summary, nothing else."},
            {"role": "user", "content": SUMMARISER_PROMPT.format(raw_brief=raw_text.strip())},
        ],
        temperature=0.2,
        max_tokens=200,
    )

    return response.choices[0].message.content
