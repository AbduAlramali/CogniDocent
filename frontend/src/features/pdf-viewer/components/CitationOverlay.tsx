import React, { useEffect } from "react";
import { useWorkspaceStore } from "@/shared/store/useWorkspaceStore";

interface CitationOverlayProps {
  pageWidth: number;
  pageHeight: number;
}

export const CitationOverlay: React.FC<CitationOverlayProps> = ({
  pageWidth,
  pageHeight,
}) => {
  const activeBbox = useWorkspaceStore((state) => state.activeBbox);
  const setActiveBbox = useWorkspaceStore((state) => state.setActiveBbox);

  useEffect(() => {
    if (activeBbox) {
      // Auto-clear highlight after 6 seconds
      const timer = setTimeout(() => {
        setActiveBbox(null);
      }, 6000);
      return () => clearTimeout(timer);
    }
  }, [activeBbox, setActiveBbox]);

  if (!activeBbox || activeBbox.length < 4) return null;

  const [ymin, xmin, ymax, xmax] = activeBbox;

  // Determine if coordinates are normalized [0..1]
  const isNormalized =
    ymin <= 1.0 && xmin <= 1.0 && ymax <= 1.0 && xmax <= 1.0;

  let left = 0;
  let top = 0;
  let width = 0;
  let height = 0;

  if (isNormalized) {
    left = xmin * pageWidth;
    top = ymin * pageHeight;
    width = (xmax - xmin) * pageWidth;
    height = (ymax - ymin) * pageHeight;
  } else {
    left = xmin;
    top = ymin;
    width = xmax - xmin;
    height = ymax - ymin;
  }

  return (
    <div
      className="absolute border-2 border-amber-500 bg-amber-400/25 rounded shadow-lg pointer-events-none z-20 animate-pulse"
      style={{
        left: `${left}px`,
        top: `${top}px`,
        width: `${width}px`,
        height: `${height}px`,
      }}
    >
      <span className="absolute -top-5 left-0 px-1.5 py-0.5 rounded bg-amber-500 text-white text-[10px] font-bold uppercase tracking-wider shadow">
        Cited Reference
      </span>
    </div>
  );
};
