CHAT_CRITERIA = [
    {
        "id": "c1",
        "section": "Chat Handling",
        "name": "Opening & greeting",
        "weight": 0.20,
        "score_1": "No greeting or very abrupt opening",
        "score_2": "Generic greeting without personalization",
        "score_3": "Professional greeting with context acknowledgement",
        "scoring_notes": "",
    },
    {
        "id": "c2",
        "section": "Chat Handling",
        "name": "Tone & professionalism",
        "weight": 0.20,
        "score_1": "Unprofessional, rude, or dismissive tone",
        "score_2": "Neutral tone, no glaring issues but not warm",
        "score_3": "Consistently professional, empathetic, and polished",
        "scoring_notes": "",
    },
    {
        "id": "c3",
        "section": "Resolution",
        "name": "Issue understanding",
        "weight": 0.20,
        "score_1": "Misunderstood or ignored the customer's issue",
        "score_2": "Understood the issue but needed multiple clarifications",
        "score_3": "Quickly and accurately identified the root issue",
        "scoring_notes": "",
    },
    {
        "id": "c4",
        "section": "Resolution",
        "name": "Solution accuracy",
        "weight": 0.20,
        "score_1": "Incorrect or no solution provided",
        "score_2": "Partially correct solution or workaround given",
        "score_3": "Accurate, complete solution provided efficiently",
        "scoring_notes": "",
    },
    {
        "id": "c5",
        "section": "Resolution",
        "name": "Closing",
        "weight": 0.20,
        "score_1": "No closing or abrupt end to conversation",
        "score_2": "Basic closing without confirming resolution",
        "score_3": "Confirmed resolution, warm closing, offered further help",
        "scoring_notes": "",
    },
]


def compute_chat_total_score(scores: dict) -> float:
    """Compute weighted score from {criterion_id: 1|2|3} dict. Returns 0–100."""
    total = 0.0
    for c in CHAT_CRITERIA:
        s = scores.get(c["id"])
        if s is not None:
            total += (int(s) / 3) * c["weight"] * 100
    return round(total, 1)
