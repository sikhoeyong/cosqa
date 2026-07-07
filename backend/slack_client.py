import os
import requests

SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
FEEDBACK_CHANNEL = "C0BFCVCETV1"
FEEDBACK_THREAD_TS = "1783461243.224699"


def post_chat_feedback(reviewer: str, agent_email: str, convo_title: str, convo_id: str, feedback: str) -> None:
    text = (
        f"*Chat QA Feedback*\n"
        f"*Reviewer:* {reviewer}\n"
        f"*Agent:* {agent_email}\n"
        f"*Conversation:* {convo_title or convo_id}\n"
        f"*Feedback:*\n{feedback}"
    )
    resp = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
        json={
            "channel": FEEDBACK_CHANNEL,
            "thread_ts": FEEDBACK_THREAD_TS,
            "text": text,
        },
        timeout=10,
    )
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack error: {data.get('error')}")
