import { useEffect, useState } from "react";
import { fetchAgents } from "../api";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const today = new Date().toISOString().slice(0, 10);
const weekAgo = new Date(Date.now() - 7 * 86400000).toISOString().slice(0, 10);

const TIER_STYLES = {
  "III": { dot: "bg-purple-500", label: "text-purple-700 bg-purple-50 border-purple-200", display: "COM/TL" },
  "II":  { dot: "bg-blue-500",   label: "text-blue-700 bg-blue-50 border-blue-200",       display: "COSII" },
  "I":   { dot: "bg-slate-400",  label: "text-slate-600 bg-slate-50 border-slate-200",    display: "COSI" },
  "—":   { dot: "bg-gray-300",   label: "text-gray-500 bg-gray-50 border-gray-200",       display: "COS" },
};

const TIER_FILTERS = [
  { value: "all", label: "All" },
  { value: "I",   label: "COSI" },
  { value: "II",  label: "COSII" },
  { value: "III", label: "COM/TL" },
];

export function TierBadge({ tier, className = "" }) {
  const style = TIER_STYLES[tier] ?? TIER_STYLES["—"];
  return (
    <span
      className={`inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded border leading-none ${style.label} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
      {style.display}
    </span>
  );
}

export default function AgentPicker({ onSearch }) {
  const [startDate, setStartDate] = useState(weekAgo);
  const [endDate, setEndDate] = useState(today);

  const [agents, setAgents] = useState([]);
  const [agentsLoading, setAgentsLoading] = useState(false);
  const [agentsError, setAgentsError] = useState(null);
  const [agentId, setAgentId] = useState("");
  const [tierFilter, setTierFilter] = useState("all");

  function loadAgents(start, end) {
    setAgentsLoading(true);
    setAgentsError(null);
    setAgents([]);
    setAgentId("");
    fetchAgents(start, end)
      .then((data) => {
        setAgents(data);
        if (data.length > 0) setAgentId(data[0].id);
      })
      .catch((e) => setAgentsError(e.message))
      .finally(() => setAgentsLoading(false));
  }

  useEffect(() => {
    loadAgents(startDate, endDate);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleDateBlur() {
    if (startDate && endDate && startDate <= endDate) {
      loadAgents(startDate, endDate);
    }
  }

  function handleSearch(e) {
    e.preventDefault();
    if (!agentId) return;
    const agent = agents.find((a) => a.id === agentId);
    onSearch({ agentId, startDate, endDate, agent });
  }

  const filteredAgents = tierFilter === "all" ? agents : agents.filter((a) => a.tier === tierFilter);
  const selectedAgent = agents.find((a) => a.id === agentId);

  function handleTierFilter(tier) {
    setTierFilter(tier);
    const match = (tier === "all" ? agents : agents.filter((a) => a.tier === tier));
    if (match.length > 0) setAgentId(match[0].id);
    else setAgentId("");
  }

  return (
    <form onSubmit={handleSearch} className="flex flex-wrap gap-4 items-end">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="from">From</Label>
        <Input
          id="from"
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          onBlur={handleDateBlur}
          required
          className="w-36"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="to">To</Label>
        <Input
          id="to"
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          onBlur={handleDateBlur}
          required
          className="w-36"
        />
      </div>

      {/* Tier filter */}
      <div className="flex flex-col gap-1.5">
        <Label>Tier</Label>
        <div className="flex rounded-md border overflow-hidden h-9">
          {TIER_FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              onClick={() => handleTierFilter(f.value)}
              className={`px-3 text-xs font-medium border-r last:border-r-0 transition-colors ${
                tierFilter === f.value
                  ? "bg-primary text-primary-foreground"
                  : "bg-background text-muted-foreground hover:bg-muted"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-1.5 flex-1 min-w-[280px]">
        <Label htmlFor="agent">
          COS Agent
          {agentsLoading && (
            <span className="ml-2 text-xs text-muted-foreground font-normal">Loading…</span>
          )}
          {!agentsLoading && filteredAgents.length > 0 && (
            <span className="ml-2 text-xs text-muted-foreground font-normal">
              {filteredAgents.length} agent{filteredAgents.length !== 1 ? "s" : ""}
            </span>
          )}
        </Label>
        <Select
          value={agentId}
          onValueChange={setAgentId}
          disabled={agentsLoading || filteredAgents.length === 0}
          required
        >
          <SelectTrigger id="agent" className="w-full">
            <SelectValue
              placeholder={
                agentsLoading
                  ? "Loading agents…"
                  : agentsError
                  ? "Error loading agents"
                  : filteredAgents.length === 0
                  ? "No agents in this period"
                  : "Select agent…"
              }
            >
              {selectedAgent && (
                <span className="flex items-center gap-2 min-w-0">
                  <TierBadge tier={selectedAgent.tier} />
                  <span className="truncate">{selectedAgent.full_name}</span>
                  <span className="text-muted-foreground text-xs shrink-0">
                    {selectedAgent.call_count} calls
                  </span>
                </span>
              )}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {filteredAgents.map((a) => (
              <SelectItem key={a.id} value={a.id}>
                <span className="flex items-center gap-2 w-full">
                  <TierBadge tier={a.tier} />
                  <span className="flex-1">{a.full_name}</span>
                  <span className="text-muted-foreground text-xs">
                    {a.call_count} calls
                  </span>
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {agentsError && (
          <p className="text-xs text-destructive">{agentsError}</p>
        )}
      </div>

      <Button type="submit" disabled={!agentId || agentsLoading}>
        Pull Calls
      </Button>
    </form>
  );
}
