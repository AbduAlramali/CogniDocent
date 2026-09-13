import React, { useState, useEffect } from "react";
import { useWorkspaceStore } from "@/shared/store/useWorkspaceStore";
import { MessageSquareQuote, Copy, Check } from "lucide-react";

interface TextSelectionPopupProps {
  containerRef: React.RefObject<HTMLDivElement>;
}

export const TextSelectionPopup: React.FC<TextSelectionPopupProps> = ({
  containerRef,
}) => {
  const activePage = useWorkspaceStore((state) => state.activePage);
  const setQuoteToAppend = useWorkspaceStore((state) => state.setQuoteToAppend);

  const [position, setPosition] = useState<{ x: number; y: number } | null>(null);
  const [selectedText, setSelectedText] = useState("");
  const [hasCopied, setHasCopied] = useState(false);

  useEffect(() => {
    const handleMouseUp = () => {
      const selection = window.getSelection();
      if (!selection || selection.isCollapsed) {
        setPosition(null);
        setSelectedText("");
        return;
      }

      const text = selection.toString().trim();
      if (text.length < 3) {
        setPosition(null);
        return;
      }

      const range = selection.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      const containerRect = containerRef.current?.getBoundingClientRect();

      if (containerRect && rect) {
        setSelectedText(text);
        setPosition({
          x: rect.left + rect.width / 2 - containerRect.left,
          y: rect.top - containerRect.top - 44,
        });
      }
    };

    const container = containerRef.current;
    if (container) {
      container.addEventListener("mouseup", handleMouseUp);
    }
    return () => {
      if (container) {
        container.removeEventListener("mouseup", handleMouseUp);
      }
    };
  }, [containerRef]);

  const handleQuoteInChat = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!selectedText) return;

    const formattedQuote = `> "${selectedText}"\n*(Reference: Page ${activePage})*\n\n`;
    setQuoteToAppend(formattedQuote);

    // Clear selection and hide popup
    window.getSelection()?.removeAllRanges();
    setPosition(null);
  };

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(selectedText);
    setHasCopied(true);
    setTimeout(() => {
      setHasCopied(false);
      window.getSelection()?.removeAllRanges();
      setPosition(null);
    }, 800);
  };

  if (!position) return null;

  return (
    <div
      className="absolute z-40 -translate-x-1/2 flex items-center gap-1 p-1 bg-card text-card-foreground border border-border rounded-xl shadow-xl animate-in fade-in zoom-in-95 duration-150"
      style={{ left: position.x, top: Math.max(10, position.y) }}
    >
      <button
        type="button"
        onClick={handleQuoteInChat}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/95 transition-all shadow-sm"
      >
        <MessageSquareQuote className="w-3.5 h-3.5" />
        <span>Quote in Chat</span>
      </button>

      <button
        type="button"
        onClick={handleCopy}
        className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
        title="Copy to clipboard"
      >
        {hasCopied ? (
          <Check className="w-3.5 h-3.5 text-emerald-500" />
        ) : (
          <Copy className="w-3.5 h-3.5" />
        )}
      </button>
    </div>
  );
};
