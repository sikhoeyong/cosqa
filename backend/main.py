import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import snowflake_client
import scorer
import sheets
from rubric import CRITERIA, compute_total_score

app = FastAPI(title="COS QA Tool")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Agents ────────────────────────────────────────────────────────────────────

@app.get("/agents")
def list_agents(start_date: str, end_date: str):
    try:
        return snowflake_client.get_cos_agents(start_date, end_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Calls ─────────────────────────────────────────────────────────────────────

@app.get("/calls")
def list_calls(agent_id: str, start_date: str, end_date: str):
    try:
        calls = snowflake_client.get_calls(agent_id, start_date, end_date)
        for c in calls:
            c["has_transcript"] = bool(c.get("transcript"))
            c.pop("transcript", None)

        last_call_date = None
        if not calls:
            rows = snowflake_client.query(f"""
                SELECT TO_CHAR(MAX(call_started_at_est), 'YYYY-MM-DD')
                FROM PROD_WONDERS_LAKE.CALL_CENTER.CALLS
                WHERE operator_id = '{agent_id}'
            """)
            last_call_date = rows[0][0] if rows and rows[0][0] else None

        return {"calls": calls, "last_call_date": last_call_date}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/calls/{call_id}/wira-tickets")
def get_wira_tickets(call_id: str):
    try:
        return snowflake_client.get_wira_tickets(call_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/calls/{call_id}/transcript")
def get_transcript(call_id: str):
    try:
        rows = snowflake_client.query(f"""
            SELECT chinese_call_transcript
            FROM PROD_WONDERS_LAKE.ASR.ASR_TRANSCRIPT
            WHERE call_id = '{call_id}'
            LIMIT 1
        """)
        return {"transcript": rows[0][0] if rows else None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── AI Scoring ────────────────────────────────────────────────────────────────

@app.post("/calls/{call_id}/ai-score")
def ai_score(call_id: str):
    try:
        rows = snowflake_client.query(f"""
            SELECT chinese_call_transcript
            FROM PROD_WONDERS_LAKE.ASR.ASR_TRANSCRIPT
            WHERE call_id = '{call_id}'
            LIMIT 1
        """)
        transcript = rows[0][0] if rows else ""
        result = scorer.score_transcript(transcript)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Submit Review ─────────────────────────────────────────────────────────────

class ReviewPayload(BaseModel):
    reviewer: str
    agent_name: str
    agent_id: str
    call: dict
    scores: dict[str, int]       # human-confirmed scores per criterion
    ai_scores: dict               # raw AI output {id: {score, justification}}
    notes: str = ""


@app.post("/submit")
def submit_review(payload: ReviewPayload):
    try:
        sheets.submit_review(
            reviewer=payload.reviewer,
            agent_name=payload.agent_name,
            agent_id=payload.agent_id,
            call=payload.call,
            scores=payload.scores,
            ai_scores=payload.ai_scores,
            notes=payload.notes,
        )
        total = compute_total_score(payload.scores)
        return {"status": "ok", "total_score": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Rubric ────────────────────────────────────────────────────────────────────

@app.get("/rubric")
def get_rubric():
    return CRITERIA
