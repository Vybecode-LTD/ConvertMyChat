import { useEffect, useState } from "react";
import type { ConversationData } from "@/types";

const API = import.meta.env.VITE_API_URL || "";

interface ShareData {
  id: string;
  title: string;
  message_count: number;
  created_at: string;
  conversation: ConversationData;
}

function MessageBlock({ msg, aiLabel }: {
  msg: ConversationData["messages"][0];
  aiLabel: string;
}) {
  const isUser = msg.role === "user";
  return (
    <div className={`py-5 border-b border-dark-700 ${isUser ? "" : ""}`}>
      <div className={`text-xs uppercase tracking-widest font-semibold mb-2 ${isUser ? "text-blue-400" : "text-green-400"}`}>
        {isUser ? "You" : aiLabel}
      </div>
      <div className="text-gray-200 text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</div>
    </div>
  );
}

export function ShareView({ shareId }: { shareId: string }) {
  const [data, setData] = useState<ShareData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/share/${shareId}`)
      .then(async (res) => {
        if (!res.ok) throw new Error(res.status === 404 ? "This share link doesn't exist or has expired." : "Failed to load conversation.");
        return res.json();
      })
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [shareId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-dark-900 flex items-center justify-center">
        <div className="flex items-center gap-3 text-gray-400">
          <div className="w-5 h-5 border-2 border-ember border-t-transparent rounded-full animate-spin" />
          Loading conversation…
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-dark-900 flex items-center justify-center">
        <div className="text-center space-y-3">
          <p className="text-red-400">{error || "Not found"}</p>
          <a href="/" className="text-xs text-ember hover:underline">Go to ConvertMyChat</a>
        </div>
      </div>
    );
  }

  const convo = data.conversation;
  const platform = String(convo.metadata?.platform || "gemini");
  const aiLabel = platform === "chatgpt" ? "ChatGPT" : "Gemini";
  const summary = convo.metadata?.summary as string | undefined;
  const exportedDate = new Date(data.created_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });

  return (
    <div className="min-h-screen bg-dark-900 flex flex-col">
      <header className="border-b border-dark-700 px-6 py-3">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <a href="/" className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-md bg-ember flex items-center justify-center">
              <span className="text-white font-bold text-xs">C</span>
            </div>
            <span className="text-sm font-bold text-white">ConvertMy<span className="text-ember">.chat</span></span>
          </a>
          <a href="/"
            className="text-xs text-gray-400 hover:text-ember border border-dark-600 px-3 py-1.5 rounded-lg hover:border-ember transition-colors">
            Export your own
          </a>
        </div>
      </header>

      <main className="flex-1 px-6 py-8">
        <div className="max-w-3xl mx-auto">
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-white mb-2">{convo.title}</h1>
            <p className="text-xs text-gray-500">
              {data.message_count} messages &nbsp;·&nbsp; shared {exportedDate} &nbsp;·&nbsp;
              <a href={convo.share_url} target="_blank" rel="noopener noreferrer" className="text-ember hover:underline">
                Original {aiLabel} link
              </a>
            </p>
          </div>

          {summary && (
            <div className="mb-6 bg-dark-800 border border-dark-600 border-l-2 border-l-ember rounded-lg p-4">
              <div className="text-xs text-ember uppercase tracking-wider font-semibold mb-2">AI Summary</div>
              <p className="text-sm text-gray-300 leading-relaxed">{summary}</p>
            </div>
          )}

          <div>
            {convo.messages.map((msg, i) => (
              <MessageBlock key={i} msg={msg} aiLabel={aiLabel} />
            ))}
          </div>
        </div>
      </main>

      <footer className="border-t border-dark-700 px-6 py-3">
        <div className="max-w-3xl mx-auto text-center text-xs text-gray-600">
          Shared via <a href="/" className="text-ember hover:underline">ConvertMyChat</a>
        </div>
      </footer>
    </div>
  );
}
