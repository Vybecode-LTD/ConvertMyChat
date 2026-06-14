import { useState, useEffect } from "react";
import type { HistoryItem, ExportFormat } from "@/types";
import { getHistory, deleteHistoryItem, reexportHistoryItem, downloadBlob } from "@/services/api";

export function HistoryView() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const res = await getHistory();
      setItems(res.items);
      setTotal(res.total);
    } catch { /* ignore */ }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleReexport = async (id: string, format: ExportFormat) => {
    try {
      const { blob, filename } = await reexportHistoryItem(id, format);
      downloadBlob(blob, filename);
    } catch { /* ignore */ }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this export from history?")) return;
    await deleteHistoryItem(id);
    load();
  };

  if (loading) return <p className="text-center text-gray-500 py-8">Loading history...</p>;
  if (items.length === 0) return <p className="text-center text-gray-500 py-8">No exports yet. Extract a conversation to get started.</p>;

  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-400">{total} saved export{total !== 1 ? "s" : ""}</p>
      {items.map((item) => (
        <div key={item.id} className="bg-dark-800 border border-dark-600 rounded-lg p-4 flex items-center justify-between gap-4">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{item.title}</p>
            <p className="text-xs text-gray-500 font-mono truncate">{item.share_url}</p>
            <p className="text-xs text-gray-600 mt-1">
              {item.message_count} msgs · {new Date(item.created_at).toLocaleDateString()}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {(["pdf", "docx", "csv", "markdown"] as ExportFormat[]).map((fmt) => (
              <button key={fmt} onClick={() => handleReexport(item.id, fmt)}
                className="text-xs px-2 py-1 bg-dark-700 border border-dark-600 rounded text-gray-400 hover:text-ember hover:border-ember transition-colors">
                {fmt === "markdown" ? "MD" : fmt.toUpperCase()}
              </button>
            ))}
            <button onClick={() => handleDelete(item.id)}
              className="text-xs px-2 py-1 text-red-400 hover:text-red-300 transition-colors">
              ✕
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
