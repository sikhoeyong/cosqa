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
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:5176", "http://localhost:3000"],
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


@app.get("/calls/{call_id}/related-calls")
def get_related_calls(call_id: str):
    try:
        return snowflake_client.get_related_calls(call_id)
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
            SELECT call_transcript, chinese_call_transcript
            FROM PROD_WONDERS_LAKE.ASR.ASR_TRANSCRIPT
            WHERE call_id = '{call_id}'
            LIMIT 1
        """)
        if rows:
            return {"transcript_en": rows[0][0], "transcript_zh": rows[0][1]}
        return {"transcript_en": None, "transcript_zh": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── AI Scoring ────────────────────────────────────────────────────────────────

@app.post("/calls/{call_id}/ai-score")
def ai_score(call_id: str):
    try:
        rows = snowflake_client.query(f"""
            SELECT t.chinese_call_transcript, c.call_skills_required
            FROM PROD_WONDERS_LAKE.ASR.ASR_TRANSCRIPT t
            JOIN PROD_WONDERS_LAKE.CALL_CENTER.CALLS c ON c.conversation_id = t.call_id
            WHERE t.call_id = '{call_id}'
            LIMIT 1
        """)
        transcript_zh = rows[0][0] if rows and rows[0][0] else ""
        skills = (rows[0][1] or "") if rows else ""
        is_chinese_assistant = "chinese_assistant" in skills
        wira_tickets = snowflake_client.get_wira_tickets(call_id)
        result = scorer.score_audio(
            call_id,
            transcript_zh=transcript_zh,
            is_chinese_assistant=is_chinese_assistant,
            wira_tickets=wira_tickets or None,
        )
        return {**result, "_source": "audio"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Reviews ───────────────────────────────────────────────────────────────────

@app.get("/reviews")
def list_reviews(agent_id: str, start_date: str, end_date: str):
    try:
        return snowflake_client.get_reviews(agent_id, start_date, end_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/reviews/{call_id}")
def delete_review(call_id: str, agent_id: str):
    try:
        snowflake_client.delete_review(call_id, agent_id)
        return {"status": "ok"}
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
    total = compute_total_score(payload.scores)
    try:
        snowflake_client.save_review(
            reviewer=payload.reviewer,
            agent_name=payload.agent_name,
            agent_id=payload.agent_id,
            call=payload.call,
            scores=payload.scores,
            total_score=total,
            notes=payload.notes,
            ai_scores=payload.ai_scores,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Snowflake write failed: {e}")

    # Sheets is best-effort; don't fail the request if it errors
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
    except Exception:
        pass

    return {"status": "ok", "total_score": total}


# ── Rubric ────────────────────────────────────────────────────────────────────

@app.get("/rubric")
def get_rubric():
    from rubric import _load
    return _load()


@app.put("/rubric")
def put_rubric(criteria: list[dict]):
    try:
        from rubric import save
        save(criteria)
        return {"status": "ok", "count": len(criteria)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
