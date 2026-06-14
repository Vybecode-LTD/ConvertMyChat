import { useState } from "react";

const PAT = /^https?:\/\/(gemini\.google\.com\/share\/[a-zA-Z0-9]+|g\.co\/gemini\/share\/[a-zA-Z0-9]+|chatgpt\.com\/share\/[a-zA-Z0-9\-]+|chat\.openai\.com\/share\/[a-zA-Z0-9\-]+)/;

export function LinkInput({ onSubmit, disabled }: { onSubmit: (url: string) => void; disabled?: boolean }) {
  const [url, setUrl] = useState("");
  const [err, setErr] = useState("");

  const submit = () => {
    let u = url.trim();
    if (!u) { setErr("Paste a share link"); return; }
    if (!u.startsWith("http")) u = `https://${u}`;
    if (!PAT.test(u)) { setErr("Expected a Gemini or ChatGPT share link"); return; }
    setErr("");
    onSubmit(u);
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      <label htmlFor="share-link" className="block text-sm text-gray-400 mb-2">Gemini or ChatGPT share link</label>
      <div className="flex gap-3">
        <input id="share-link" type="url" value={url}
          onChange={(e) => { setUrl(e.target.value); setErr(""); }}
          onKeyDown={(e) => e.key === "Enter" && !disabled && submit()}
          disabled={disabled} placeholder="Paste a chatgpt.com/share/... or gemini.google.com/share/... link"
          className="flex-1 px-4 py-3 bg-dark-700 border border-dark-600 rounded-lg text-white font-mono text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-ember disabled:opacity-50 transition-all" />
        <button onClick={submit} disabled={disabled || !url.trim()}
          className="px-6 py-3 bg-ember hover:bg-ember-hover text-white font-semibold rounded-lg transition-colors disabled:opacity-50">
          Extract
        </button>
      </div>
      {err && <p className="mt-2 text-sm text-red-400">{err}</p>}
    </div>
  );
}
