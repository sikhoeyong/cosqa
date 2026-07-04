import { useState, Fragment } from "react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const PAGE_SIZE = 20;

function fmt(secs) {
  if (!secs && secs !== 0) return "—";
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

const SKILL_COLORS = {
  green_dot:            "bg-green-100 text-green-800",
  chinese_assistant:    "bg-purple-100 text-purple-800",
  chinese:              "bg-purple-100 text-purple-800",
  client:               "bg-blue-100 text-blue-800",
  new_customer:         "bg-amber-100 text-amber-800",
  spanish:              "bg-orange-100 text-orange-800",
  manager:              "bg-red-100 text-red-800",
  subject_matter_expert:"bg-teal-100 text-teal-800",
  delivery_enabled:     "bg-cyan-100 text-cyan-800",
  party_orders:         "bg-pink-100 text-pink-800",
};

function SkillTags({ skills }) {
  if (!skills) return <span className="text-muted-foreground text-xs">—</span>;
  const tags = skills.split(";").map(s => s.trim()).filter(s => s && s !== "green_dot");
  return (
    <div className="flex flex-wrap gap-1">
      {tags.map(tag => (
        <span
          key={tag}
          className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium leading-none ${SKILL_COLORS[tag] ?? "bg-muted text-muted-foreground"}`}
        >
          {tag.replace(/_/g, " ")}
        </span>
      ))}
    </div>
  );
}

const TYPE_LABEL = {
  agent: "Agent",
  client: "Client",
  customer: "Customer",
  outbound: "3-way",
};

export default function CallList({ calls, loading, error, lastCallDate, agentName, onSelect, selectedId, reviewsMap = {} }) {
  const [page, setPage] = useState(0);
  const [expandedRelated, setExpandedRelated] = useState(new Set());

  function toggleRelated(e, callId) {
    e.stopPropagation();
    setExpandedRelated(prev => {
      const next = new Set(prev);
      next.has(callId) ? next.delete(callId) : next.add(callId);
      return next;
    });
  }

  if (loading) return <p className="text-sm text-muted-foreground px-4 py-4">Loading calls…</p>;
  if (error) return <p className="text-sm text-destructive px-4 py-4">Error: {error}</p>;
  if (!calls) return null;
  if (calls.length === 0) {
    return (
      <div className="px-4 py-6 space-y-1">
        <p className="text-sm text-muted-foreground">
          No calls found for {agentName ?? "this agent"} in the selected period.
        </p>
        {lastCallDate && (
          <p className="text-xs text-muted-foreground">
            Last recorded call: <span className="font-medium text-foreground">{lastCallDate}</span>
            {" "}— try adjusting the date range.
          </p>
        )}
      </div>
    );
  }

  const totalPages = Math.ceil(calls.length / PAGE_SIZE);
  const pageCalls = calls.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Date & Time</TableHead>
            <TableHead>AHT / ATT / AWT</TableHead>
            <TableHead>Skills</TableHead>
            <TableHead>Recording</TableHead>
            <TableHead>WIRA</TableHead>
            <TableHead>Related</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {pageCalls.map((c) => (
            <Fragment key={c.call_id}>
            <TableRow
              onClick={() => onSelect(c)}
              className={`cursor-pointer ${selectedId === c.call_id ? "bg-muted" : ""}`}
            >
              <TableCell className="font-mono text-xs">{c.call_started}</TableCell>
              <TableCell>
                {(() => {
                  const aht = (c.att_seconds || 0) + (c.awt_seconds || 0) + (c.acw_seconds || 0);
                  return aht > 0 ? (
                    <div className="space-y-0.5">
                      <div className="font-mono text-xs font-medium">{aht}s</div>
                      <div className="text-[10px] text-muted-foreground font-mono leading-none">
                        {c.att_seconds}s · {c.awt_seconds}s
                      </div>
                    </div>
                  ) : <span className="text-muted-foreground text-xs">—</span>;
                })()}
              </TableCell>
              <TableCell><SkillTags skills={c.skills_required} /></TableCell>
              <TableCell onClick={e => e.stopPropagation()}>
                {c.greendot_url ? (
                  <a
                    href={c.greendot_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-primary hover:underline"
                  >
                    ▶ Open
                  </a>
                ) : (
                  <span className="text-muted-foreground text-xs">—</span>
                )}
              </TableCell>
              <TableCell onClick={e => e.stopPropagation()}>
                {c.wira_tickets?.length > 0 ? (
                  <div className="flex flex-col gap-0.5">
                    {c.wira_tickets.map(t => (
                      <a
                        key={t.task_id}
                        href={t.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-primary hover:underline"
                      >
                        {t.task_id}
                      </a>
                    ))}
                  </div>
                ) : (
                  <span className="text-muted-foreground text-xs">—</span>
                )}
              </TableCell>
              <TableCell onClick={e => e.stopPropagation()}>
                {c.related_calls?.length > 0 ? (
                  <button
                    onClick={e => toggleRelated(e, c.call_id)}
                    className="text-xs text-primary hover:underline"
                  >
                    {c.related_calls.length} {expandedRelated.has(c.call_id) ? "▲" : "▼"}
                  </button>
                ) : (
                  <span className="text-muted-foreground text-xs">—</span>
                )}
              </TableCell>
              <TableCell className="text-right">
                {reviewsMap[c.call_id] ? (
                  <span className={`text-xs font-semibold tabular-nums ${
                    reviewsMap[c.call_id].total_score >= 80 ? "text-green-600" :
                    reviewsMap[c.call_id].total_score >= 60 ? "text-amber-600" :
                    "text-destructive"
                  }`}>
                    {reviewsMap[c.call_id].total_score.toFixed(1)}%
                  </span>
                ) : (
                  <span className="text-xs text-primary hover:underline">Review →</span>
                )}
              </TableCell>
            </TableRow>
            {expandedRelated.has(c.call_id) && c.related_calls?.map(rc => {
              const full = calls.find(x => x.call_id === rc.call_id);
              return (
                <TableRow
                  key={rc.call_id}
                  onClick={() => full && onSelect(full)}
                  className={`bg-muted/40 border-l-2 border-primary/30 ${full ? "cursor-pointer hover:bg-muted/60" : ""} ${selectedId === rc.call_id ? "bg-muted" : ""}`}
                >
                  <TableCell className="font-mono text-xs pl-8 text-muted-foreground">
                    {full ? full.call_started : rc.call_id.slice(0, 8) + "…"}
                  </TableCell>
                  <TableCell>{full ? fmt(full.duration_seconds) : "—"}</TableCell>
                  <TableCell>
                    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium ${
                      rc.type === "client" ? "bg-blue-100 text-blue-800" :
                      rc.type === "customer" ? "bg-amber-100 text-amber-800" :
                      rc.type === "outbound" ? "bg-green-100 text-green-800" :
                      "bg-muted text-muted-foreground"
                    }`}>
                      {TYPE_LABEL[rc.type] ?? rc.type}
                    </span>
                  </TableCell>
                  <TableCell colSpan={3} className="text-xs text-muted-foreground">
                    {full ? "" : <span className="font-mono">{rc.call_id}</span>}
                  </TableCell>
                </TableRow>
              );
            })}
            </Fragment>
          ))}
        </TableBody>
      </Table>
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t">
          <span className="text-xs text-muted-foreground">
            {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, calls.length)} of {calls.length}
          </span>
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="sm" onClick={() => setPage(0)} disabled={page === 0} className="h-7 px-2 text-xs">«</Button>
            <Button variant="ghost" size="sm" onClick={() => setPage(p => p - 1)} disabled={page === 0} className="h-7 px-2 text-xs">‹ Prev</Button>
            <span className="text-xs px-2">Page {page + 1} of {totalPages}</span>
            <Button variant="ghost" size="sm" onClick={() => setPage(p => p + 1)} disabled={page === totalPages - 1} className="h-7 px-2 text-xs">Next ›</Button>
            <Button variant="ghost" size="sm" onClick={() => setPage(totalPages - 1)} disabled={page === totalPages - 1} className="h-7 px-2 text-xs">»</Button>
          </div>
        </div>
      )}
    </div>
  );
}
