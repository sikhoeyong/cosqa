import os
import time
import requests

SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT", "XDDUPKQ-WP18692")
SNOWFLAKE_TOKEN = os.getenv("SNOWFLAKE_TOKEN", "")
BASE_URL = f"https://{SNOWFLAKE_ACCOUNT}.snowflakecomputing.com/api/v2/statements"


def _headers():
    return {
        "Authorization": f"Bearer {SNOWFLAKE_TOKEN}",
        "Content-Type": "application/json",
    }


def _poll(statement_handle: str) -> dict:
    url = f"{BASE_URL}/{statement_handle}"
    for _ in range(60):
        resp = requests.get(url, headers=_headers(), timeout=30).json()
        if resp.get("code") != "333334":
            return resp
        time.sleep(2)
    raise TimeoutError(f"Snowflake query timed out: {statement_handle}")


def _fetch_partition(statement_handle: str, partition: int) -> list[list]:
    url = f"{BASE_URL}/{statement_handle}?partition={partition}"
    resp = requests.get(url, headers=_headers(), timeout=30).json()
    return resp.get("data", [])


def query(sql: str) -> list[list]:
    """Execute SQL and return all rows as list of lists, fetching all partitions."""
    payload = {"statement": sql, "timeout": 60}
    resp = requests.post(BASE_URL, headers=_headers(), json=payload, timeout=90).json()

    if resp.get("code") == "333334":
        resp = _poll(resp["statementHandle"])

    if resp.get("code") not in ("090001", None) and "data" not in resp:
        raise RuntimeError(f"Snowflake error {resp.get('code')}: {resp.get('message')}")

    rows = resp.get("data", [])

    # Fetch additional partitions if the result set is paginated
    partitions = resp.get("resultSetMetaData", {}).get("partitionInfo", [])
    handle = resp.get("statementHandle")
    if handle and len(partitions) > 1:
        for i in range(1, len(partitions)):
            rows.extend(_fetch_partition(handle, i))

    return rows


def get_wira_tickets(call_id: str) -> list[dict]:
    rows = query(f"""
        SELECT
            t.wira_task_id,
            t.wira_ticket_url,
            t.task_title,
            t.task_status,
            TO_CHAR(t.task_created_at_est, 'YYYY-MM-DD HH24:MI') AS created_at
        FROM PROD_WONDERS_LAKE.CALL_CENTER.CALLS c
        JOIN PROD_WONDERS_LAKE.CORE.RESTAURANTS r ON r.id = c.restaurant_id
        JOIN PROD_WONDERS_LAKE.INTERMEDIATE.INT_CALL_CENTER__INTERNAL_USERS_UNIFIED u ON u.id = c.operator_id
        JOIN PROD_WONDERS_LAKE.INTERMEDIATE.INT_CORE__WIRA_TASKS t
            ON t.restaurant_unique_code = r.unique_code
            AND t.task_created_at_est BETWEEN c.call_started_at_est
                                          AND DATEADD(minute, 30, c.call_started_at_est)
            AND (
                t.task_created_by = LOWER(REPLACE(u.full_name, ' ', '')) || 'wonderscocom'
                OR t.task_created_by IS NULL
                OR t.task_created_by = ''
            )
        WHERE c.conversation_id = '{call_id}'
        ORDER BY t.task_created_at_est
    """)
    return [
        {
            "task_id": r[0],
            "url": r[1],
            "title": r[2],
            "status": r[3],
            "created_at": r[4],
        }
        for r in rows
    ]


