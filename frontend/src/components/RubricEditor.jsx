import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { fetchRubric, updateRubric } from "../api";

const SCORE_STYLES = {
  score_1: { label: "Score 1 — Poor",       border: "border-l-destructive", bg: "bg-red-50" },
  score_2: { label: "Score 2 — Acceptable", border: "border-l-amber-400",   bg: "bg-amber-50" },
  score_3: { label: "Score 3 — Excellent",  border: "border-l-green-500",   bg: "bg-green-50" },
};

function CriterionCard({ criterion, onChange }) {
  const { id, name, weight, scoring_notes } = criterion;
  const [showAiContext, setShowAiContext] = useState(false);

  function field(key) {
    return (e) => onChange({ ...criterion, [key]: e.target.value });
  }

  return (
    <div className="rounded-lg border bg-card p-4 space-y-3">
      {/* Header row */}
      <div className="flex items-center gap-3">
        <span className="font-mono text-xs font-bold text-muted-foreground w-6 shrink-0">{id}</span>
        <Input
          value={name}
          onChange={field("name")}
          className="flex-1 h-8 text-sm font-medium"
        />
        <div className="flex items-center gap-1.5 shrink-0">
          <Input
            type="number"
            min={1}
            max={100}
            value={Math.round(weight * 100)}
            onChange={(e) => onChange({ ...criterion, weight: Number(e.target.value) / 100 })}
            className="w-16 h-8 text-xs text-center"
          />
          <span className="text-xs text-muted-foreground">%</span>
        </div>
      </div>

      {/* Score descriptors */}
      <div className="grid grid-cols-3 gap-2">
        {["score_1", "score_2", "score_3"].map((key) => {
          const { label, border, bg } = SCORE_STYLES[key];
          return (
            <div key={key} className={`rounded border-l-2 ${border} ${bg} p-2 space-y-1`}>
              <Label className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">
                {label}
              </Label>
              <Textarea
                value={criterion[key]}
                onChange={field(key)}
                rows={2}
                className="text-xs resize-none bg-transparent border-0 p-0 focus-visible:ring-0 shadow-none"
              />
            </div>
          );
        })}
      </div>

      {/* AI scoring context — collapsible */}
      <div>
        <button
          type="button"
          onClick={() => setShowAiContext(v => !v)}
          className="text-[10px] text-muted-foreground hover:text-foreground transition-colors"
        >
          {showAiContext ? "▲" : "▼"} AI scoring context
        </button>
        {showAiContext && (
          <Textarea
            value={scoring_notes}
            onChange={field("scoring_notes")}
            rows={3}
            placeholder="Edge cases, N/A rules, decision guidance for AI scorer…"
            className="mt-1.5 text-xs resize-none"
          />
        )}
      </div>
    </div>
  );
}

export default function RubricEditor({ onBack, onSaved }) {
  const [criteria, setCriteria] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetchRubric().then(data => setCriteria(data.map(c => ({ ...c })))).catch(e => setError(e.message));
  }, []);

  function handleChange(updated) {
    setCriteria(prev => prev.map(c => c.id === updated.id ? updated : c));
    setSaved(false);
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await updateRubric(criteria);
      setSaved(true);
      onSaved(criteria);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  if (!criteria) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-sm text-muted-foreground">{error ?? "Loading rubric…"}</p>
      </div>
    );
  }

  const sections = [...new Set(criteria.map(c => c.section))];
  const totalWeight = Math.round(criteria.reduce((s, c) => s + c.weight, 0) * 100);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-primary text-primary-foreground px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-base font-semibold tracking-wide">Tarro</span>
          <span className="text-xs opacity-50">|</span>
          <span className="text-sm opacity-80">QA Rubric</span>
        </div>
        <button onClick={onBack} className="text-sm opacity-70 hover:opacity-100 transition-opacity">
          ← Back to QA tool
        </button>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-6 space-y-6">
        {/* Weight summary */}
        <div className="flex items-center justify-between rounded-lg border bg-muted/30 px-4 py-2.5">
          <span className="text-sm text-muted-foreground">
            Total weight: <span className={`font-semibold ${totalWeight === 100 ? "text-green-600" : "text-destructive"}`}>{totalWeight}%</span>
            {totalWeight !== 100 && <span className="ml-2 text-xs text-destructive">(must sum to 100%)</span>}
          </span>
          <div className="flex items-center gap-2">
            {error && <span className="text-xs text-destructive">{error}</span>}
            {saved && <span className="text-xs text-green-600">Saved</span>}
            <Button onClick={handleSave} disabled={saving || totalWeight !== 100} size="sm">
              {saving ? "Saving…" : "Save rubric"}
            </Button>
          </div>
        </div>

        {sections.map((section) => (
          <div key={section} className="space-y-3">
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground whitespace-nowrap">
                {section}
              </h2>
              <Separator className="flex-1" />
            </div>
            {criteria.filter(c => c.section === section).map(c => (
              <CriterionCard key={c.id} criterion={c} onChange={handleChange} />
            ))}
          </div>
        ))}

        <div className="flex justify-end pb-8">
          <Button onClick={handleSave} disabled={saving || totalWeight !== 100}>
            {saving ? "Saving…" : "Save rubric"}
          </Button>
        </div>
      </main>
    </div>
  );
}
