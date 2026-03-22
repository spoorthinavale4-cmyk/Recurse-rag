import { useState } from "react";

export default function ChunkViewer({ chunks }) {
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState(null);

  const relevant = chunks.filter((chunk) => chunk.relevant);
  const irrelevant = chunks.filter((chunk) => !chunk.relevant);

  return (
    <div className="border border-slate-800 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 bg-slate-900 hover:bg-slate-800/80 transition-colors"
      >
        <div className="flex items-center gap-2">
          <svg className="w-3.5 h-3.5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
            />
          </svg>
          <span className="text-xs font-medium text-slate-400">{chunks.length} retrieved chunks</span>
          <span className="text-xs text-emerald-500">{relevant.length} relevant</span>
          {irrelevant.length > 0 && <span className="text-xs text-slate-600">{irrelevant.length} filtered</span>}
        </div>
        <svg
          className={`w-4 h-4 text-slate-500 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="divide-y divide-slate-800">
          {chunks.map((chunk, i) => (
            <div key={i} className={chunk.relevant ? "bg-slate-950" : "bg-slate-950/50 opacity-60"}>
              <button
                onClick={() => setExpanded(expanded === i ? null : i)}
                className="w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-slate-900/50 transition-colors"
              >
                <div className={`mt-0.5 w-1.5 h-1.5 rounded-full shrink-0 ${chunk.relevant ? "bg-emerald-500" : "bg-slate-600"}`} />

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[11px] font-medium text-slate-500 truncate">{chunk.source}</span>
                    <span className="text-[10px] text-slate-600">chunk {chunk.chunk_index}</span>
                    <span
                      className={`text-[10px] ml-auto font-mono ${
                        chunk.score > 0.8 ? "text-emerald-500" : chunk.score > 0.6 ? "text-amber-500" : "text-slate-500"
                      }`}
                    >
                      {chunk.score}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">{chunk.text}</p>
                </div>

                <svg
                  className={`w-3.5 h-3.5 text-slate-600 shrink-0 mt-0.5 transition-transform ${expanded === i ? "rotate-180" : ""}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {expanded === i && (
                <div className="px-4 pb-4 ml-4">
                  <div className="bg-slate-900 rounded-lg p-3 border border-slate-800">
                    <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">{chunk.text}</p>
                  </div>
                  <div className="flex items-center gap-3 mt-2">
                    <span
                      className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full border ${
                        chunk.relevant
                          ? "bg-emerald-950/50 border-emerald-800/50 text-emerald-400"
                          : "bg-slate-900 border-slate-700 text-slate-500"
                      }`}
                    >
                      {chunk.relevant ? "Relevant" : "Filtered"}
                    </span>
                    <span className="text-[10px] text-slate-600">Score: {chunk.score} · {chunk.source}</span>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
