import { useState } from "react";
import QueryPanel from "./components/QueryPanel";
import ReasoningTrace from "./components/ReasoningTrace";
import { queryAPI, clearCache } from "./api/client";

export default function App() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);

  async function handleSubmit(q) {
    if (!q.trim() || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await queryAPI(q);
      setResult(data);
      setHistory((h) => [{ query: q, answer: data.answer, ts: Date.now() }, ...h].slice(0, 10));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleClearCache() {
    await clearCache();
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <header className="border-b border-slate-800 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
          </div>
          <div>
            <h1 className="text-sm font-semibold text-white leading-none">Agentic RAG</h1>
            <p className="text-xs text-slate-500 mt-0.5">Self-Correcting Retrieval · LangGraph</p>
          </div>
        </div>
        <button
          onClick={handleClearCache}
          className="text-xs text-slate-500 hover:text-slate-300 transition-colors px-2 py-1 rounded border border-slate-800 hover:border-slate-600"
        >
          Clear Cache
        </button>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <QueryPanel
          query={query}
          setQuery={setQuery}
          result={result}
          loading={loading}
          error={error}
          history={history}
          onSubmit={handleSubmit}
          onHistoryClick={(q) => {
            setQuery(q);
            handleSubmit(q);
          }}
        />
        <ReasoningTrace result={result} loading={loading} />
      </div>
    </div>
  );
}
