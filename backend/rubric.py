CRITERIA = [
    {
        "id": "1a",
        "section": "Call Handling",
        "name": "Opening spiel",
        "weight": 0.05,
        "scoring_notes": "3 = full correct spiel, clear self-introduction; 2 = greeted but missed one element; 1 = wrong or skipped entirely.",
        "score_1": "Did not greet OR used entirely wrong spiel",
        "score_2": "Greeted but missed one element of spiel",
        "score_3": "Full correct spiel, clear self-introduction",
    },
    {
        "id": "1b",
        "section": "Call Handling",
        "name": "Tone, no jargon & dead air",
        "weight": 0.05,
        "scoring_notes": "3 = warm, composed, plain language, no unmanaged silences; 2 = mostly professional, minor lapses or brief dead air; 1 = abrupt, heavy jargon, or long unmanaged silences.",
        "score_1": "Abrupt, dismissive, heavy jargon, or long unmanaged silences",
        "score_2": "Mostly professional; minor jargon or brief dead air",
        "score_3": "Warm, composed, plain language; silence managed with verbal updates",
    },
    {
        "id": "1c",
        "section": "Call Handling",
        "name": "Empathy & composure",
        "weight": 0.05,
        "scoring_notes": "3 = consistent empathy, de-escalated naturally; 2 = attempted but inconsistent; 1 = defensive or dismissive. Mark 3 if no difficult moment arose.",
        "score_1": "Defensive or dismissive on a difficult call",
        "score_2": "Attempted empathy but inconsistent",
        "score_3": "Consistent empathy; de-escalated naturally. Mark 3 if no difficult moment arose.",
    },
    {
        "id": "1d",
        "section": "Call Handling",
        "name": "Mandarin proficiency",
        "weight": 0.05,
        "scoring_notes": "3 = full Mandarin throughout, natural and fluent; 2 = mostly Mandarin, occasional English mix; 1 = primarily English or significant language mismatch. N/A if client is English-speaking — mark 3.",
        "score_1": "Primarily English or significant language mismatch with Mandarin-speaking client",
        "score_2": "Mostly Mandarin; occasional English mix or unnecessary code-switching",
        "score_3": "Full Mandarin throughout; natural, fluent. Mark 3 if client is English-speaking.",
    },
    {
        "id": "2a",
        "section": "Problem Solving",
        "name": "Listening & concise questioning",
        "weight": 0.10,
        "scoring_notes": "3 = all key info gathered efficiently, no redundant probing; 2 = got main facts, some unnecessary questions or missed follow-ups; 1 = proceeded without adequate info or excessive re-probing.",
        "score_1": "Proceeded without basic info OR excessive re-probing",
        "score_2": "Got key facts; some unnecessary questions or missed follow-ups",
        "score_3": "All relevant info gathered efficiently; no redundant questions",
    },
    {
        "id": "2b",
        "section": "Problem Solving",
        "name": "Root cause triage",
        "weight": 0.10,
        "scoring_notes": "3 = correct root cause, right solution path; 2 = identified issue but misread root cause; 1 = wrong diagnosis. Penalise wrong triage even if the call resolved accidentally.",
        "score_1": "Wrong diagnosis; resolved the wrong issue entirely",
        "score_2": "Identified the issue but misread the root cause",
        "score_3": "Accurate root cause; correct solution path chosen",
    },
    {
        "id": "2c",
        "section": "Problem Solving",
        "name": "Knowledge application",
        "weight": 0.10,
        "scoring_notes": "3 = confident, accurate; 2 = general knowledge, gaps on edge cases; 1 = clear misunderstanding. Note whether error was product or process.",
        "score_1": "Clear product or process misunderstanding",
        "score_2": "General knowledge; gaps on edge cases or procedures",
        "score_3": "Confident, accurate product and process application",
    },
    {
        "id": "2d",
        "section": "Problem Solving",
        "name": "Correct resolution / escalation",
        "weight": 0.15,
        "scoring_notes": "3 = resolved correctly OR escalated with clear reason + timeline; 2 = correct decision, vague timeline or incomplete execution; 1 = wrong resolution given or unnecessary escalation.",
        "score_1": "Wrong resolution given OR escalated unnecessarily",
        "score_2": "Correct decision but vague timeline or incomplete execution",
        "score_3": "Resolved correctly OR escalated with clear reason and timeline",
    },
    {
        "id": "2e",
        "section": "Problem Solving",
        "name": "Ticket documentation",
        "weight": 0.05,
        "scoring_notes": "3 = correct intent/sub-intent, clear notes; 2 = ticket created, minor intent error; 1 = wrong type or no ticket.",
        "score_1": "No ticket created OR completely wrong intent type",
        "score_2": "Ticket created; minor intent or sub-intent error",
        "score_3": "Correct intent, sub-intent, and clear case notes",
    },
    {
        "id": "3a",
        "section": "Ownership & Coaching",
        "name": "Ownership",
        "weight": 0.10,
        "scoring_notes": "3 = resolved independently OR escalated only where truly necessary; 2 = attempted resolution but escalation borderline necessary; 1 = passed off without attempting resolution.",
        "score_1": "Passed to another team without attempting resolution",
        "score_2": "Attempted resolution; escalated but borderline necessary",
        "score_3": "Resolved independently OR escalated only where truly required",
    },
    {
        "id": "3b",
        "section": "Ownership & Coaching",
        "name": "CMA self-serve coaching [Q3 PRIORITY]",
        "weight": 0.15,
        "scoring_notes": "3 = proactively coached with specific CMA steps, confirmed client can do it next time; 2 = mentioned self-serve but did not walk through steps; 1 = missed opportunity entirely. Mark 3 if self-serve was not applicable.",
        "score_1": "Missed opportunity entirely — no CMA mention on an applicable call",
        "score_2": "Mentioned CMA self-serve but did not walk client through steps",
        "score_3": "Proactively coached client through specific CMA steps; confirmed they can self-serve next time",
    },
    {
        "id": "3c",
        "section": "Ownership & Coaching",
        "name": "Clear close & confirmed understanding",
        "weight": 0.05,
        "scoring_notes": "3 = clear resolution summary, confirmed understanding, clean close; 2 = adequate close but no confirmation of understanding; 1 = abrupt end or client unclear on outcome.",
        "score_1": "Abrupt end; client unclear on resolution or next steps",
        "score_2": "Adequate close but no confirmation of client understanding",
        "score_3": "Clear resolution summary; confirmed client understanding before closing",
    },
]

CRITERIA_BY_ID = {c["id"]: c for c in CRITERIA}


def compute_total_score(scores: dict[str, int]) -> float:
    """Compute total QA score as a percentage (0–100). Formula: (score-1)/2 * weight."""
    total = 0.0
    for criterion in CRITERIA:
        cid = criterion["id"]
        score = scores.get(cid, 1)
        total += ((score - 1) / 2) * criterion["weight"]
    return round(total * 100, 1)
