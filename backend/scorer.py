import os
import json
import anthropic
from rubric import CRITERIA

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

SYSTEM_PROMPT = """You are a QA specialist auditing Customer Operations Support (COS) calls at a food-ordering company called Wonders. Your job is to score a call transcript against a 12-criterion rubric.

Score each criterion 1, 2, or 3:
- 1 = Poor
- 2 = Acceptable
- 3 = Excellent

RUBRIC:
{rubric}

IMPORTANT RULES:
- If a criterion is clearly not applicable (e.g. Mandarin proficiency when the client speaks English), score it 3 as instructed in the notes.
- For ticket documentation (2e), you can only assess what's visible in the transcript — if ticket actions are not mentioned, note that in the justification and score 2.
- Be fair but rigorous. Score 2 unless there's clear evidence of excellence (3) or failure (1).
- Respond ONLY with a valid JSON object. No markdown, no extra text.

RESPONSE FORMAT:
{{
  "1a": {{"score": <1|2|3>, "justification": "<one sentence>"}},
  "1b": {{"score": <1|2|3>, "justification": "<one sentence>"}},
  "1c": {{"score": <1|2|3>, "justification": "<one sentence>"}},
  "1d": {{"score": <1|2|3>, "justification": "<one sentence>"}},
  "2a": {{"score": <1|2|3>, "justification": "<one sentence>"}},
  "2b": {{"score": <1|2|3>, "justification": "<one sentence>"}},
  "2c": {{"score": <1|2|3>, "justification": "<one sentence>"}},
  "2d": {{"score": <1|2|3>, "justification": "<one sentence>"}},
  "2e": {{"score": <1|2|3>, "justification": "<one sentence>"}},
  "3a": {{"score": <1|2|3>, "justification": "<one sentence>"}},
  "3b": {{"score": <1|2|3>, "justification": "<one sentence>"}},
  "3c": {{"score": <1|2|3>, "justification": "<one sentence>"}}
}}"""


def _build_rubric_text() -> str:
    lines = []
    for c in CRITERIA:
        lines.append(
            f"{c['id']} — {c['name']} (weight {int(c['weight']*100)}%)\n"
            f"  1: {c['score_1']}\n"
            f"  2: {c['score_2']}\n"
            f"  3: {c['score_3']}\n"
            f"  Notes: {c['scoring_notes']}"
        )
    return "\n\n".join(lines)


def score_transcript(transcript: str) -> dict:
    """Return AI scores for each criterion. Each value: {score, justification}."""
    if not transcript or not transcript.strip():
        return {
            c["id"]: {"score": 2, "justification": "No transcript available for this call."}
            for c in CRITERIA
        }

    system = SYSTEM_PROMPT.format(rubric=_build_rubric_text())
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system,
        messages=[
            {
                "role": "user",
                "content": f"Score this call transcript:\n\n{transcript[:8000]}",
            }
        ],
    )

    text = message.content[0].text.strip()
    return json.loads(text)
