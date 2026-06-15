import { useState } from "react";
import type { ConversationData } from "@/types";
import { createShare } from "@/services/api";

export function ShareModal({ conversation, onClose }: {
  conversation: ConversationData;
  onClose: () => void;
}) {
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  const generate = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await createShare(conversation);
      setUrl(res.view_url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create share link");
    } finally {
      setLoading(false);
    }
  };

  const copy = async () => {
    if (!url) return;
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4"
         onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="bg-dark-800 border border-dark-600 rounded-xl p-6 w-full max-w-md">
        <h3 className="text-lg font-bold text-white mb-2">Share this conversation</h3>
        <p className="text-xs text-gray-400 mb-5">
          Creates a public pretty-view page at convertmy.chat/v/… — anyone with the link can view it.
        </p>

        {!url ? (
          <>
            {error && <p className="text-red-400 text-xs mb-3">{error}</p>}
            <div className="flex gap-3">
              <button onClick={generate} disabled={loading}
                className="flex-1 py-2.5 bg-ember hover:bg-ember-hover text-white rounded-lg font-semibold text-sm transition-colors disabled:opacity-50">
                {loading ? "Creating…" : "Create share link"}
              </button>
              <button onClick={onClose}
                className="px-4 py-2.5 bg-dark-700 border border-dark-600 text-gray-300 rounded-lg text-sm hover:text-white transition-colors">
                Cancel
              </button>
            </div>
          </>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center gap-2 bg-dark-700 border border-dark-600 rounded-lg px-3 py-2">
              <span className="flex-1 text-xs text-gray-200 truncate">{url}</span>
              <button onClick={copy}
                className="text-xs text-ember hover:text-white transition-colors shrink-0">
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
            <div className="flex gap-3">
              <a href={url} target="_blank" rel="noopener noreferrer"
                className="flex-1 text-center py-2 bg-dark-700 border border-dark-600 text-gray-300 rounded-lg text-sm hover:text-white transition-colors">
                Open link
              </a>
              <button onClick={onClose}
                className="flex-1 py-2 bg-ember hover:bg-ember-hover text-white rounded-lg text-sm transition-colors">
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
