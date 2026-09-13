import React from "react";
import { useWorkspaceStore } from "@/shared/store/useWorkspaceStore";
import { Bookmark } from "lucide-react";

interface CitationPillProps {
  pageNumber: number;
  bbox?: number[];
  sourceName?: string;
  refId?: string;
}

export const CitationPill: React.FC<CitationPillProps> = ({
  pageNumber,
  bbox,
  sourceName,
}) => {
  const jumpToPage = useWorkspaceStore((state) => state.jumpToPage);

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    jumpToPage(pageNumber, bbox || null);
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className="inline-flex items-center gap-1 px-2 py-0.5 my-0.5 text-xs font-semibold rounded-md bg-primary/10 text-primary hover:bg-primary/25 border border-primary/25 transition-all cursor-pointer shadow-xs active:scale-95"
      title={`Jump to Page ${pageNumber}${sourceName ? ` - ${sourceName}` : ""}${bbox ? " (Highlight citation area)" : ""}`}
    >
      <Bookmark className="w-3 h-3 shrink-0" />
      <span>Page {pageNumber}</span>
      {sourceName && (
        <span className="text-[10px] opacity-75 font-normal truncate max-w-[120px]">
          ({sourceName})
        </span>
      )}
    </button>
  );
};
