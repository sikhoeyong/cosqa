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
            t.task_type,
            t.sub_intent,
            TO_CHAR(t.task_created_at_est, 'YYYY-MM-DD HH24:MI') AS created_at
        FROM PROD_WONDERS_LAKE.CALL_CENTER.CALLS c
        JOIN PROD_WONDERS_LAKE.CORE.RESTAURANTS r ON r.id = c.restaurant_id
        JOIN PROD_WONDERS_LAKE.INTERMEDIATE.INT_CORE__WIRA_TASKS t
            ON t.restaurant_unique_code = r.unique_code
            AND t.task_created_at_est BETWEEN c.call_started_at_est
                                          AND DATEADD(minute, 30, c.call_started_at_est)
        WHERE c.conversation_id = '{call_id}'
        ORDER BY t.task_created_at_est
    """)
    return [
        {
            "task_id": r[0],
            "url": r[1],
            "title": r[2],
            "status": r[3],
            "task_category": r[4],
            "task_intent": r[5],
            "created_at": r[6],
        }
        for r in rows
    ]


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
                    ELSE NULL
                END
            ) AS greendot_url,
            c.is_order_converted_call,
            c.call_skills_required,
            t.chinese_call_transcript,
            t.cortex_sentiment_score
        FROM PROD_WONDERS_LAKE.CALL_CENTER.CALLS c
        LEFT JOIN PROD_WONDERS_LAKE.CORE.RESTAURANTS r ON r.id = c.restaurant_id
        LEFT JOIN PROD_WONDERS_LAKE.ASR.ASR_TRANSCRIPT t ON c.conversation_id = t.call_id
        LEFT JOIN (
            SELECT call_id,
                   REGEXP_REPLACE(ANY_VALUE(customer_phone_number), '^\\+1', '') AS phone
            FROM PROD_WONDERS_LAKE.GREENDOT_ANALYTICS.GREENDOT_ANALYTICS_EVENTS
            WHERE customer_phone_number IS NOT NULL
              AND customer_phone_number REGEXP '^\\+1[0-9]{{10}}$'
            GROUP BY call_id
        ) ae ON ae.call_id = c.conversation_id
        LEFT JOIN LATERAL (
            SELECT ANY_VALUE(c2.call_phone_detail) AS phone
            FROM PROD_WONDERS_LAKE.CALL_CENTER.CALLS c2
            WHERE c2.restaurant_id = c.restaurant_id
              AND c2.call_communicator_type IN ('client', 'customer')
              AND c2.call_phone_detail REGEXP '^[0-9]{{10}}$'
              AND ABS(DATEDIFF('second', c2.call_started_at_est, c.call_started_at_est)) <= 300
              AND c2.conversation_id != c.conversation_id
        ) rl ON TRUE
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
            "transcript": r[6],
            "sentiment_score": r[7],
        }
        for r in rows
    ]
