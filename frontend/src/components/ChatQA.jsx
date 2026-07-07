import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { toast } from "sonner";
import { fetchConversationAgents, fetchConversations, fetchConversationThread, submitChatFeedback } from "../api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// ── helpers ──────────────────────────────────────────────────────────────────

function today() {
  return new Date().toISOString().slice(0, 10);
}

function weekAgo() {
  const d = new Date();
  d.setDate(d.getDate() - 7);
  return d.toISOString().slice(0, 10);
}

// ── ConversationSlideOver ─────────────────────────────────────────────────────

function ConversationSlideOver({ convo, onClose }) {
  const [thread, setThread] = useState(null);
  const [feedback, setFeedback] = useState("");
  const [reviewer, setReviewer] = useState(() => localStorage.getItem("chat_reviewer") || "");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    setLoading(true);
    fetchConversationThread(convo.convo_id)
      .then(msgs => {
        setThread(msgs);
        setLoading(false);
        setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
      })
      .catch(e => {
        toast.error("Failed to load thread: " + e.message);
        setLoading(false);
      });
  }, [convo.convo_id]);

  function handleReviewerChange(val) {
    setReviewer(val);
    localStorage.setItem("chat_reviewer", val);
  }

  async function handleSave() {
    if (!reviewer.trim()) {
      toast.warning("Please enter your name as reviewer");
      return;
    }
    if (!feedback.trim()) {
      toast.warning("Please enter some feedback before saving");
      return;
    }
    setSaving(true);
    try {
      await submitChatFeedback({
        reviewer: reviewer.trim(),
        agent_email: convo.agent_email || "",
        convo_title: convo.title || "",
        convo_id: convo.convo_id,
        feedback: feedback.trim(),
      });
      toast.success("Feedback posted to Slack");
      onClose();
    } catch (e) {
      toast.error("Failed to post feedback: " + e.message);
    } finally {
      setSaving(false);
    }
  }

  return createPortal(
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/40" onClick={onClose} />

      <div className="w-full max-w-3xl bg-background shadow-xl flex flex-col overflow-hidden border-l">
        {/* header */}
        <div className="px-6 py-4 border-b flex items-start justify-between gap-4 shrink-0">
          <div className="min-w-0">
            <p className="text-sm font-semibold truncate">{convo.title || convo.convo_id}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{convo.created_at} · {convo.message_count} messages</p>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground shrink-0 mt-0.5">✕</button>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">Loading…</div>
        ) : (
          <div className="flex-1 overflow-y-auto flex flex-col">
            {/* chat thread */}
            <div className="px-6 py-4 space-y-3 border-b">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Conversation</p>
              {(thread || []).map((msg, i) => (
                <div key={i} className={`flex ${msg.is_agent ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm shadow-sm ${
                    msg.is_agent
                      ? "bg-primary text-primary-foreground rounded-br-sm"
                      : "bg-muted text-foreground rounded-bl-sm"
                  }`}>
                    <p className={`text-[10px] font-medium mb-1 ${msg.is_agent ? "text-primary-foreground/70" : "text-muted-foreground"}`}>
                      {msg.is_agent ? msg.alias : "Client"}
                    </p>
                    <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                    <p className={`text-[10px] mt-1 ${msg.is_agent ? "text-primary-foreground/50" : "text-muted-foreground/60"}`}>
                      {msg.timestamp}
                    </p>
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>

            {/* feedback form */}
            <div className="px-6 py-5 space-y-4">
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Feedback</Label>
                <Textarea
                  value={feedback}
                  onChange={e => setFeedback(e.target.value)}
                  placeholder="What went well? What could be improved?"
                  rows={5}
                  className="text-sm resize-none"
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Reviewer name</Label>
                <Input
                  value={reviewer}
                  onChange={e => handleReviewerChange(e.target.value)}
                  placeholder="Your name"
                  className="h-8 text-sm"
                />
              </div>

              <div className="flex gap-2 pt-1">
                <Button onClick={handleSave} disabled={saving} className="flex-1">
                  {saving ? "Saving…" : "Save feedback"}
                </Button>
                <Button variant="outline" onClick={onClose} className="flex-1">Cancel</Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>,
    document.body
  );
}

// ── ChatQA (main export) ──────────────────────────────────────────────────────

export default function ChatQA() {
  const [startDate, setStartDate] = useState(weekAgo);
  const [endDate, setEndDate] = useState(today);
  const [agents, setAgents] = useState(null);
  const [agentsLoading, setAgentsLoading] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [conversations, setConversations] = useState(null);
  const [convosLoading, setConvosLoading] = useState(false);
  const [selectedConvo, setSelectedConvo] = useState(null);
  const [error, setError] = useState(null);

  async function handleSearch(e) {
    e.preventDefault();
    setAgentsLoading(true);
    setError(null);
    setAgents(null);
    setConversations(null);
    setSelectedAgent(null);
    setSelectedConvo(null);
    try {
      const data = await fetchConversationAgents(startDate, endDate);
      setAgents(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setAgentsLoading(false);
    }
  }

  async function handleAgentSelect(agent) {
    setSelectedAgent(agent);
    setConversations(null);
    setSelectedConvo(null);
    setConvosLoading(true);
    try {
      const data = await fetchConversations(agent.email, startDate, endDate);
      setConversations(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setConvosLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      {/* Search form */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Select Date Range</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSearch} className="flex items-end gap-3 flex-wrap">
            <div className="space-y-1">
              <Label className="text-xs">Start date</Label>
              <Input
                type="date"
                value={startDate}
                onChange={e => setStartDate(e.target.value)}
                className="h-8 text-sm w-40"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">End date</Label>
              <Input
                type="date"
                value={endDate}
                onChange={e => setEndDate(e.target.value)}
                className="h-8 text-sm w-40"
              />
            </div>
            <Button type="submit" disabled={agentsLoading} className="h-8 text-sm">
              {agentsLoading ? "Loading…" : "Find agents"}
            </Button>
            {error && <p className="text-xs text-destructive">{error}</p>}
          </form>
        </CardContent>
      </Card>

      {/* Agent list */}
      {agents !== null && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">
              {agents.length} agent{agents.length !== 1 ? "s" : ""} with conversations
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {agents.length === 0 ? (
              <p className="px-4 py-4 text-sm text-muted-foreground">No conversations found in this date range.</p>
            ) : (
              <div className="divide-y">
                {agents.map(a => (
                  <button
                    key={a.email}
                    onClick={() => handleAgentSelect(a)}
                    className={`w-full text-left px-4 py-3 flex items-center justify-between hover:bg-muted/50 transition-colors ${selectedAgent?.email === a.email ? "bg-muted" : ""}`}
                  >
                    <div>
                      <p className="text-sm font-medium">{a.display_name}</p>
                      <p className="text-xs text-muted-foreground">{a.email}</p>
                    </div>
                    <span className="text-xs text-muted-foreground shrink-0">{a.convo_count} convo{a.convo_count !== 1 ? "s" : ""}</span>
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Conversations list */}
      {selectedAgent && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">
              {convosLoading
                ? "Loading conversations…"
                : conversations !== null
                  ? `${conversations.length} conversation${conversations.length !== 1 ? "s" : ""} — ${selectedAgent.display_name}`
                  : `Conversations — ${selectedAgent.display_name}`}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {convosLoading ? (
              <p className="px-4 py-4 text-sm text-muted-foreground">Loading…</p>
            ) : conversations?.length === 0 ? (
              <p className="px-4 py-4 text-sm text-muted-foreground">No conversations found.</p>
            ) : (
              <div className="divide-y">
                {(conversations || []).map(c => (
                  <button
                    key={c.convo_id}
                    onClick={() => setSelectedConvo({ ...c, agent_email: selectedAgent?.email || "" })}
                    className="w-full text-left px-4 py-3 hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{c.title || c.convo_id}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">{c.created_at}</p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                          c.status === "closed"
                            ? "bg-green-100 text-green-700"
                            : "bg-amber-100 text-amber-700"
                        }`}>
                          {c.status || "unknown"}
                        </span>
                        <span className="text-xs text-muted-foreground">{c.message_count} msg</span>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Slide-over */}
      {selectedConvo && (
        <ConversationSlideOver
          convo={selectedConvo}
          onClose={() => setSelectedConvo(null)}
        />
      )}
    </div>
  );
}
