import { useRef } from "react";
import ChunkViewer from "./ChunkViewer";

export default function QueryPanel({
  query,
  setQuery,
  result,
  loading,
  error,
  history,
  onSubmit,
  onHistoryClick,
}) {
  const textareaRef = useRef(null);

  function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSubmit(query);
    }
  }

  return (
    <div className="w-[55%] border-r border-slate-800 flex flex-col overflow-hidden">
      <div className="p-5 border-b border-slate-800">
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask a question about your document corpus..."
            rows={3}
            className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 resize-none focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50 transition-all"
          />
          <button
            onClick={() => onSubmit(query)}
            disabled={loading || !query.trim()}
            className="absolute bottom-3 right-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5"
          >
            {loading ? (
              <>
                <span className="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Running
              </>
            ) : (
              <>
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                </svg>
                Ask
              </>
            )}
          </button>
        </div>
        <p className="text-xs text-slate-600 mt-2">Enter to submit · Shift+Enter for newline</p>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {loading && (
          <div className="space-y-3 animate-pulse">
            <div className="h-3 bg-slate-800 rounded w-3/4" />
            <div className="h-3 bg-slate-800 rounded w-full" />
            <div className="h-3 bg-slate-800 rounded w-5/6" />
            <div className="h-3 bg-slate-800 rounded w-2/3" />
          </div>
        )}

        {error && (
          <div className="bg-red-950/40 border border-red-800/50 rounded-xl p-4">
            <p className="text-sm font-medium text-red-400 mb-1">Error</p>
            <p className="text-sm text-red-300/80">{error}</p>
          </div>
        )}

        {result && !loading && (
          <>
            <div className="flex flex-wrap gap-2">
              {result.cache_hit && (
                <Badge color="emerald" icon="⚡">
                  Cache hit · {(result.cache_similarity * 100).toFixed(1)}% similar
                </Badge>
              )}
              {result.rewrite_happened && (
                <Badge color="amber" icon="✏">
                  Query rewritten · {result.retry_count} retry
                </Badge>
              )}
              {result.route_decision === "direct" && (
                <Badge color="blue" icon="→">
                  Direct answer (no retrieval)
                </Badge>
              )}
              {result.latency_ms?.total && (
                <Badge color="slate" icon="⏱">
                  {result.latency_ms.total}ms total
                </Badge>
              )}
            </div>

            {result.rewrite_happened && result.rewritten_query && (
              <div className="bg-amber-950/30 border border-amber-800/40 rounded-xl p-4 space-y-2">
                <p className="text-xs font-semibold text-amber-400 uppercase tracking-wider">Query Rewrite</p>
                <div className="space-y-1.5">
                  <div>
                    <p className="text-xs text-slate-500 mb-0.5">Original</p>
                    <p className="text-sm text-slate-300 line-through opacity-60">
                      {result.nodes_fired.length > 0 ? query : "-"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 mb-0.5">Rewritten</p>
                    <p className="text-sm text-amber-300">{result.rewritten_query}</p>
                  </div>
                </div>
              </div>
            )}

            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Answer</p>
              <div className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">{result.answer}</div>
            </div>

            {result.retrieved_chunks?.length > 0 && <ChunkViewer chunks={result.retrieved_chunks} />}
          </>
        )}

        {!result && !loading && !error && history.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Recent</p>
            <div className="space-y-2">
              {history.map((h) => (
                <button
                  key={h.ts}
                  onClick={() => onHistoryClick(h.query)}
                  className="w-full text-left p-3 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 transition-colors group"
                >
                  <p className="text-xs text-indigo-400 group-hover:text-indigo-300 truncate">{h.query}</p>
                  <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">{h.answer.slice(0, 80)}...</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {!result && !loading && !error && history.length === 0 && (
          <div className="flex flex-col items-center justify-center h-48 text-center">
            <div className="w-12 h-12 rounded-full bg-slate-900 flex items-center justify-center mb-3">
              <svg className="w-5 h-5 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
            </div>
            <p className="text-sm text-slate-500">Ask something about your corpus</p>
            <p className="text-xs text-slate-600 mt-1">The agent will route, retrieve, grade, and answer</p>
          </div>
        )}
      </div>
    </div>
  );
}

function Badge({ color, icon, children }) {
  const colors = {
    emerald: "bg-emerald-950/50 border-emerald-800/50 text-emerald-400",
    amber: "bg-amber-950/50 border-amber-800/50 text-amber-400",
    blue: "bg-blue-950/50 border-blue-800/50 text-blue-400",
    slate: "bg-slate-900 border-slate-700 text-slate-400",
  };

  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full border ${colors[color]}`}>
      <span>{icon}</span>
      {children}
    </span>
  );
}
