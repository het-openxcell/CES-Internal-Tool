import { useEffect, useRef, useState } from "react";
import {
  FileText as DocIcon,
  Repeat as RepeatIcon,
  Search as SearchIcon,
  Send as SendIcon,
  Sparkles as SparkleIcon,
  Star as StarIcon,
} from "lucide-react";
import { useSearchParams } from "react-router";

import { apiClient, type NLQueryResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

type RecentQuery = {
  query: string;
  resultCount: number;
  timestamp: number;
};

const SUGGESTION_CHIPS = [
  "Stuck pipe events on ARC Resources last quarter",
  "All lost circulation in Montney wells > 3000m",
  "Back ream occurrences across Tourmaline wells in 2026",
  "Tight hole events between 1500–1700m intermediate section",
  "Average ROP per bit run on WCP Karr 8-19",
  "All rig repair downtime in Q1 2026",
];

const SAVED_QUERIES = [
  "Weekly stuck-pipe report",
  "Montney lost-circ tracking",
];

function formatTimeAgo(epoch: number): string {
  const diff = Date.now() - epoch;
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "Yesterday";
  return `${days}d ago`;
}

function loadRecentQueries(): RecentQuery[] {
  try {
    return JSON.parse(localStorage.getItem("ces-recent-queries") || "[]");
  } catch {
    return [];
  }
}

export default function QueryPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<NLQueryResponse | null>(null);
  const [recentQueries, setRecentQueries] = useState<RecentQuery[]>(loadRecentQueries);
  const abortRef = useRef<AbortController | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();

  const runQuery = async (q: string) => {
    const trimmed = q.trim();
    if (!trimmed) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.queryNL(trimmed, controller.signal);
      setResult(res);
      const entry: RecentQuery = {
        query: trimmed,
        resultCount: res.sources?.length ?? 0,
        timestamp: Date.now(),
      };
      setRecentQueries((prev) => {
        const updated = [entry, ...prev.filter((r) => r.query !== trimmed)].slice(0, 10);
        localStorage.setItem("ces-recent-queries", JSON.stringify(updated));
        return updated;
      });
    } catch (err: unknown) {
      if ((err as Error).name === "AbortError") return;
      setError("Query failed — check that Qdrant is running and try again");
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const q = searchParams.get("q");
    if (q) {
      setQuery(q);
      runQuery(q);
      setSearchParams({}, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main className="flex min-h-0 flex-1 overflow-hidden bg-white">
      {/* Sidebar */}
      <aside className="hidden lg:flex w-[272px] shrink-0 flex-col border-r border-gray-100 overflow-y-auto">
        <div className="p-5 space-y-6">
          <div>
            <h3 className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-3">Recent Queries</h3>
            <div className="space-y-0.5">
              {recentQueries.length === 0 && (
                <p className="text-[13px] text-gray-300 italic px-2.5">No queries yet</p>
              )}
              {recentQueries.map((rq) => (
                <button
                  key={rq.query}
                  type="button"
                  onClick={() => { setQuery(rq.query); runQuery(rq.query); }}
                  className="w-full text-left px-2.5 py-2 rounded-md hover:bg-gray-50 transition-colors group"
                >
                  <div className="text-[13px] font-medium text-gray-700 group-hover:text-gray-900 line-clamp-2">{rq.query}</div>
                  <div className="text-[11px] text-gray-400 mt-0.5">
                    {rq.resultCount} results · {formatTimeAgo(rq.timestamp)}
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-3">Saved</h3>
            <div className="space-y-0.5">
              {SAVED_QUERIES.map((label) => (
                <button
                  key={label}
                  type="button"
                  onClick={() => { setQuery(label); runQuery(label); }}
                  className="w-full flex items-center gap-2 text-left px-2.5 py-2 rounded-md hover:bg-gray-50 transition-colors text-[13px] text-gray-600 hover:text-gray-900"
                >
                  <RepeatIcon className="w-3.5 h-3.5 shrink-0 text-gray-400" />
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-[860px] px-10 py-8">
          {/* Header */}
          <div className="mb-6">
            <span className="text-[12px] font-bold uppercase tracking-wider text-ces-red">Cross-DDR Search</span>
            <div className="mt-1 flex items-center gap-3 flex-wrap">
              <h1 className="text-[26px] font-bold tracking-tight text-gray-950">Ask anything about your DDR archive</h1>
              <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2.5 py-0.5 text-[12px] font-medium text-ces-red">
                <SparkleIcon className="h-3 w-3" />
                Natural language
              </span>
            </div>
          </div>

          {/* Search bar */}
          <div className="mb-6 flex items-center gap-3">
            <div className="relative flex-1">
              <SearchIcon className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") runQuery(query); }}
                placeholder="Ask a question about your DDR data… e.g. all stuck pipe events on ARC Resources last quarter"
                className={cn(
                  "h-11 w-full rounded-lg border border-gray-200 bg-white pl-10 pr-4 text-[14px] text-gray-900 placeholder:text-gray-400",
                  "focus:border-ces-red focus:outline-none focus:ring-2 focus:ring-ces-red/20",
                )}
                aria-label="Natural language query"
              />
            </div>
            <button
              type="button"
              onClick={() => runQuery(query)}
              disabled={loading || !query.trim()}
              className={cn(
                "inline-flex h-11 items-center gap-2 rounded-lg px-5 text-[14px] font-semibold text-white transition-colors shrink-0",
                loading || !query.trim() ? "cursor-not-allowed bg-ces-red/50" : "bg-ces-red hover:bg-ces-red-dark",
              )}
            >
              {loading ? (
                <>
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Searching…
                </>
              ) : (
                <>
                  Search
                  <SendIcon className="h-4 w-4" />
                </>
              )}
            </button>
          </div>

          {/* Error */}
          {error && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-[14px] text-red-700">
              {error}
            </div>
          )}

          {/* Loading */}
          {loading && (
            <div className="flex flex-col items-center gap-3 py-16 text-center text-[14px] text-gray-400">
              <svg className="h-6 w-6 animate-spin text-ces-red" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Searching time logs and generating answer…
            </div>
          )}

          {/* Idle: suggestions + info cards */}
          {!result && !loading && (
            <>
              <div className="mb-8">
                <h3 className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-3">Try one of these</h3>
                <div className="flex flex-wrap gap-2">
                  {SUGGESTION_CHIPS.map((chip) => (
                    <button
                      key={chip}
                      type="button"
                      onClick={() => { setQuery(chip); runQuery(chip); }}
                      className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-3.5 py-1.5 text-[13px] text-gray-600 hover:border-ces-red/40 hover:bg-ces-red/5 hover:text-ces-red transition-colors"
                    >
                      <SparkleIcon className="h-3 w-3 text-ces-red/60" />
                      {chip}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="rounded-xl border border-gray-200 bg-white p-5">
                  <div className="flex items-center gap-2.5 mb-3">
                    <div className="h-8 w-8 rounded-lg bg-gray-100 grid place-items-center">
                      <DocIcon className="h-4 w-4 text-gray-500" />
                    </div>
                    <span className="text-[14px] font-semibold text-gray-900">Indexed corpus</span>
                  </div>
                  <p className="text-[13px] leading-relaxed text-gray-500">
                    <span className="font-semibold text-gray-700">487</span> DDR reports · <span className="font-semibold text-gray-700">11,294</span> occurrences across <span className="font-semibold text-gray-700">38</span> wells · last indexed 6 minutes ago.
                  </p>
                </div>

                <div className="rounded-xl border border-gray-200 bg-white p-5">
                  <div className="flex items-center gap-2.5 mb-3">
                    <div className="h-8 w-8 rounded-lg bg-red-50 grid place-items-center">
                      <StarIcon className="h-4 w-4 text-ces-red" />
                    </div>
                    <span className="text-[14px] font-semibold text-gray-900">Tips</span>
                  </div>
                  <ul className="space-y-1.5 text-[13px] text-gray-500">
                    <li>• Mention operator, well, or area to scope results</li>
                    <li>• Use time references like "last quarter", "Q1 2026", or "since March"</li>
                    <li>• Combine type + depth band ("tight hole 1500–1700m")</li>
                  </ul>
                </div>
              </div>
            </>
          )}

          {/* Answer */}
          {!loading && result && (
            <div className="space-y-6">
              <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <div className="mb-3 flex items-center gap-2">
                  <SparkleIcon className="h-4 w-4 text-ces-red" />
                  <span className="text-[12px] font-bold uppercase tracking-wider text-gray-500">Answer</span>
                </div>
                <p className="whitespace-pre-wrap text-[15px] leading-7 text-gray-800">{result.answer}</p>
              </div>
              <button
                type="button"
                onClick={() => { setQuery(""); setResult(null); }}
                className="text-[13px] font-semibold text-ces-red hover:underline"
              >
                ← Ask another question
              </button>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