def get_related_calls(call_id: str) -> list[dict]:
    rows = query(f"""
        -- Related calls by same agent to same customer (within 60 min)
        SELECT
            c2.conversation_id,
            c2.call_communicator_type AS type,
            TO_CHAR(c2.call_started_at_est, 'YYYY-MM-DD HH24:MI:SS') AS call_started,
            c2.call_duration_in_seconds AS duration_seconds,
            COALESCE(
                c2.greendot_call_url,
                CASE
                    WHEN r.unique_code IS NOT NULL AND c2.call_phone_detail REGEXP '^[0-9]{{10}}$'
                    THEN 'https://greendot.prod.letsdowonders.io/greendot/restaurant/'
                         || r.unique_code || '?caller_id='
                         || SUBSTRING(c2.call_phone_detail, 1, 3) || '-'
                         || SUBSTRING(c2.call_phone_detail, 4, 3) || '-'
                         || SUBSTRING(c2.call_phone_detail, 7, 4)
                         || '&callId=' || c2.conversation_id
                    WHEN r.unique_code IS NOT NULL
                    THEN 'https://greendot.prod.letsdowonders.io/greendot/restaurant/'
                         || r.unique_code || '?callId=' || c2.conversation_id
                         || '&panel=call_recordings'
                    ELSE 'https://greendot.prod.letsdowonders.io/greendot/callrecordings?callIds='
                         || c2.conversation_id
                END
            ) AS greendot_url
        FROM PROD_WONDERS_LAKE.CALL_CENTER.CALLS c1
        JOIN PROD_WONDERS_LAKE.CALL_CENTER.CALLS c2
            ON c2.restaurant_id = c1.restaurant_id
            AND c2.conversation_id != '{call_id}'
            AND c2.operator_id = c1.operator_id
            AND c2.call_phone_detail = c1.call_phone_detail
            AND c1.call_phone_detail REGEXP '^[0-9]{{10}}$'
            AND ABS(DATEDIFF('minute', c2.call_started_at_est, c1.call_started_at_est)) <= 60
        LEFT JOIN PROD_WONDERS_LAKE.CORE.RESTAURANTS r ON r.id = c1.restaurant_id
        WHERE c1.conversation_id = '{call_id}'

        UNION ALL

        -- 3-way outbound calls spawned from this call (via ASTERISK_CALLS parent link)
        SELECT
            a.call_id AS conversation_id,
            'outbound' AS type,
            TO_CHAR(a.call_started_at_est, 'YYYY-MM-DD HH24:MI:SS') AS call_started,
            NULL AS duration_seconds,
            CASE
                WHEN r.unique_code IS NOT NULL AND a.phone_number REGEXP '^\\+1[0-9]{{10}}$'
                THEN 'https://greendot.prod.letsdowonders.io/greendot/restaurant/'
                     || r.unique_code || '?caller_id='
                     || SUBSTRING(REGEXP_REPLACE(a.phone_number, '^\\+1', ''), 1, 3) || '-'
                     || SUBSTRING(REGEXP_REPLACE(a.phone_number, '^\\+1', ''), 4, 3) || '-'
                     || SUBSTRING(REGEXP_REPLACE(a.phone_number, '^\\+1', ''), 7, 4)
                     || '&callId=' || a.call_id
                WHEN r.unique_code IS NOT NULL
                THEN 'https://greendot.prod.letsdowonders.io/greendot/restaurant/'
                     || r.unique_code || '?callId=' || a.call_id
                     || '&panel=call_recordings'
                ELSE 'https://greendot.prod.letsdowonders.io/greendot/callrecordings?callIds='
                     || a.call_id
            END AS greendot_url
        FROM PROD_WONDERS_LAKE.CALL_CENTER.CALLS c1
        JOIN PROD_WONDERS_LAKE.CALL_CENTER.ASTERISK_CALLS a_orig ON a_orig.call_id = '{call_id}'
        JOIN PROD_WONDERS_LAKE.CALL_CENTER.ASTERISK_CALLS a
            ON a.ref_previous_call_asterisk_call_wid = a_orig.wid
            AND a.call_id != '{call_id}'
        LEFT JOIN PROD_WONDERS_LAKE.CORE.RESTAURANTS r ON r.id = c1.restaurant_id
        WHERE c1.conversation_id = '{call_id}'

        ORDER BY call_started
    """)
    return [
        {
            "call_id": r[0],
            "type": r[1],
            "call_started": r[2],
            "duration_seconds": r[3],
            "greendot_url": r[4],
        }
        for r in rows
    ]


QA_TABLE = os.getenv("SNOWFLAKE_QA_TABLE", "DEV_ENGINEERING.COS_QA.QA_REVIEWS")


