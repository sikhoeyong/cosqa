import { useEffect, useState } from "react";
import { Toaster, toast } from "sonner";
import AgentPicker from "./components/AgentPicker";
import CallList from "./components/CallList";
import QAReview from "./components/QAReview";
import RubricEditor from "./components/RubricEditor";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchCalls, fetchRubric, fetchReviews } from "./api";

export default function App() {
  const [rubric, setRubric] = useState([]);
  const [calls, setCalls] = useState(null);
  const [callsKey, setCallsKey] = useState(0);
  const [lastCallDate, setLastCallDate] = useState(null);
  const [callsLoading, setCallsLoading] = useState(false);
  const [callsError, setCallsError] = useState(null);
  const [selectedCall, setSelectedCall] = useState(null);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [reviewsMap, setReviewsMap] = useState({});
  const [searchParams, setSearchParams] = useState(null);
  const [view, setView] = useState("qa");

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
    setSearchParams({ agentId, startDate, endDate });
    try {
      const [{ calls: data, last_call_date }, reviews] = await Promise.all([
        fetchCalls(agentId, startDate, endDate),
        fetchReviews(agentId, startDate, endDate).catch(() => []),
      ]);
      setCalls(data);
      setLastCallDate(last_call_date);
      setReviewsMap(Object.fromEntries(reviews.map(r => [r.call_id, r])));
    } catch (e) {
      setCallsError(e.message);
    } finally {
      setCallsLoading(false);
    }
  }

  async function handleSubmitted(total, callId) {
    setSelectedCall(null);
    if (total !== null) {
      toast.success(`Review saved — QA score: ${total.toFixed(1)}%`);
    } else {
      toast.info("Review deleted.");
    }
    if (searchParams) {
      const { agentId, startDate, endDate } = searchParams;
      const reviews = await fetchReviews(agentId, startDate, endDate).catch(() => []);
      setReviewsMap(Object.fromEntries(reviews.map(r => [r.call_id, r])));
    }
  }

  if (view === "rubric") {
    return (
      <RubricEditor
        onBack={() => setView("qa")}
        onSaved={(updated) => { setRubric(updated); setView("qa"); }}
      />
    );
  }

  return (
    <div className="min-h-screen bg-background text-left">
      <header className="border-b bg-primary text-primary-foreground px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-base font-semibold tracking-wide">Tarro</span>
            <span className="text-xs opacity-50">|</span>
            <span className="text-sm opacity-80">COS QA</span>
          </div>
          <button
            onClick={() => setView("rubric")}
            className="text-xs opacity-60 hover:opacity-100 transition-opacity"
          >
            Edit rubric
          </button>
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
                reviewsMap={reviewsMap}
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
          existingReview={reviewsMap[selectedCall.call_id] ?? null}
          onClose={() => setSelectedCall(null)}
          onSubmitted={handleSubmitted}
        />
      )}

      <Toaster richColors position="bottom-right" />
    </div>
  );
}
