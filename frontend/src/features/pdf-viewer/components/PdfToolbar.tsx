import React, { useState } from "react";
import { useWorkspaceStore } from "@/shared/store/useWorkspaceStore";
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Crop,
  Sparkles,
  RotateCw,
} from "lucide-react";

interface PdfToolbarProps {
  rotation?: number;
  onRotate: () => void;
  isDescriptionOpen: boolean;
  onToggleDescription: () => void;
}

export const PdfToolbar: React.FC<PdfToolbarProps> = ({
  onRotate,
  isDescriptionOpen,
  onToggleDescription,
}) => {
  const activePage = useWorkspaceStore((state) => state.activePage);
  const totalPages = useWorkspaceStore((state) => state.totalPages);
  const scale = useWorkspaceStore((state) => state.scale);
  const setScale = useWorkspaceStore((state) => state.setScale);
  const jumpToPage = useWorkspaceStore((state) => state.jumpToPage);
  const snippingMode = useWorkspaceStore((state) => state.snippingMode);
  const setSnippingMode = useWorkspaceStore((state) => state.setSnippingMode);

  const [pageInput, setPageInput] = useState(String(activePage));

  const handlePrevPage = () => {
    if (activePage > 1) {
      jumpToPage(activePage - 1);
      setPageInput(String(activePage - 1));
    }
  };

  const handleNextPage = () => {
    if (activePage < totalPages) {
      jumpToPage(activePage + 1);
      setPageInput(String(activePage + 1));
    }
  };

  const handlePageInputSubmit = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      const parsed = parseInt(pageInput, 10);
      if (!isNaN(parsed)) {
        jumpToPage(parsed);
      } else {
        setPageInput(String(activePage));
      }
    }
  };

  const handleZoomIn = () => setScale(scale + 0.15);
  const handleZoomOut = () => setScale(scale - 0.15);
  const handleResetZoom = () => setScale(1.0);

  return (
    <div className="flex flex-wrap items-center justify-between px-4 py-2.5 border-b border-border bg-card text-card-foreground select-none gap-2 z-10">
      {/* Page Navigation Controls */}
      <div className="flex items-center space-x-1 text-sm">
        <button
          type="button"
          onClick={handlePrevPage}
          disabled={activePage <= 1}
          className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground disabled:opacity-40 disabled:pointer-events-none transition-colors"
          title="Previous Page"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        <div className="flex items-center space-x-1.5 px-1">
          <input
            type="text"
            value={pageInput}
            onChange={(e) => setPageInput(e.target.value)}
            onKeyDown={handlePageInputSubmit}
            onBlur={() => setPageInput(String(activePage))}
            className="w-11 text-center font-medium border border-border rounded-lg py-1 text-xs bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
          <span className="text-xs text-muted-foreground">/ {totalPages}</span>
        </div>

        <button
          type="button"
          onClick={handleNextPage}
          disabled={activePage >= totalPages}
          className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground disabled:opacity-40 disabled:pointer-events-none transition-colors"
          title="Next Page"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Zoom and View Controls */}
      <div className="flex items-center space-x-1 text-sm">
        <button
          type="button"
          onClick={handleZoomOut}
          disabled={scale <= 0.4}
          className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground disabled:opacity-40 transition-colors"
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>

        <button
          type="button"
          onClick={handleResetZoom}
          className="px-2 py-1 text-xs font-mono font-medium rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors min-w-[50px] text-center"
          title="Reset Zoom"
        >
          {Math.round(scale * 100)}%
        </button>

        <button
          type="button"
          onClick={handleZoomIn}
          disabled={scale >= 2.5}
          className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground disabled:opacity-40 transition-colors"
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>

        <button
          type="button"
          onClick={onRotate}
          className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors ml-1"
          title="Rotate Page"
        >
          <RotateCw className="w-4 h-4" />
        </button>
      </div>

      {/* Tools: Snipping Tool & AI Page Description */}
      <div className="flex items-center space-x-2">
        <button
          type="button"
          onClick={() => setSnippingMode(!snippingMode)}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
            snippingMode
              ? "bg-primary text-primary-foreground shadow-sm animate-pulse ring-2 ring-primary/40"
              : "border border-border hover:bg-muted text-muted-foreground hover:text-foreground"
          }`}
          title="Clip screenshot from page to reference in chat"
        >
          <Crop className="w-3.5 h-3.5" />
          <span>{snippingMode ? "Snipping..." : "Snip to Chat"}</span>
        </button>

        <button
          type="button"
          onClick={onToggleDescription}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
            isDescriptionOpen
              ? "bg-primary/10 text-primary border border-primary/30"
              : "border border-border hover:bg-muted text-muted-foreground hover:text-foreground"
          }`}
          title="Show Vision AI page description"
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-500" />
          <span>Page AI Info</span>
        </button>
      </div>
    </div>
  );
};
