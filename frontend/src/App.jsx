import { useEffect, useState } from "react";
import { Toaster, toast } from "sonner";
import AgentPicker from "./components/AgentPicker";
import CallList from "./components/CallList";
import QAReview from "./components/QAReview";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchCalls, fetchRubric } from "./api";

export default function App() {
  const [rubric, setRubric] = useState([]);
  const [calls, setCalls] = useState(null);
  const [callsKey, setCallsKey] = useState(0);
  const [lastCallDate, setLastCallDate] = useState(null);
  const [callsLoading, setCallsLoading] = useState(false);
  const [callsError, setCallsError] = useState(null);
  const [selectedCall, setSelectedCall] = useState(null);
  const [selectedAgent, setSelectedAgent] = useState(null);

  useEffect(() => {
    fetchRubric().then(setRubric).catch(console.error);
  }, []);

  async function handleSearch({ agentId, startDate, endDate, agent }) {
    setCallsLoading(true);
    setCallsError(null);
    setCalls(null);
    setCallsKey(k => k + 1);
    setLastCallDate(null);
    setSelectedCall(null);
    setSelectedAgent(agent);
    try {
      const { calls: data, last_call_date } = await fetchCalls(agentId, startDate, endDate);
      setCalls(data);
      setLastCallDate(last_call_date);
    } catch (e) {
      setCallsError(e.message);
    } finally {
      setCallsLoading(false);
    }
  }

  function handleSubmitted(total) {
    setSelectedCall(null);
    toast.success(`Review saved — QA score: ${total.toFixed(1)}%`);
  }

  return (
    <div className="min-h-screen bg-background text-left">
      <header className="border-b bg-primary text-primary-foreground px-6 py-4">
        <div className="flex items-center gap-3">
          <span className="text-base font-semibold tracking-wide">Tarro</span>
          <span className="text-xs opacity-50">|</span>
          <span className="text-sm opacity-80">COS QA</span>
        </div>
      </header>

      <main className="px-6 py-6 space-y-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Select Agent & Date Range</CardTitle>
          </CardHeader>
          <CardContent>
            <AgentPicker onSearch={handleSearch} />
          </CardContent>
        </Card>

        {(calls !== null || callsLoading || callsError) && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">
                {calls
                  ? `${calls.length} call${calls.length !== 1 ? "s" : ""} found`
                  : "Calls"}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <CallList
                key={callsKey}
                calls={calls}
                loading={callsLoading}
                error={callsError}
                lastCallDate={lastCallDate}
                agentName={selectedAgent?.full_name}
                onSelect={setSelectedCall}
                selectedId={selectedCall?.call_id}
              />
            </CardContent>
          </Card>
        )}
      </main>

      {selectedCall && selectedAgent && rubric.length > 0 && (
        <QAReview
          call={selectedCall}
          agent={selectedAgent}
          rubric={rubric}
          onClose={() => setSelectedCall(null)}
          onSubmitted={handleSubmitted}
        />
      )}

      <Toaster richColors position="bottom-right" />
    </div>
  );
}
