import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { LinkInput } from "@/components/LinkInput";
import { FormatPicker } from "@/components/FormatPicker";
import { Preview } from "@/components/Preview";
import { SignInButton } from "@/components/SignInButton";
import { HistoryView } from "@/components/HistoryView";
import { AdminPanel } from "@/components/AdminPanel";
import { EmbeddedContentToggle } from "@/components/EmbeddedContentToggle";
import { useExport } from "@/hooks/useExport";
import { googleCallback } from "@/services/api";
import type { ExportFormat, AppView } from "@/types";

export default function App() {
  const { user, setAuth } = useAuth();
  const {
    status, error, conversation, cached,
    embeddedContent, contentSummary,
    extract, exportAs, exportAsBundle, reset,
  } = useExport();
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>("pdf");
  const [view, setView] = useState<AppView>("home");

  // Bundle toggles
  const [includeTables, setIncludeTables] = useState(true);
  const [includeJson, setIncludeJson] = useState(true);
  const [includeCode, setIncludeCode] = useState(true);

  // Handle Google OAuth callback
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    if (code) {
      googleCallback(code, window.location.origin + "/auth/callback")
        .then((res) => setAuth(res.access_token, res.user))
        .catch(() => {})
        .finally(() => window.history.replaceState({}, "", "/"));
    }
  }, [setAuth]);

  const isExtracting = status === "extracting";
  const isExporting = status === "exporting";
  const hasConvo = status === "extracted" || status === "done";
  const hasEmbedded = contentSummary.total > 0;
  const anyEmbeddedEnabled = (includeTables && contentSummary.tables > 0)
    || (includeJson && contentSummary.json > 0)
    || (includeCode && contentSummary.code > 0);

  const handleExport = () => {
    if (anyEmbeddedEnabled) {
      exportAsBundle(selectedFormat, includeTables, includeJson, includeCode);
    } else {
      exportAs(selectedFormat);
    }
  };

  return (
    <div className="min-h-screen bg-dark-900 flex flex-col">
      <header className="border-b border-dark-700 px-6 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => { setView("home"); reset(); }} className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-ember flex items-center justify-center">
                <span className="text-white font-bold text-sm">C</span>
              </div>
              <h1 className="text-xl font-bold text-white tracking-tight">
                ConvertMy<span className="text-ember">.chat</span>
              </h1>
            </button>
            {user && (
              <nav className="flex gap-1 ml-6">
                {(["home", "history", ...(user.is_admin ? ["admin"] : [])] as AppView[]).map((v) => (
                  <button key={v} onClick={() => setView(v)}
                    className={`text-xs px-3 py-1.5 rounded-lg transition-colors capitalize
                      ${view === v ? "bg-dark-700 text-white" : "text-gray-500 hover:text-gray-300"}`}>
                    {v}
                  </button>
                ))}
              </nav>
            )}
          </div>
          <SignInButton />
        </div>
      </header>

      <main className="flex-1 px-6 py-10">
        <div className="max-w-4xl mx-auto space-y-8">
          {view === "home" && (
            <>
              <div className="text-center space-y-2">
                <h2 className="text-3xl sm:text-4xl font-bold text-white">Export any shared AI chat</h2>
                <p className="text-gray-400 max-w-lg mx-auto text-sm">
                  Paste a Gemini or ChatGPT share link and download as PDF, Word, CSV, or Markdown.
                  Tables, JSON, and code blocks are automatically detected and exportable as separate files.
                  {!user && <span className="text-gray-500"> Sign in to save your export history.</span>}
                </p>
              </div>

              <LinkInput onSubmit={extract} disabled={isExtracting || isExporting} />

              {isExtracting && (
                <div className="text-center">
                  <div className="inline-flex items-center gap-3 px-5 py-3 bg-dark-800 rounded-lg border border-dark-600">
                    <div className="w-4 h-4 border-2 border-ember border-t-transparent rounded-full animate-spin" />
                    <span className="text-sm text-gray-300">Rendering the share page... ~10-20 seconds</span>
                  </div>
                </div>
              )}

              {error && (
                <div className="text-center">
                  <div className="inline-flex flex-col gap-2 px-5 py-3 bg-red-950/30 rounded-lg border border-red-800/50">
                    <p className="text-sm text-red-400">{error}</p>
                    <button onClick={reset} className="text-xs text-gray-400 hover:text-white underline">Try again</button>
                  </div>
                </div>
              )}

              {hasConvo && conversation && (
                <>
                  <Preview conversation={conversation} cached={cached} />

                  {/* Embedded content detection */}
                  {hasEmbedded && (
                    <EmbeddedContentToggle
                      summary={contentSummary}
                      items={embeddedContent}
                      includeTables={includeTables}
                      includeJson={includeJson}
                      includeCode={includeCode}
                      onToggleTables={setIncludeTables}
                      onToggleJson={setIncludeJson}
                      onToggleCode={setIncludeCode}
                    />
                  )}

                  <div className="space-y-4">
                    <p className="text-center text-sm text-gray-400">Choose an export format</p>
                    <FormatPicker selected={selectedFormat} onSelect={setSelectedFormat} disabled={isExporting} />
                  </div>

                  <div className="text-center space-y-3">
                    <button onClick={handleExport} disabled={isExporting}
                      className="px-8 py-3 bg-ember hover:bg-ember-hover text-white font-bold rounded-lg text-lg transition-colors disabled:opacity-50">
                      {isExporting ? (
                        <span className="flex items-center gap-2">
                          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                          Generating...
                        </span>
                      ) : anyEmbeddedEnabled
                        ? `Download bundle (.zip)`
                        : `Download as ${selectedFormat.toUpperCase()}`
                      }
                    </button>

                    {anyEmbeddedEnabled && (
                      <p className="text-xs text-gray-500">
                        ZIP includes {selectedFormat.toUpperCase()} + {contentSummary.total} embedded file{contentSummary.total !== 1 ? "s" : ""}
                      </p>
                    )}

                    {status === "done" && (
                      <p className="text-sm text-green-400">
                        Download started!{user && " Saved to your history."}
                      </p>
                    )}

                    <button onClick={reset} className="block mx-auto text-xs text-gray-500 hover:text-gray-300">
                      Extract a different conversation
                    </button>
                  </div>
                </>
              )}
            </>
          )}

          {view === "history" && user && <HistoryView />}
          {view === "admin" && user?.is_admin && <AdminPanel />}
        </div>
      </main>

      <footer className="border-t border-dark-700 px-6 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between text-xs text-gray-600">
          <span>ConvertMyChat v0.1.0</span>
          <span>Built with <span className="text-ember">FastAPI</span> + <span className="text-ember">React</span></span>
        </div>
      </footer>
    </div>
  );
}
