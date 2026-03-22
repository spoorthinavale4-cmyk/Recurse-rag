const NODE_META = {
  route_query: {
    label: "Route Query",
    desc: "Classified query type",
    color: "blue",
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8 9l4-4 4 4m0 6l-4 4-4-4" />
      </svg>
    ),
  },
  retrieve: {
    label: "Retrieve",
    desc: "Vector search in Qdrant",
    color: "violet",
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.8}
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
        />
      </svg>
    ),
  },
  grade_docs: {
    label: "Grade Docs",
    desc: "Relevance filtering",
    color: "amber",
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.8}
          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    ),
  },
  rewrite_query: {
    label: "Rewrite Query",
    desc: "Query reformulation",
    color: "rose",
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.8}
          d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
        />
      </svg>
    ),
  },
  generate: {
    label: "Generate",
    desc: "Answer synthesis",
    color: "emerald",
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.8}
          d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"
        />
      </svg>
    ),
  },
};

const COLOR_MAP = {
  blue: { ring: "ring-blue-500/40", bg: "bg-blue-500/10", icon: "text-blue-400", bar: "bg-blue-500" },
  violet: { ring: "ring-violet-500/40", bg: "bg-violet-500/10", icon: "text-violet-400", bar: "bg-violet-500" },
  amber: { ring: "ring-amber-500/40", bg: "bg-amber-500/10", icon: "text-amber-400", bar: "bg-amber-500" },
  rose: { ring: "ring-rose-500/40", bg: "bg-rose-500/10", icon: "text-rose-400", bar: "bg-rose-500" },
  emerald: {
    ring: "ring-emerald-500/40",
    bg: "bg-emerald-500/10",
    icon: "text-emerald-400",
    bar: "bg-emerald-500",
  },
};

export default function ReasoningTrace({ result, loading }) {
  return (
    <div className="w-[45%] flex flex-col overflow-hidden bg-slate-950">
      <div className="px-5 py-4 border-b border-slate-800">
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Reasoning Trace</h2>
        <p className="text-xs text-slate-600 mt-0.5">Node execution path + latency</p>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {loading && (
          <div className="space-y-3">
            {["route_query", "retrieve", "grade_docs", "generate"].map((n) => (
              <div key={n} className="flex items-center gap-3 animate-pulse">
                <div className="w-8 h-8 rounded-lg bg-slate-800 shrink-0" />
                <div className="flex-1 space-y-1.5">
                  <div className="h-2.5 bg-slate-800 rounded w-1/2" />
                  <div className="h-2 bg-slate-800/60 rounded w-1/3" />
                </div>
              </div>
            ))}
          </div>
        )}

        {result && !loading && (
          <>
            <NodeSequence nodesFired={result.nodes_fired} latency={result.latency_ms} />
            {result.latency_ms?.total && (
              <LatencyBreakdown latency={result.latency_ms} nodesFired={result.nodes_fired} />
            )}
            <StatStrip result={result} />
          </>
        )}

        {!result && !loading && (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <div className="grid grid-cols-2 gap-2 mb-5 opacity-30">
              {Object.entries(NODE_META).map(([key, meta]) => (
                <div key={key} className="flex items-center gap-1.5 text-xs text-slate-500">
                  <div className="w-5 h-5 rounded bg-slate-800 flex items-center justify-center text-slate-600">
                    {meta.icon}
                  </div>
                  {meta.label}
                </div>
              ))}
            </div>
            <p className="text-xs text-slate-600">The agent trace will appear here</p>
          </div>
        )}
      </div>
    </div>
  );
}

function NodeSequence({ nodesFired, latency }) {
  if (!nodesFired?.length) return null;

  const counts = nodesFired.reduce((acc, nodeId) => ({ ...acc, [nodeId]: (acc[nodeId] || 0) + 1 }), {});

  return (
    <div>
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
        Execution Path · {nodesFired.length} steps
      </p>
      <div className="space-y-1">
        {nodesFired.map((nodeId, i) => {
          const meta = NODE_META[nodeId];
          if (!meta) return null;
          const colors = COLOR_MAP[meta.color];
          const nodeLatency = latency?.[nodeId];
          const isRetry = nodeId === "retrieve" && counts[nodeId] > 1;

          return (
            <div key={`${nodeId}-${i}`} className="relative">
              {i < nodesFired.length - 1 && <div className="absolute left-4 top-9 w-px h-1 bg-slate-700 z-0" />}

              <div className={`relative z-10 flex items-center gap-3 p-2.5 rounded-xl ring-1 ${colors.ring} ${colors.bg} transition-all`}>
                <div className={`w-8 h-8 rounded-lg bg-slate-950/60 flex items-center justify-center ${colors.icon} shrink-0`}>
                  {meta.icon}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-slate-200">{meta.label}</span>
                    {isRetry && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/30">
                        retry
                      </span>
                    )}
                    {nodeId === "rewrite_query" && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/30">
                        self-correction
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">{meta.desc}</p>
                </div>

                {nodeLatency != null && (
                  <span className="text-[11px] text-slate-500 shrink-0 font-mono">{nodeLatency}ms</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function LatencyBreakdown({ latency, nodesFired }) {
  const total = latency.total || 1;
  const fired = [...new Set(nodesFired)];
  const nodeLatencies = fired
    .filter((n) => latency[n] != null)
    .map((n) => ({ id: n, ms: latency[n], pct: (latency[n] / total) * 100 }));

  if (!nodeLatencies.length) return null;

  return (
    <div>
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
        Latency Breakdown · {total}ms total
      </p>
      <div className="space-y-2">
        {nodeLatencies.map(({ id, ms, pct }) => {
          const meta = NODE_META[id];
          const colors = meta ? COLOR_MAP[meta.color] : { bar: "bg-slate-700" };

          return (
            <div key={id} className="space-y-1">
              <div className="flex justify-between items-center">
                <span className="text-[11px] text-slate-400">{meta?.label || id}</span>
                <span className="text-[11px] font-mono text-slate-500">{ms}ms</span>
              </div>
              <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${colors.bar} transition-all duration-700`} style={{ width: `${Math.max(pct, 2)}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StatStrip({ result }) {
  const stats = [
    { label: "Route", value: result.route_decision },
    { label: "Retries", value: result.retry_count },
    { label: "Chunks", value: result.retrieved_chunks?.length ?? 0 },
    { label: "Relevant", value: result.retrieved_chunks?.filter((chunk) => chunk.relevant).length ?? 0 },
  ];

  return (
    <div className="grid grid-cols-2 gap-2">
      {stats.map(({ label, value }) => (
        <div key={label} className="bg-slate-900 border border-slate-800 rounded-xl p-3">
          <p className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</p>
          <p className="text-sm font-semibold text-slate-200 mt-0.5">{String(value)}</p>
        </div>
      ))}
    </div>
  );
}
