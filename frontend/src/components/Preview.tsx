import type { ConversationData } from "@/types";

export function Preview({ conversation, cached }: { conversation: ConversationData; cached: boolean }) {
  return (
    <div className="w-full max-w-2xl mx-auto bg-dark-800 rounded-xl border border-dark-600 overflow-hidden">
      <div className="px-5 py-4 border-b border-dark-600 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">{conversation.title}</h3>
          <p className="text-xs text-gray-500 mt-1 font-mono">
            {conversation.message_count} messages
            {cached && <span className="ml-2 text-amber-500">(cached)</span>}
          </p>
        </div>
        <div className="text-xs text-gray-600">{new Date(conversation.extracted_at).toLocaleDateString()}</div>
      </div>
      <div className="max-h-80 overflow-y-auto divide-y divide-dark-700">
        {conversation.messages.slice(0, 6).map((m, i) => (
          <div key={i} className="px-5 py-3">
            <span className={`text-xs font-semibold uppercase tracking-wider ${m.role === "user" ? "text-blue-400" : "text-ember"}`}>
              {m.role === "user" ? "You" : "Gemini"}
            </span>
            <p className="text-sm text-gray-300 line-clamp-3 mt-1 whitespace-pre-wrap">
              {m.content.slice(0, 300)}{m.content.length > 300 ? "..." : ""}
            </p>
          </div>
        ))}
        {conversation.messages.length > 6 && (
          <div className="px-5 py-3 text-center text-sm text-gray-500">+ {conversation.messages.length - 6} more</div>
        )}
      </div>
    </div>
  );
}
