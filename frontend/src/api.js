const BASE = "http://localhost:8000";

export async function fetchAgents(startDate, endDate) {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
  const r = await fetch(`${BASE}/agents?${params}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function fetchCalls(agentId, startDate, endDate) {
  const params = new URLSearchParams({ agent_id: agentId, start_date: startDate, end_date: endDate });
  const r = await fetch(`${BASE}/calls?${params}`);
  if (!r.ok) throw new Error(await r.text());
  // returns { calls: [...], last_call_date: "YYYY-MM-DD" | null }
  return r.json();
}

export async function fetchWiraTickets(callId) {
  const r = await fetch(`${BASE}/calls/${callId}/wira-tickets`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function fetchTranscript(callId) {
  const r = await fetch(`${BASE}/calls/${callId}/transcript`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function fetchAiScore(callId) {
  const r = await fetch(`${BASE}/calls/${callId}/ai-score`, { method: "POST" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function submitReview(payload) {
  const r = await fetch(`${BASE}/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function fetchRubric() {
  const r = await fetch(`${BASE}/rubric`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
