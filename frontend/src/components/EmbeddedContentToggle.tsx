import type { ContentSummary, EmbeddedContentItem } from "@/types";

interface Props {
  summary: ContentSummary;
  items: EmbeddedContentItem[];
  includeTables: boolean;
  includeJson: boolean;
  includeCode: boolean;
  onToggleTables: (v: boolean) => void;
  onToggleJson: (v: boolean) => void;
  onToggleCode: (v: boolean) => void;
}

export function EmbeddedContentToggle({
  summary, items,
  includeTables, includeJson, includeCode,
  onToggleTables, onToggleJson, onToggleCode,
}: Props) {
  if (summary.total === 0) return null;

  const sections = [
    {
      type: "table" as const,
      label: "Tables",
      icon: "📊",
      count: summary.tables,
      enabled: includeTables,
      onToggle: onToggleTables,
      detail: items
        .filter((i) => i.content_type === "table")
        .map((i) => `${i.suggested_filename} (${i.row_count}×${i.column_count})`),
    },
    {
      type: "json" as const,
      label: "JSON blocks",
      icon: "🗂️",
      count: summary.json,
      enabled: includeJson,
      onToggle: onToggleJson,
      detail: items
        .filter((i) => i.content_type === "json")
        .map((i) => i.suggested_filename),
    },
    {
      type: "code" as const,
      label: "Code snippets",
      icon: "💻",
      count: summary.code,
      enabled: includeCode,
      onToggle: onToggleCode,
      detail: items
        .filter((i) => i.content_type === "code")
        .map((i) => `${i.suggested_filename} (${i.language})`),
    },
  ].filter((s) => s.count > 0);

  const includedCount = [
    includeTables && summary.tables,
    includeJson && summary.json,
    includeCode && summary.code,
  ].filter(Boolean).reduce((a: number, b) => a + (typeof b === "number" ? b : 0), 0);

  return (
    <div className="w-full max-w-2xl mx-auto bg-dark-800 rounded-xl border border-dark-600 overflow-hidden">
      <div className="px-5 py-3 border-b border-dark-600 flex items-center justify-between">
        <p className="text-sm font-medium text-white">
          Embedded content detected
        </p>
        <span className="text-xs text-gray-500">
          {includedCount} file{includedCount !== 1 ? "s" : ""} will be bundled
        </span>
      </div>

      <div className="divide-y divide-dark-700">
        {sections.map((s) => (
          <div key={s.type} className="px-5 py-3">
            <label className="flex items-center justify-between cursor-pointer group">
              <div className="flex items-center gap-3">
                <span className="text-lg">{s.icon}</span>
                <div>
                  <p className="text-sm text-white group-hover:text-ember transition-colors">
                    {s.count} {s.label}
                  </p>
                  <p className="text-xs text-gray-500">
                    {s.detail.slice(0, 3).join(", ")}
                    {s.detail.length > 3 ? ` +${s.detail.length - 3} more` : ""}
                  </p>
                </div>
              </div>
              <div className="relative">
                <input
                  type="checkbox"
                  checked={s.enabled}
                  onChange={(e) => s.onToggle(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-dark-600 peer-checked:bg-ember rounded-full
                                transition-colors cursor-pointer" />
                <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full
                                transition-transform peer-checked:translate-x-4" />
              </div>
            </label>
          </div>
        ))}
      </div>

      <div className="px-5 py-2 bg-dark-700/50 text-xs text-gray-500">
        Enabled items will be exported as separate files in a ZIP bundle alongside your main document.
      </div>
    </div>
  );
}
