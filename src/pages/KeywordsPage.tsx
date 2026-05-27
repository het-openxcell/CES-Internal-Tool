import { useEffect, useState } from "react";
import { Plus as PlusIcon, X as XIcon } from "lucide-react";

import { apiClient } from "@/lib/api";
import { cn } from "@/lib/utils";

type KeywordRuleGroup = {
  type: string;
  patterns: string[];
};

function groupKeywords(raw: Record<string, string>): KeywordRuleGroup[] {
  const map = new Map<string, string[]>();
  for (const [pattern, type] of Object.entries(raw)) {
    if (!map.has(type)) map.set(type, []);
    map.get(type)!.push(pattern);
  }
  return Array.from(map.entries()).map(([type, patterns]) => ({ type, patterns }));
}

function flattenRules(groups: KeywordRuleGroup[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const g of groups) {
    for (const p of g.patterns) {
      if (p.trim()) out[p.trim()] = g.type;
    }
  }
  return out;
}

function LoadingSkeleton() {
  return (
    <div className="space-y-3">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="border border-gray-200 rounded-lg px-3 py-3 bg-white">
          <div className="flex gap-3 mb-2.5">
            <div className="h-5 w-20 bg-gray-100 rounded animate-pulse" />
            <div className="h-5 w-16 bg-gray-100 rounded animate-pulse" />
          </div>
          <div className="flex gap-2">
            {[...Array(5)].map((_, j) => (
              <div key={j} className={cn("h-6 bg-gray-100 rounded animate-pulse", j % 2 === 0 ? "w-20" : "w-14")} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function KeywordsPage() {
  const [groups, setGroups] = useState<KeywordRuleGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [newPatternInput, setNewPatternInput] = useState<Record<number, string>>({});

  useEffect(() => {
    apiClient.getKeywords().then((kw) => {
      setGroups(groupKeywords(kw));
      setLoading(false);
    });
  }, []);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const removePattern = (groupIdx: number, patternIdx: number) => {
    setGroups((prev) =>
      prev.map((g, i) =>
        i === groupIdx ? { ...g, patterns: g.patterns.filter((_, j) => j !== patternIdx) } : g,
      ),
    );
  };

  const addPattern = (groupIdx: number) => {
    const val = (newPatternInput[groupIdx] ?? "").trim();
    if (!val) return;
    setGroups((prev) =>
      prev.map((g, i) => (i === groupIdx ? { ...g, patterns: [...g.patterns, val] } : g)),
    );
    setNewPatternInput((prev) => ({ ...prev, [groupIdx]: "" }));
  };

  const saveGroup = async (groupIdx: number) => {
    setSaving(groups[groupIdx].type);
    try {
      const flat = flattenRules(groups);
      await apiClient.updateKeywords(flat);
      showToast(`Keyword rules updated — ${groups[groupIdx].type}`);
    } catch {
      showToast("Save failed");
    } finally {
      setSaving(null);
    }
  };

  return (
    <main className="flex-1 overflow-auto">
      <div className="px-8 py-6 max-w-[1500px] mx-auto">
        <div className="mb-5">
          <div className="text-[12px] uppercase tracking-wider font-semibold text-gray-500">Platform admin</div>
          <h1 className="text-[24px] font-bold tracking-tight text-gray-900">Keyword rules</h1>
          <p className="text-[14px] text-gray-500 mt-1">
            Supplement the LLM extractor. Updates apply to next extraction immediately — no deploy required.
          </p>
        </div>

        {loading ? (
          <LoadingSkeleton />
        ) : (
          <div className="space-y-3 relative">
            {groups.length === 0 && (
              <div className="text-[14px] text-gray-400 py-5 text-center border border-gray-200 rounded-lg bg-white">
                No keyword rules loaded
              </div>
            )}
            {groups.map((rule, gi) => (
              <div key={rule.type} className="border border-gray-200 rounded-lg px-3 py-2.5 bg-white">
                <div className="flex items-center gap-2 mb-2.5">
                  <span className="inline-flex items-center px-3 py-1 rounded text-[13px] font-semibold bg-gray-100 text-gray-700">
                    {rule.type}
                  </span>
                  <span className="text-[13px] text-gray-500">{rule.patterns.length} patterns</span>
                  <button
                    onClick={() => saveGroup(gi)}
                    disabled={saving === rule.type}
                    className="ml-auto text-[13.5px] text-[var(--ces-red,#C41E3A)] hover:underline disabled:opacity-50"
                  >
                    {saving === rule.type ? "Saving…" : "Save changes"}
                  </button>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {rule.patterns.map((p, pi) => (
                    <span
                      key={pi}
                      className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded font-mono text-[13px] bg-gray-50 border border-gray-200"
                    >
                      {p}
                      <button
                        onClick={() => removePattern(gi, pi)}
                        className="text-gray-400 hover:text-red-500 ml-0.5"
                      >
                        <XIcon size={10} />
                      </button>
                    </span>
                  ))}
                  <div className="inline-flex items-center gap-1">
                    <input
                      value={newPatternInput[gi] ?? ""}
                      onChange={(e) => setNewPatternInput((prev) => ({ ...prev, [gi]: e.target.value }))}
                      onKeyDown={(e) => e.key === "Enter" && addPattern(gi)}
                      placeholder="add pattern…"
                      className="h-7 px-2 text-[13px] font-mono border border-dashed border-gray-300 rounded focus:outline-none focus:border-gray-400 w-36"
                    />
                    <button
                      onClick={() => addPattern(gi)}
                      className="h-6 w-6 flex items-center justify-center rounded border border-dashed border-gray-700 text-gray-800 hover:text-gray-950 hover:border-gray-900"
                    >
                      <PlusIcon size={10} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {toast && (
        <div className="fixed bottom-6 right-6 z-50 bg-gray-900 text-white text-[13px] px-4 py-2.5 rounded-lg shadow-lg">
          {toast}
        </div>
      )}
    </main>
  );
}
