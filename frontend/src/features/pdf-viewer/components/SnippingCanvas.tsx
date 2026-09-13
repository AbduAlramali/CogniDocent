import React, { useState, useRef, useEffect, useCallback } from "react";
import { useWorkspaceStore } from "@/shared/store/useWorkspaceStore";
import { Crop } from "lucide-react";

interface SnippingCanvasProps {
  pageContainerRef: React.RefObject<HTMLDivElement>;
}

interface Rect {
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
}

export const SnippingCanvas: React.FC<SnippingCanvasProps> = ({
  pageContainerRef,
}) => {
  const snippingMode = useWorkspaceStore((state) => state.snippingMode);
  const setSnippingMode = useWorkspaceStore((state) => state.setSnippingMode);
  const addPendingSnippet = useWorkspaceStore((state) => state.addPendingSnippet);
  const activePage = useWorkspaceStore((state) => state.activePage);

  const [isDrawing, setIsDrawing] = useState(false);
  const [rect, setRect] = useState<Rect | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  // Handle Escape key to cancel snipping mode
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && snippingMode) {
        setSnippingMode(false);
        setRect(null);
        setIsDrawing(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [snippingMode, setSnippingMode]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (!overlayRef.current) return;
    const bounds = overlayRef.current.getBoundingClientRect();
    const x = e.clientX - bounds.left;
    const y = e.clientY - bounds.top;

    setIsDrawing(true);
    setRect({
      startX: x,
      startY: y,
      currentX: x,
      currentY: y,
    });
  }, []);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDrawing || !rect || !overlayRef.current) return;
      const bounds = overlayRef.current.getBoundingClientRect();
      const x = Math.max(0, Math.min(e.clientX - bounds.left, bounds.width));
      const y = Math.max(0, Math.min(e.clientY - bounds.top, bounds.height));

      setRect((prev) => (prev ? { ...prev, currentX: x, currentY: y } : null));
    },
    [isDrawing, rect]
  );

  const handleMouseUp = useCallback(() => {
    if (!isDrawing || !rect || !pageContainerRef.current) {
      setIsDrawing(false);
      setRect(null);
      return;
    }

    const x = Math.min(rect.startX, rect.currentX);
    const y = Math.min(rect.startY, rect.currentY);
    const width = Math.abs(rect.currentX - rect.startX);
    const height = Math.abs(rect.currentY - rect.startY);

    // Ensure user selected a meaningful area (at least 15x15 px)
    if (width > 15 && height > 15) {
      // Find the react-pdf page canvas element
      const pdfCanvas = pageContainerRef.current.querySelector(
        "canvas"
      ) as HTMLCanvasElement | null;

      if (pdfCanvas) {
        const overlayBounds = overlayRef.current?.getBoundingClientRect();
        const canvasBounds = pdfCanvas.getBoundingClientRect();

        if (overlayBounds) {
          // Compute scale ratio between CSS displayed dimensions and real canvas resolution
          const scaleX = pdfCanvas.width / canvasBounds.width;
          const scaleY = pdfCanvas.height / canvasBounds.height;

          // Compute crop coordinates relative to canvas
          const cropX = (x + (overlayBounds.left - canvasBounds.left)) * scaleX;
          const cropY = (y + (overlayBounds.top - canvasBounds.top)) * scaleY;
          const cropWidth = width * scaleX;
          const cropHeight = height * scaleY;

          // Create offscreen canvas for the crop
          const cropCanvas = document.createElement("canvas");
          cropCanvas.width = Math.max(1, cropWidth);
          cropCanvas.height = Math.max(1, cropHeight);
          const ctx = cropCanvas.getContext("2d");

          if (ctx) {
            ctx.drawImage(
              pdfCanvas,
              Math.max(0, cropX),
              Math.max(0, cropY),
              cropWidth,
              cropHeight,
              0,
              0,
              cropWidth,
              cropHeight
            );

            cropCanvas.toBlob((blob) => {
              if (blob) {
                const previewUrl = URL.createObjectURL(blob);
                addPendingSnippet({
                  id: crypto.randomUUID(),
                  blob,
                  previewUrl,
                  filename: `Page_${activePage}_Clip.png`,
                  pageNum: activePage,
                });
              }
            }, "image/png");
          }
        }
      }
    }

    setIsDrawing(false);
    setRect(null);
    setSnippingMode(false);
  }, [isDrawing, rect, pageContainerRef, activePage, addPendingSnippet, setSnippingMode]);

  if (!snippingMode) return null;

  const left = rect ? Math.min(rect.startX, rect.currentX) : 0;
  const top = rect ? Math.min(rect.startY, rect.currentY) : 0;
  const width = rect ? Math.abs(rect.currentX - rect.startX) : 0;
  const height = rect ? Math.abs(rect.currentY - rect.startY) : 0;

  return (
    <div
      ref={overlayRef}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      className="absolute inset-0 z-30 cursor-crosshair bg-black/20 select-none overflow-hidden"
    >
      {/* Instructions Banner */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 px-4 py-2 rounded-full bg-background/95 text-foreground text-xs font-semibold shadow-xl border border-border flex items-center gap-2 pointer-events-none">
        <Crop className="w-3.5 h-3.5 text-primary" />
        <span>Click and drag a box to clip screenshot. Press Esc to cancel.</span>
      </div>

      {/* Marquee Selection Box */}
      {rect && width > 0 && height > 0 && (
        <div
          className="absolute border-2 border-primary bg-primary/20 shadow-lg rounded-sm pointer-events-none"
          style={{ left, top, width, height }}
        >
          <div className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/70 text-[10px] text-white font-mono">
            {Math.round(width)} × {Math.round(height)}
          </div>
        </div>
      )}
    </div>
  );
};
