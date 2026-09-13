import React, { useState, useEffect } from "react";
import { useWorkspaceStore } from "@/shared/store/useWorkspaceStore";
import { documentsApi } from "@/api";
import { Sparkles, Loader2, X, RefreshCw, AlertCircle } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface PageDescriptionPanelProps {
  isOpen: boolean;
  onClose: () => void;
  docId: string;
}

export const PageDescriptionPanel: React.FC<PageDescriptionPanelProps> = ({
  isOpen,
  onClose,
  docId,
}) => {
  const activePage = useWorkspaceStore((state) => state.activePage);

  const [description, setDescription] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Cache descriptions by page
  const [cache, setCache] = useState<Record<number, string>>({});

  const fetchDescription = async (force: boolean = false) => {
    if (!force && cache[activePage]) {
      setDescription(cache[activePage]);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const res = await documentsApi.getPageDescription(docId, activePage);
      setDescription(res.description);
      setCache((prev) => ({ ...prev, [activePage]: res.description }));
    } catch (err: any) {
      setError(err.message || "Failed to generate page description.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchDescription();
    }
  }, [isOpen, activePage, docId]);

  if (!isOpen) return null;

  return (
    <div className="border-t border-border bg-card text-card-foreground shadow-lg flex flex-col max-h-72 transition-all">
      {/* Panel Header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-muted/40 border-b border-border">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-amber-500" />
          <h4 className="text-xs font-bold uppercase tracking-wider text-foreground">
            Page {activePage} AI Description (Vision Analysis)
          </h4>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => fetchDescription(true)}
            disabled={isLoading}
            className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            title="Regenerate page description"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
          </button>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            title="Close panel"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Panel Content */}
      <div className="p-4 overflow-y-auto text-sm leading-relaxed space-y-2">
        {isLoading ? (
          <div className="py-8 flex flex-col items-center justify-center gap-2 text-muted-foreground">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
            <p className="text-xs font-medium">Vision LLM is analyzing text, charts, and tables on page {activePage}...</p>
          </div>
        ) : error ? (
          <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-xs flex items-center gap-2 border border-destructive/20">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : description ? (
          <div className="prose dark:prose-invert prose-xs max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {description}
            </ReactMarkdown>
          </div>
        ) : (
          <div className="py-6 text-center text-xs text-muted-foreground">
            Click regenerate to analyze page content.
          </div>
        )}
      </div>
    </div>
  );
};
