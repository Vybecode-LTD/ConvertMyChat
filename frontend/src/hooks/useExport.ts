import { useState, useCallback } from "react";
import type { ConversationData, ExportFormat, AppStatus, EmbeddedContentItem, ContentSummary } from "@/types";
import { extractConversationV2, exportConversation, exportBundle, downloadBlob } from "@/services/api";

export function useExport() {
  const [status, setStatus] = useState<AppStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [conversation, setConversation] = useState<ConversationData | null>(null);
  const [cached, setCached] = useState(false);
  const [embeddedContent, setEmbeddedContent] = useState<EmbeddedContentItem[]>([]);
  const [contentSummary, setContentSummary] = useState<ContentSummary>({ tables: 0, json: 0, code: 0, total: 0 });

  const extract = useCallback(async (url: string) => {
    setStatus("extracting"); setError(null);
    try {
      const r = await extractConversationV2(url);
      if (r.success && r.conversation) {
        setConversation(r.conversation);
        setCached(r.cached);
        setEmbeddedContent(r.embedded_content);
        setContentSummary(r.content_summary);
        setStatus("extracted");
      } else {
        setError(r.error || "Failed"); setStatus("error");
      }
    } catch (e) { setError(e instanceof Error ? e.message : "Error"); setStatus("error"); }
  }, []);

  const exportAs = useCallback(async (format: ExportFormat) => {
    if (!conversation) return;
    setStatus("exporting"); setError(null);
    try {
      const { blob, filename } = await exportConversation(conversation, format);
      downloadBlob(blob, filename);
      setStatus("done");
    } catch (e) { setError(e instanceof Error ? e.message : "Error"); setStatus("error"); }
  }, [conversation]);

  const exportAsBundle = useCallback(async (
    format: ExportFormat,
    includeTables: boolean,
    includeJson: boolean,
    includeCode: boolean,
  ) => {
    if (!conversation) return;
    setStatus("exporting"); setError(null);
    try {
      const { blob, filename } = await exportBundle(
        conversation, format, includeTables, includeJson, includeCode,
      );
      downloadBlob(blob, filename);
      setStatus("done");
    } catch (e) { setError(e instanceof Error ? e.message : "Error"); setStatus("error"); }
  }, [conversation]);

  const reset = useCallback(() => {
    setStatus("idle"); setError(null); setConversation(null);
    setCached(false); setEmbeddedContent([]); setContentSummary({ tables: 0, json: 0, code: 0, total: 0 });
  }, []);

  return {
    status, error, conversation, cached,
    embeddedContent, contentSummary,
    extract, exportAs, exportAsBundle, reset,
  };
}
