import os
import gspread
from datetime import datetime
from rubric import CRITERIA, compute_total_score

SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID", "1H0lu-cOxRecJ3z_oxL9QDoiSQFGK4ILeAWVjccRWDtw")
RESULTS_TAB = "QA Reviews"

HEADER = [
    "Timestamp",
    "Reviewer",
    "Agent Name",
    "Agent ID",
    "Call ID",
    "Call Date",
    "Duration (s)",
    "Call URL",
    *[f"{c['id']} — {c['name']}" for c in CRITERIA],
    "Total QA Score (%)",
    "AI Suggested Score (%)",
    "Notes",
]


def _get_sheet():
    creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    gc = gspread.oauth(
        credentials_filename=creds_path,
        authorized_user_filename="token.json",
    )
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)

    try:
        ws = spreadsheet.worksheet(RESULTS_TAB)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=RESULTS_TAB, rows=1000, cols=len(HEADER))
        ws.append_row(HEADER)

    return ws


def submit_review(
    reviewer: str,
    agent_name: str,
    agent_id: str,
    call: dict,
    scores: dict[str, int],
    ai_scores: dict,
    notes: str,
) -> None:
    ws = _get_sheet()

    call_date = (call.get("call_started") or "")[:10]
    total = compute_total_score(scores)
    ai_total = compute_total_score({k: v["score"] for k, v in ai_scores.items()})

    row = [
        datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        reviewer,
        agent_name,
        agent_id,
        call.get("call_id", ""),
        call_date,
        call.get("duration_seconds", ""),
        call.get("greendot_url", ""),
        *[scores.get(c["id"], "") for c in CRITERIA],
        total,
        ai_total,
        notes,
    ]

    ws.append_row(row)
