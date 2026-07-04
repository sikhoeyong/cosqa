import os
import io
import json
import base64
import requests
from pydub import AudioSegment
from openai import OpenAI
import rubric as _rubric

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

SYSTEM_PROMPT = """You are a QA specialist auditing Customer Operations Support (COS) calls at a food-ordering company called Wonders. Your job is to listen to a call recording and score it against a 12-criterion rubric.

Score each criterion 1, 2, or 3:
- 1 = Poor
- 2 = Acceptable
- 3 = Excellent

CALL TYPE: {call_type_desc}

RUBRIC:
{rubric}

IMPORTANT RULES:
- If a criterion is clearly not applicable (e.g. Mandarin proficiency when the client speaks English), score it 3 as instructed in the notes.
- For ticket documentation (2e): WIRA ticket data will be provided if available. Use it to assess whether the agent documented correctly. If no WIRA ticket data is provided and ticket actions are not mentioned in the recording, set score to null (cannot assess). Only score 2e when you have actual evidence to work with.
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
  "2e": {{"score": <1|2|3|null>, "justification": "<one sentence>"}},
  "3a": {{"score": <1|2|3>, "justification": "<one sentence>"}},
  "3b": {{"score": <1|2|3>, "justification": "<one sentence>"}},
  "3c": {{"score": <1|2|3>, "justification": "<one sentence>"}}
}}"""


def _build_rubric_text() -> str:
    lines = []
    for c in _rubric._load():
        lines.append(
            f"{c['id']} — {c['name']} (weight {int(c['weight']*100)}%)\n"
            f"  1: {c['score_1']}\n"
            f"  2: {c['score_2']}\n"
            f"  3: {c['score_3']}\n"
            f"  Notes: {c['scoring_notes']}"
        )
    return "\n\n".join(lines)


AUDIO_URL = "https://greendot.prod.letsdowonders.io/greendot/greendot-rust/call/{call_id}/audio"


def score_audio(call_id: str, transcript_zh: str = "", is_chinese_assistant: bool = False, wira_tickets: list = None) -> dict:
    """Download recording, convert FLAC→MP3, score via gpt-audio."""
    resp = requests.get(AUDIO_URL.format(call_id=call_id), timeout=60)
    resp.raise_for_status()
    seg = AudioSegment.from_file(io.BytesIO(resp.content), format="flac")
    mp3_buf = io.BytesIO()
    seg.export(mp3_buf, format="mp3")
    audio_b64 = base64.b64encode(mp3_buf.getvalue()).decode()

    if is_chinese_assistant:
        call_type_desc = (
            "CHINESE ASSISTANT CALL — the agent speaks English with a dispatcher, then makes an outbound Mandarin call to a restaurant owner. "
            "CRITERION 1a RULE FOR THIS CALL TYPE: score 3 if (a) the agent answered the dispatcher with any English greeting, AND (b) the agent opened the Mandarin segment with '老板你好/老板娘你好' AND stated the 食客通 brand name. "
            "Do NOT require restaurant name or '我是[name]' — those rules apply only to client calls. "
            "IMPORTANT: 食客通 (Shí Kè Tōng) is frequently garbled in recordings. Accept any phonetically similar attempt: '十个通', '十客通', '食可通', '实客通', '十个通话', or any ~3-syllable phrase in that position. "
            "The pattern '老板娘你好，这是[anything 2-4 syllables]' = brand name credited. Only penalise if 食客通 is completely absent from the greeting."
        )
    else:
        call_type_desc = (
            "CLIENT CALL — the agent calls a restaurant owner directly, primarily in Mandarin. "
            "CRITERION 1a RULE: score 3 if the agent stated the restaurant name AND introduced themselves with any name (我是[any name]). "
            "Score 2 if only the restaurant name was stated. Score 1 if neither was present."
        )
    system = SYSTEM_PROMPT.format(rubric=_build_rubric_text(), call_type_desc=call_type_desc)
    user_text = "Score this call recording against the rubric. Respond with JSON only."
    if wira_tickets:
        ticket_lines = "\n".join(f"- {t.get('task_id', '')} ({t.get('url', '')})" for t in wira_tickets)
        user_text += f"\n\nWIRA tickets logged within 30 minutes of this call:\n{ticket_lines}\nUse these to assess criterion 2e (ticket documentation)."
    else:
        user_text += "\n\nNo WIRA ticket data available for this call — set 2e score to null."
    if transcript_zh:
        user_text += f"\n\nReference transcript (may have errors — audio is ground truth):\n{transcript_zh[:6000]}"

    response = client.chat.completions.create(
        model="gpt-audio-2025-08-28",
        max_tokens=1024,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {"data": audio_b64, "format": "mp3"},
                    },
                    {
                        "type": "text",
                        "text": user_text,
                    },
                ],
            },
        ],
    )
    return json.loads(response.choices[0].message.content.strip())


def score_transcript(transcript: str) -> dict:
    """Return AI scores for each criterion. Each value: {score, justification}."""
    if not transcript or not transcript.strip():
        return {
            c["id"]: {"score": 2, "justification": "No transcript available for this call."}
            for c in _rubric._load()
        }

    system = SYSTEM_PROMPT.format(rubric=_build_rubric_text(), call_type_desc="Unknown — infer from the transcript content.")
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=1024,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Score this call transcript:\n\n{transcript[:8000]}"},
        ],
    )

    text = response.choices[0].message.content.strip()
    return json.loads(text)
