import type { ExportFormat } from "@/types";
import { FORMAT_LABELS, FORMAT_ICONS } from "@/types";

const FMTS: ExportFormat[] = ["pdf", "docx", "csv", "markdown"];

export function FormatPicker({ selected, onSelect, disabled }: {
  selected: ExportFormat; onSelect: (f: ExportFormat) => void; disabled?: boolean;
}) {
  return (
    <div className="flex flex-wrap gap-3 justify-center">
      {FMTS.map((f) => (
        <button key={f} onClick={() => onSelect(f)} disabled={disabled}
          className={`flex items-center gap-2 px-5 py-3 rounded-lg font-medium text-sm border transition-all disabled:opacity-50
            ${selected === f ? "bg-ember/20 border-ember text-ember" : "bg-dark-700 border-dark-600 text-gray-300 hover:border-gray-500 hover:text-white"}`}>
          <span className="text-lg">{FORMAT_ICONS[f]}</span>{FORMAT_LABELS[f]}
        </button>
      ))}
    </div>
  );
}