def _esc(s: str) -> str:
    """Escape single quotes for inline SQL strings."""
    return str(s or "").replace("'", "''")


def ensure_qa_table() -> None:
    parts = QA_TABLE.split(".")
    schema = ".".join(parts[:2])
    query(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    query(f"""
        CREATE TABLE IF NOT EXISTS {QA_TABLE} (
            reviewed_at      TIMESTAMP_NTZ,
            reviewer         VARCHAR,
            agent_name       VARCHAR,
            agent_id         VARCHAR,
            call_id          VARCHAR,
            call_date        DATE,
            duration_seconds INT,
            greendot_url     VARCHAR,
            scores           VARIANT,
            total_score      FLOAT,
            notes            TEXT
        )
    """)


def save_review(
    reviewer: str,
    agent_name: str,
    agent_id: str,
    call: dict,
    scores: dict,
    total_score: float,
    notes: str,
    ai_scores: dict = None,
) -> None:
    import json
    ensure_qa_table()
    call_date = (_esc(call.get("call_started") or ""))[:10]
    # Merge human scores with AI justifications: {id: {score, justification}}
    merged = {
        cid: {
            "score": score,
            "justification": (ai_scores or {}).get(cid, {}).get("justification", ""),
        }
        for cid, score in scores.items()
    }
    scores_json = _esc(json.dumps(merged))
    duration = int(call.get("duration_seconds") or 0)
    query(f"""
        INSERT INTO {QA_TABLE} (
            reviewed_at, reviewer, agent_name, agent_id,
            call_id, call_date, duration_seconds, greendot_url,
            scores, total_score, notes
        )
        SELECT
            CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP())::TIMESTAMP_NTZ,
            '{_esc(reviewer)}',
            '{_esc(agent_name)}',
            '{_esc(agent_id)}',
            '{_esc(call.get("call_id", ""))}',
            '{call_date}'::DATE,
            {duration},
            '{_esc(call.get("greendot_url", ""))}',
            PARSE_JSON('{scores_json}'),
            {total_score},
            '{_esc(notes)}'
    """)


def get_reviews(operator_id: str, start_date: str, end_date: str) -> list[dict]:
    import json
    try:
        rows = query(f"""
            SELECT call_id,
                   TO_CHAR(reviewed_at, 'YYYY-MM-DD HH24:MI') AS reviewed_at,
                   reviewer,
                   scores::VARCHAR AS scores,
                   total_score,
                   notes
            FROM {QA_TABLE}
            WHERE agent_id = '{_esc(operator_id)}'
              AND call_date BETWEEN '{_esc(start_date)}' AND '{_esc(end_date)}'
            ORDER BY reviewed_at DESC
        """)
    except Exception:
        return []
    seen: set = set()
    result = []
    for r in rows:
        call_id = r[0]
        if call_id in seen:
            continue
        seen.add(call_id)
        try:
            scores = json.loads(r[3]) if r[3] else {}
        except Exception:
            scores = {}
        result.append({
            "call_id": call_id,
            "reviewed_at": r[1],
            "reviewer": r[2],
            "scores": scores,
            "total_score": float(r[4]) if r[4] else None,
            "notes": r[5] or "",
        })
    return result


def delete_review(call_id: str, agent_id: str) -> None:
    query(f"""
        DELETE FROM {QA_TABLE}
        WHERE call_id = '{_esc(call_id)}'
          AND agent_id = '{_esc(agent_id)}'
    """)


def get_cos_agents(start_date: str, end_date: str) -> list[dict]:
    rows = query(f"""
        SELECT
            u.id,
            u.full_name,
            u.position_name,
            u.team_description,
            COUNT(c.conversation_id) AS call_count,
            TO_CHAR(MAX(c.call_started_at_est), 'YYYY-MM-DD') AS last_call_date,
            u.user_login_name
        FROM PROD_WONDERS_LAKE.INTERMEDIATE.INT_CALL_CENTER__INTERNAL_USERS_UNIFIED u
        JOIN PROD_WONDERS_LAKE.CALL_CENTER.CALLS c ON c.operator_id = u.id
        WHERE (LOWER(u.position_name) LIKE '%cos%' OR LOWER(u.team_description) LIKE '%cos%')
          AND u.is_active = TRUE
          AND c.call_communicator_type = 'agent'
          AND DATE(c.call_started_at_est) BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY u.id, u.full_name, u.position_name, u.team_description, u.user_login_name
        ORDER BY u.full_name
    """)
    def _tier(position_name: str) -> str:
        p = (position_name or "").upper()
        if "TIER III" in p or "TIER 3" in p:
            return "III"
        if "TIER II" in p or "TIER 2" in p:
            return "II"
        if "TIER I" in p or "TIER 1" in p:
            return "I"
        return "—"

    return [
        {
            "id": r[0],
            "full_name": r[1],
            "position_name": r[2],
            "team_description": r[3],
            "call_count": r[4],
            "last_call_date": r[5],
            "gd_username": r[6],
            "tier": _tier(r[2]),
        }
        for r in rows
    ]


def get_calls(operator_id: str, start_date: str, end_date: str) -> list[dict]:
    rows = query(f"""
        SELECT
            c.conversation_id,
            TO_CHAR(c.call_started_at_est, 'YYYY-MM-DD HH24:MI:SS') AS call_started,
            c.call_duration_in_seconds,
            COALESCE(
                c.greendot_call_url,
                CASE
                    WHEN r.unique_code IS NOT NULL
                         AND c.call_phone_detail REGEXP '^[0-9]{{10}}$'
                    THEN 'https://greendot.prod.letsdowonders.io/greendot/restaurant/'
                         || r.unique_code
                         || '?caller_id='
                         || SUBSTRING(c.call_phone_detail, 1, 3) || '-'
                         || SUBSTRING(c.call_phone_detail, 4, 3) || '-'
                         || SUBSTRING(c.call_phone_detail, 7, 4)
                         || '&callId=' || c.conversation_id
                    WHEN r.unique_code IS NOT NULL AND ae.phone IS NOT NULL
                    THEN 'https://greendot.prod.letsdowonders.io/greendot/restaurant/'
                         || r.unique_code
                         || '?caller_id='
                         || SUBSTRING(ae.phone, 1, 3) || '-'
                         || SUBSTRING(ae.phone, 4, 3) || '-'
                         || SUBSTRING(ae.phone, 7, 4)
                         || '&callId=' || c.conversation_id
                    WHEN r.unique_code IS NOT NULL AND rl.phone IS NOT NULL
                    THEN 'https://greendot.prod.letsdowonders.io/greendot/restaurant/'
                         || r.unique_code
                         || '?caller_id='
                         || SUBSTRING(rl.phone, 1, 3) || '-'
                         || SUBSTRING(rl.phone, 4, 3) || '-'
                         || SUBSTRING(rl.phone, 7, 4)
                         || '&callId=' || c.conversation_id
                    WHEN r.unique_code IS NOT NULL
                    THEN 'https://greendot.prod.letsdowonders.io/greendot/restaurant/'
                         || r.unique_code
                         || '?callId=' || c.conversation_id
                         || '&panel=call_recordings'
                    ELSE 'https://greendot.prod.letsdowonders.io/greendot/callrecordings?callIds='
                         || c.conversation_id
                END
            ) AS greendot_url,
            c.is_order_converted_call,
            c.call_skills_required,
            COALESCE(c.call_time_in_seconds, 0) AS att_seconds,
            COALESCE(c.call_wait_in_seconds, 0) AS awt_seconds,
            COALESCE(c.wrap_up_time_in_seconds, 0) AS acw_seconds,
            t.chinese_call_transcript,
            t.cortex_sentiment_score,
            wira_all.tickets_agg AS wira_tickets,
            rel.related_agg AS related_calls
        FROM PROD_WONDERS_LAKE.CALL_CENTER.CALLS c
        LEFT JOIN PROD_WONDERS_LAKE.CORE.RESTAURANTS r ON r.id = c.restaurant_id
        LEFT JOIN PROD_WONDERS_LAKE.ASR.ASR_TRANSCRIPT t ON c.conversation_id = t.call_id
        LEFT JOIN (
            SELECT
                c4.conversation_id,
                LISTAGG(t3.wira_task_id || '::' || t3.wira_ticket_url, '|||')
                    WITHIN GROUP (ORDER BY t3.task_created_at_est) AS tickets_agg
            FROM PROD_WONDERS_LAKE.CALL_CENTER.CALLS c4
            JOIN PROD_WONDERS_LAKE.CORE.RESTAURANTS r3 ON r3.id = c4.restaurant_id
            JOIN PROD_WONDERS_LAKE.INTERMEDIATE.INT_CALL_CENTER__INTERNAL_USERS_UNIFIED u3 ON u3.id = c4.operator_id
            JOIN PROD_WONDERS_LAKE.INTERMEDIATE.INT_CORE__WIRA_TASKS t3
                ON t3.restaurant_unique_code = r3.unique_code
                AND t3.task_created_at_est BETWEEN c4.call_started_at_est
                    AND DATEADD(minute, 30, c4.call_started_at_est)
                AND (
                    t3.task_created_by = LOWER(REPLACE(u3.full_name, ' ', '')) || 'wonderscocom'
                    OR t3.task_created_by IS NULL
                    OR t3.task_created_by = ''
                )
            WHERE c4.operator_id = '{operator_id}'
              AND DATE(c4.call_started_at_est) BETWEEN '{start_date}' AND '{end_date}'
            GROUP BY c4.conversation_id
        ) wira_all ON wira_all.conversation_id = c.conversation_id
        LEFT JOIN (
            SELECT c5.conversation_id,
                LISTAGG(c6.conversation_id || '::' || c6.call_communicator_type, '|||')
                    WITHIN GROUP (ORDER BY c6.call_started_at_est) AS related_agg
            FROM PROD_WONDERS_LAKE.CALL_CENTER.CALLS c5
            JOIN PROD_WONDERS_LAKE.CALL_CENTER.CALLS c6
                ON c6.operator_id = c5.operator_id
                AND c6.call_phone_detail = c5.call_phone_detail
                AND c5.call_phone_detail REGEXP '^[0-9]{{10}}$'
                AND c6.conversation_id != c5.conversation_id
                AND ABS(DATEDIFF('minute', c6.call_started_at_est, c5.call_started_at_est)) <= 60
            WHERE c5.operator_id = '{operator_id}'
              AND DATE(c5.call_started_at_est) BETWEEN '{start_date}' AND '{end_date}'
            GROUP BY c5.conversation_id
        ) rel ON rel.conversation_id = c.conversation_id
        LEFT JOIN (
            SELECT call_id,
                   REGEXP_REPLACE(ANY_VALUE(customer_phone_number), '^\\+1', '') AS phone
            FROM PROD_WONDERS_LAKE.GREENDOT_ANALYTICS.GREENDOT_ANALYTICS_EVENTS
            WHERE customer_phone_number IS NOT NULL
              AND customer_phone_number REGEXP '^\\+1[0-9]{{10}}$'
            GROUP BY call_id
        ) ae ON ae.call_id = c.conversation_id
        LEFT JOIN (
            SELECT
                c2.restaurant_id,
                ANY_VALUE(c2.call_phone_detail) AS phone
            FROM PROD_WONDERS_LAKE.CALL_CENTER.CALLS c2
            WHERE c2.operator_id = '{operator_id}'
              AND c2.call_communicator_type IN ('client', 'customer')
              AND c2.call_phone_detail REGEXP '^[0-9]{{10}}$'
            GROUP BY c2.restaurant_id
        ) rl ON rl.restaurant_id = c.restaurant_id
        WHERE c.operator_id = '{operator_id}'
          AND c.call_communicator_type = 'agent'
          AND DATE(c.call_started_at_est) BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY c.call_started_at_est DESC
    """)
    return [
        {
            "call_id": r[0],
            "call_started": r[1],
            "duration_seconds": r[2],
            "greendot_url": r[3],
            "is_order_converted": r[4],
            "skills_required": r[5],
            "att_seconds": int(float(r[6])) if r[6] else 0,
            "awt_seconds": int(float(r[7])) if r[7] else 0,
            "acw_seconds": int(float(r[8])) if r[8] else 0,
            "transcript": r[9],
            "sentiment_score": r[10],
            "wira_tickets": [
                {"task_id": p.split("::")[0], "url": p.split("::")[1]}
                for p in r[11].split("|||")
                if "::" in p
            ] if r[11] else [],
            "related_calls": [
                {"call_id": p.split("::")[0], "type": p.split("::")[1]}
                for p in r[12].split("|||")
                if "::" in p
            ] if r[12] else [],
        }
        for r in rows
    ]


def get_conversation_agents(start_date: str, end_date: str) -> list:
    """Agents who participated in conversations in the date range."""
    rows = query(f"""
        SELECT
            e.commenter_alias AS alias,
            COUNT(DISTINCT e.task_id) AS convo_count
        FROM (
            SELECT
                r.wid AS task_id,
                PARSE_JSON(ev.payload):payload_append_comment:commenter_alias::STRING AS commenter_alias
            FROM PROD_WONDERS_LAKE.WONDERSDB_SOURCES.WIRA_TASK_ROOT r
            JOIN PROD_WONDERS_LAKE.WONDERSDB_SOURCES.WIRA_TASK_EVENT ev
                ON ev.owner_wid = r.wid
            WHERE r.task_type = '{{"kind":"conversation"}}'
              AND PARSE_JSON(ev.payload):kind::STRING = 'append_comment'
              AND DATE(TO_TIMESTAMP(r.create_time)) BETWEEN '{_esc(start_date)}' AND '{_esc(end_date)}'
        ) e
        WHERE e.commenter_alias IS NOT NULL
          AND e.commenter_alias != ''
          AND e.commenter_alias NOT LIKE 'client-%'
          AND e.commenter_alias NOT LIKE 'internal-client-view-%'
          AND e.commenter_alias NOT LIKE 'cma-pin-user-%'
          AND e.commenter_alias LIKE '%@%'
        GROUP BY e.commenter_alias
        ORDER BY e.commenter_alias
    """)

    def _display_name(alias: str) -> str:
        if "@" in alias:
            prefix = alias.split("@")[0]
            return " ".join(part.capitalize() for part in prefix.replace(".", " ").split())
        return alias  # already a display name

    return [
        {
            "email": r[0],
            "display_name": _display_name(r[0]),
            "convo_count": int(r[1]) if r[1] else 0,
        }
        for r in rows
    ]


def get_conversations(agent_email: str, start_date: str, end_date: str) -> list:
    """List conversations handled by this agent in the date range."""
    rows = query(f"""
        SELECT
            r.wid AS convo_id,
            r.title AS title,
            TO_CHAR(TO_TIMESTAMP(r.create_time), 'YYYY-MM-DD HH24:MI:SS') AS created_at,
            r.status AS status,
            COUNT(ev.wid) AS message_count
        FROM PROD_WONDERS_LAKE.WONDERSDB_SOURCES.WIRA_TASK_ROOT r
        JOIN PROD_WONDERS_LAKE.WONDERSDB_SOURCES.WIRA_TASK_EVENT ev
            ON ev.owner_wid = r.wid
            AND PARSE_JSON(ev.payload):kind::STRING = 'append_comment'
        WHERE r.task_type = '{{"kind":"conversation"}}'
          AND DATE(TO_TIMESTAMP(r.create_time)) BETWEEN '{_esc(start_date)}' AND '{_esc(end_date)}'
          AND r.wid IN (
              SELECT DISTINCT owner_wid
              FROM PROD_WONDERS_LAKE.WONDERSDB_SOURCES.WIRA_TASK_EVENT
              WHERE PARSE_JSON(payload):kind::STRING = 'append_comment'
                AND PARSE_JSON(payload):payload_append_comment:commenter_alias::STRING = '{_esc(agent_email)}'
          )
        GROUP BY r.wid, r.title, r.create_time, r.status
        ORDER BY r.create_time DESC
    """)
    import json as _json

    def _status(raw):
        try:
            return _json.loads(raw or "").get("kind", raw)
        except Exception:
            return raw

    return [
        {
            "convo_id": r[0],
            "title": r[1],
            "created_at": r[2],
            "status": _status(r[3]),
            "message_count": int(r[4]) if r[4] else 0,
        }
        for r in rows
    ]


def get_conversation_thread(convo_id: str) -> list:
    """All messages in a conversation, ordered chronologically."""
    rows = query(f"""
        SELECT
            PARSE_JSON(payload):payload_append_comment:commenter_alias::STRING AS alias,
            PARSE_JSON(payload):payload_append_comment:contents::STRING AS content,
            TO_CHAR(TO_TIMESTAMP(create_time), 'YYYY-MM-DD HH24:MI:SS') AS ts
        FROM PROD_WONDERS_LAKE.WONDERSDB_SOURCES.WIRA_TASK_EVENT
        WHERE owner_wid = '{_esc(convo_id)}'
          AND PARSE_JSON(payload):kind::STRING = 'append_comment'
        ORDER BY create_time ASC
    """)
    return [
        {
            "alias": r[0],
            "is_agent": not (r[0] or "").startswith("client-"),
            "content": r[1],
            "timestamp": r[2],
        }
        for r in rows
    ]


def get_call_by_id(call_id: str):
    rows = query(f"""
        SELECT
            c.conversation_id,
            TO_CHAR(c.call_started_at_est, 'YYYY-MM-DD HH24:MI:SS') AS call_started,
            c.call_duration_in_seconds,
            COALESCE(
                c.greendot_call_url,
                CASE
                    WHEN r.unique_code IS NOT NULL
                    THEN 'https://greendot.prod.letsdowonders.io/greendot/restaurant/'
                         || r.unique_code
                         || '?callId=' || c.conversation_id
                         || '&panel=call_recordings'
                    ELSE 'https://greendot.prod.letsdowonders.io/greendot/callrecordings?callIds='
                         || c.conversation_id
                END
            ) AS greendot_url,
            c.is_order_converted_call,
            c.call_skills_required,
            COALESCE(c.call_time_in_seconds, 0),
            COALESCE(c.call_wait_in_seconds, 0),
            COALESCE(c.wrap_up_time_in_seconds, 0),
            t.chinese_call_transcript,
            t.cortex_sentiment_score,
            c.operator_id,
            u.full_name AS agent_name,
            u.position_name,
            u.team_description
        FROM PROD_WONDERS_LAKE.CALL_CENTER.CALLS c
        LEFT JOIN PROD_WONDERS_LAKE.CORE.RESTAURANTS r ON r.id = c.restaurant_id
        LEFT JOIN PROD_WONDERS_LAKE.ASR.ASR_TRANSCRIPT t ON c.conversation_id = t.call_id
        LEFT JOIN PROD_WONDERS_LAKE.INTERMEDIATE.INT_CALL_CENTER__INTERNAL_USERS_UNIFIED u ON u.id = c.operator_id
        WHERE c.conversation_id = '{_esc(call_id)}'
        LIMIT 1
    """)
    if not rows:
        return None
    r = rows[0]

    def _tier(position_name: str) -> str:
        p = (position_name or "").upper()
        if "TIER III" in p or "TIER 3" in p: return "III"
        if "TIER II" in p or "TIER 2" in p: return "II"
        if "TIER I" in p or "TIER 1" in p: return "I"
        return "—"

    return {
        "call": {
            "call_id": r[0],
            "call_started": r[1],
            "duration_seconds": r[2],
            "greendot_url": r[3],
            "is_order_converted": r[4],
            "skills_required": r[5],
            "att_seconds": int(float(r[6])) if r[6] else 0,
            "awt_seconds": int(float(r[7])) if r[7] else 0,
            "acw_seconds": int(float(r[8])) if r[8] else 0,
            "transcript": r[9],
            "sentiment_score": r[10],
            "wira_tickets": [],
            "related_calls": [],
        },
        "agent": {
            "id": r[11],
            "full_name": r[12] or "Unknown",
            "position_name": r[13],
            "team_description": r[14],
            "tier": _tier(r[13]),
        },
    }
