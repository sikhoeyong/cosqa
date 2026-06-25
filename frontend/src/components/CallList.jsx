import { useState } from "react";
import { Badge } from "@/components/ui/badge";
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
  if (!secs) return "—";
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export default function CallList({ calls, loading, error, lastCallDate, agentName, onSelect, selectedId }) {
  const [page, setPage] = useState(0);

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
            <TableHead>Duration</TableHead>
            <TableHead>Skills</TableHead>
            <TableHead>Order</TableHead>
            <TableHead>Transcript</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {pageCalls.map((c) => (
            <TableRow
              key={c.call_id}
              onClick={() => onSelect(c)}
              className={`cursor-pointer ${selectedId === c.call_id ? "bg-muted" : ""}`}
            >
              <TableCell className="font-mono text-xs">{c.call_started}</TableCell>
              <TableCell>{fmt(c.duration_seconds)}</TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {c.skills_required || "—"}
              </TableCell>
              <TableCell>
                {c.is_order_converted === true || c.is_order_converted === "true" ? (
                  <Badge variant="secondary" className="text-green-700 bg-green-50">Yes</Badge>
                ) : (
                  <span className="text-muted-foreground text-xs">No</span>
                )}
              </TableCell>
              <TableCell>
                {c.has_transcript ? (
                  <Badge variant="outline" className="text-xs">Available</Badge>
                ) : (
                  <span className="text-muted-foreground text-xs">None</span>
                )}
              </TableCell>
              <TableCell className="text-right">
                <span className="text-xs text-primary hover:underline">Review →</span>
              </TableCell>
            </TableRow>
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
