import { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { fetchAiScore, fetchTranscript, fetchWiraTickets, submitReview } from "../api";
import { TierBadge } from "./AgentPicker";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const SECTIONS = ["Call Handling", "Problem Solving", "Ownership & Coaching"];

const SCORE_COLORS = {
  1: {
    active: "bg-destructive text-destructive-foreground border-destructive",
    hover:  "hover:border-destructive hover:text-destructive",
    tip:    "border-destructive/30 bg-red-50 text-red-800",
  },
  2: {
    active: "bg-amber-400 text-white border-amber-400",
    hover:  "hover:border-amber-400 hover:text-amber-600",
    tip:    "border-amber-300/50 bg-amber-50 text-amber-800",
  },
  3: {
    active: "bg-green-500 text-white border-green-500",
    hover:  "hover:border-green-500 hover:text-green-600",
    tip:    "border-green-300/50 bg-green-50 text-green-800",
  },
};

function ScoreButton({ value, active, onClick, tipText }) {
  const [tipRect, setTipRect] = useState(null);
  const ref = useRef(null);
  const c = SCORE_COLORS[value];
  const base = "w-8 h-8 rounded-full text-sm font-semibold border transition-all";
  const cls = active
    ? `${base} ${c.active}`
    : `${base} border-border text-muted-foreground ${c.hover}`;

  function handleMouseEnter() {
    if (ref.current) setTipRect(ref.current.getBoundingClientRect());
  }

  return (
    <div
      ref={ref}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={() => setTipRect(null)}
    >
      <button type="button" onClick={onClick} className={cls}>
        {value}
      </button>
      {tipRect && tipText && createPortal(
        <div
          className={`fixed text-xs rounded-md border px-2.5 py-2 shadow-md z-[9999] pointer-events-none leading-relaxed w-56 ${c.tip}`}
          style={{
            top: tipRect.top - 8,
            left: tipRect.left + tipRect.width / 2,
            transform: "translateX(-50%) translateY(-100%)",
          }}
        >
          <span className="font-semibold block mb-0.5">
            {value === 1 ? "Needs improvement" : value === 2 ? "Meets standard" : "Exceeds standard"}
          </span>
          {tipText}
        </div>,
        document.body
      )}
    </div>
  );
}

export default function QAReview({ call, agent, rubric, onClose, onSubmitted }) {
  const [transcript, setTranscript] = useState(null);
  const [transcriptLoading, setTranscriptLoading] = useState(false);
  const [aiScores, setAiScores] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState(null);
  const [wiraTickets, setWiraTickets] = useState(null);

  useEffect(() => {
    fetchWiraTickets(call.call_id).then(setWiraTickets).catch(() => setWiraTickets([]));
  }, [call.call_id]);

  useEffect(() => {
    loadTranscript();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [scores, setScores] = useState(() =>
    Object.fromEntries(rubric.map((c) => [c.id, null]))
  );
  const [reviewer, setReviewer] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  async function loadTranscript() {
    setTranscriptLoading(true);
    try {
      const { transcript: t } = await fetchTranscript(call.call_id);
      setTranscript(t || "No transcript available.");
    } catch (e) {
      setTranscript("Failed to load transcript: " + e.message);
    } finally {
      setTranscriptLoading(false);
    }
  }

  async function runAiScore() {
    setAiLoading(true);
    setAiError(null);
    try {
      const result = await fetchAiScore(call.call_id);
      setAiScores(result);
      setScores(Object.fromEntries(Object.entries(result).map(([k, v]) => [k, v.score])));
    } catch (e) {
      setAiError(e.message);
    } finally {
      setAiLoading(false);
    }
  }

  function computeTotal(s) {
    return rubric.reduce((acc, c) => {
      const score = s[c.id];
      if (score == null) return acc;
      return acc + ((score - 1) / 2) * c.weight;
    }, 0) * 100;
  }

  const unscoredCount = rubric.filter((c) => scores[c.id] == null).length;
  const total = computeTotal(scores);
  const totalColor = total >= 80 ? "text-green-600" : total >= 60 ? "text-amber-600" : "text-destructive";

  async function handleSubmit(e) {
    e.preventDefault();
    if (!reviewer.trim()) {
      setSubmitError("Please enter your name before submitting.");
      return;
    }
    if (unscoredCount > 0) {
      setSubmitError(`${unscoredCount} criteria still unscored.`);
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    try {
      await submitReview({
        reviewer: reviewer.trim(),
        agent_name: agent.full_name,
        agent_id: agent.id,
        call,
        scores,
        ai_scores: aiScores || {},
        notes,
      });
      onSubmitted(computeTotal(scores));
    } catch (e) {
      setSubmitError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  const duration = `${Math.floor(call.duration_seconds / 60)}:${String(call.duration_seconds % 60).padStart(2, "0")}`;

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="w-[96vw] max-w-[1400px] h-[92vh] flex flex-col p-0 gap-0">

        {/* Header */}
        <DialogHeader className="px-6 py-4 border-b shrink-0">
          <div className="flex items-center justify-between gap-4">
            <DialogTitle className="text-base flex items-center gap-2">
              QA Review — {agent.full_name}
              {agent.gd_username && (
                <span className="font-mono text-xs text-muted-foreground font-normal">
                  ({agent.gd_username})
                </span>
              )}
              {agent.tier && <TierBadge tier={agent.tier} />}
            </DialogTitle>
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <span className="font-mono text-xs">{call.call_id}</span>
              <span>{call.call_started?.slice(0, 16)}</span>
              <span>{duration}</span>
            </div>
          </div>
        </DialogHeader>

        {/* Two-column body */}
        <div className="flex flex-1 min-h-0 divide-x overflow-hidden">

          {/* Left: call info + recording link + transcript */}
          <div className="w-80 xl:w-96 shrink-0 flex flex-col overflow-hidden">
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">

              {/* Recording link — prominent */}
              {call.greendot_url ? (
                <a
                  href={call.greendot_url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-center gap-2 w-full rounded-md border border-primary/30 bg-primary/5 px-3 py-2.5 text-sm font-medium text-primary hover:bg-primary/10 transition-colors"
                >
                  ▶ Open call recording
                </a>
              ) : (
                <div className="flex items-center justify-center w-full rounded-md border border-dashed px-3 py-2.5 text-xs text-muted-foreground">
                  No recording available
                </div>
              )}

              {/* AI score button */}
              <Button
                type="button"
                variant="secondary"
                className="w-full"
                onClick={runAiScore}
                disabled={aiLoading}
              >
                {aiLoading ? "Scoring…" : "✦ Auto-score with Claude"}
              </Button>
              {aiScores && (
                <p className="text-xs text-muted-foreground text-center -mt-2">
                  AI scores applied — adjust if needed
                </p>
              )}
              {aiError && <p className="text-xs text-destructive text-center">{aiError}</p>}

              <Separator />

              {/* WIRA Tickets */}
              {wiraTickets === null ? (
                <p className="text-xs text-muted-foreground">Loading tickets…</p>
              ) : wiraTickets.length > 0 && (
                <div className="space-y-1.5">
                  <Label className="text-sm">WIRA Tickets</Label>
                  {wiraTickets.map((t) => (
                    <a
                      key={t.task_id}
                      href={t.url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-start gap-2 rounded-md border px-2.5 py-2 text-xs hover:bg-muted/50 transition-colors group"
                    >
                      <span className="flex-1 min-w-0 space-y-0.5">
                        <span className="font-medium group-hover:text-primary leading-snug block">{t.title || "—"}</span>
                        <span className="text-muted-foreground flex gap-2 flex-wrap">
                          {t.task_category && <span>{t.task_category}</span>}
                          {t.task_intent && <span className="text-foreground/70">{t.task_intent}</span>}
                        </span>
                      </span>
                      <span className={`shrink-0 mt-0.5 px-1.5 py-0.5 rounded text-[10px] font-semibold leading-none ${
                        t.status === "closed" ? "bg-green-50 text-green-700" :
                        t.status === "open" ? "bg-amber-50 text-amber-700" :
                        "bg-muted text-muted-foreground"
                      }`}>{t.status}</span>
                    </a>
                  ))}
                </div>
              )}

              <Separator />

              {/* Transcript */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-sm">Transcript</Label>
                  {!transcript && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={loadTranscript}
                      disabled={transcriptLoading}
                      className="h-6 text-xs px-2"
                    >
                      {transcriptLoading ? "Loading…" : "Load"}
                    </Button>
                  )}
                </div>
                {transcript ? (
                  <div
                    className="overflow-y-auto rounded-md border bg-muted/40 p-3"
                    style={{ maxHeight: "calc(92vh - 300px)" }}
                  >
                    <pre className="text-xs whitespace-pre-wrap text-muted-foreground leading-relaxed">
                      {transcript}
                    </pre>
                  </div>
                ) : (
                  <div
                    className="rounded-md border border-dashed bg-muted/20 flex items-center justify-center text-xs text-muted-foreground"
                    style={{ height: "160px" }}
                  >
                    Click Load to view transcript
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right: scorecard + reviewer */}
          <form
            id="qa-form"
            onSubmit={handleSubmit}
            className="flex-1 overflow-y-auto px-6 py-4 space-y-5"
          >
            {SECTIONS.map((section) => {
              const criteria = rubric.filter((c) => c.section === section);
              return (
                <div key={section} className="space-y-3">
                  <div className="flex items-center gap-2">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground whitespace-nowrap">
                      {section}
                    </h3>
                    <Separator className="flex-1" />
                  </div>
                  {criteria.map((c) => (
                    <div key={c.id} className="flex items-start gap-3">
                      <div className="flex-1 min-w-0 space-y-0.5">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-mono font-semibold text-muted-foreground w-5 shrink-0">
                            {c.id}
                          </span>
                          <span className="text-sm font-medium">{c.name}</span>
                          <span className="text-xs text-muted-foreground">
                            {Math.round(c.weight * 100)}%
                          </span>
                        </div>
                        {aiScores?.[c.id]?.justification && (
                          <p className="text-xs text-muted-foreground ml-7 leading-relaxed">
                            {aiScores[c.id].justification}
                          </p>
                        )}
                      </div>
                      <div className="flex gap-1.5 shrink-0 pt-0.5">
                        {[1, 2, 3].map((v) => (
                          <ScoreButton
                            key={v}
                            value={v}
                            active={scores[c.id] === v}
                            onClick={() => setScores((s) => ({ ...s, [c.id]: v }))}
                            tipText={c[`score_${v}`]}
                          />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              );
            })}

            {/* Total score */}
            <div className="flex items-center justify-between rounded-lg border bg-muted/30 px-4 py-3">
              <div>
                <span className="text-sm font-medium">Total QA Score</span>
                {unscoredCount > 0 && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    ({unscoredCount} unscored)
                  </span>
                )}
              </div>
              <span className={`text-3xl font-bold tabular-nums ${unscoredCount > 0 ? "text-muted-foreground" : totalColor}`}>
                {unscoredCount > 0 ? "—" : `${total.toFixed(1)}%`}
              </span>
            </div>

            {/* Reviewer + notes */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="reviewer">Your name</Label>
                <Input
                  id="reviewer"
                  value={reviewer}
                  onChange={(e) => setReviewer(e.target.value)}
                  placeholder="Reviewer name"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="notes">Coaching notes</Label>
                <Textarea
                  id="notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                  placeholder="Optional coaching points…"
                  className="resize-none"
                />
              </div>
            </div>

            {submitError && <p className="text-sm text-destructive">{submitError}</p>}
          </form>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t bg-muted/20 shrink-0">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="qa-form" disabled={submitting || unscoredCount > 0}>
            {submitting ? "Saving…" : `Save to Google Sheets${unscoredCount > 0 ? ` (${unscoredCount} unscored)` : ""}`}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
