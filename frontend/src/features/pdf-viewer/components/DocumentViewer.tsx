import React, { useState, useRef } from "react";
import { Document, Page } from "react-pdf";
import "../pdfConfig";
import "react-pdf/dist/esm/Page/TextLayer.css";
import "react-pdf/dist/esm/Page/AnnotationLayer.css";

import { useWorkspaceStore } from "@/shared/store/useWorkspaceStore";
import { PdfToolbar } from "./PdfToolbar";
import { SnippingCanvas } from "./SnippingCanvas";
import { TextSelectionPopup } from "./TextSelectionPopup";
import { PageDescriptionPanel } from "./PageDescriptionPanel";
import { CitationOverlay } from "./CitationOverlay";
import { Loader2, FileX } from "lucide-react";

interface DocumentViewerProps {
  documentUrl: string;
  docId: string;
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  documentUrl,
  docId,
}) => {
  const activePage = useWorkspaceStore((state) => state.activePage);
  const totalPages = useWorkspaceStore((state) => state.totalPages);
  const setTotalPages = useWorkspaceStore((state) => state.setTotalPages);
  const scale = useWorkspaceStore((state) => state.scale);

  const [rotation, setRotation] = useState(0);
  const [isDescriptionOpen, setIsDescriptionOpen] = useState(false);
  const [pageSize, setPageSize] = useState({ width: 612, height: 792 });

  const pageContainerRef = useRef<HTMLDivElement>(null);

  const handleDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setTotalPages(numPages);
  };

  const handlePageLoadSuccess = (page: any) => {
    setPageSize({
      width: page.width * scale,
      height: page.height * scale,
    });
  };

  const handleRotate = () => {
    setRotation((prev) => (prev + 90) % 360);
  };

  return (
    <div className="flex flex-col h-full bg-muted/40 border-r border-border overflow-hidden">
      {/* Top Controls Toolbar */}
      <PdfToolbar
        rotation={rotation}
        onRotate={handleRotate}
        isDescriptionOpen={isDescriptionOpen}
        onToggleDescription={() => setIsDescriptionOpen((prev) => !prev)}
      />

      {/* Main PDF Scroll Viewport */}
      <div className="flex-1 overflow-auto p-6 flex justify-center items-start">
        <div
          ref={pageContainerRef}
          className="relative bg-card shadow-2xl rounded-lg border border-border transition-all duration-150 select-text"
        >
          <Document
            file={documentUrl}
            onLoadSuccess={handleDocumentLoadSuccess}
            loading={
              <div className="flex flex-col items-center justify-center p-20 gap-3 text-muted-foreground">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
                <span className="text-xs font-medium">Loading PDF document...</span>
              </div>
            }
            error={
              <div className="flex flex-col items-center justify-center p-16 gap-3 text-destructive">
                <FileX className="w-10 h-10" />
                <span className="text-sm font-semibold">Failed to load PDF</span>
                <span className="text-xs text-muted-foreground">
                  Check if document exists or try re-uploading.
                </span>
              </div>
            }
          >
            <Page
              pageNumber={Math.min(Math.max(1, activePage), totalPages)}
              scale={scale}
              rotate={rotation}
              onLoadSuccess={handlePageLoadSuccess}
              renderTextLayer={true}
              renderAnnotationLayer={false}
              className="rounded-lg overflow-hidden"
            />
          </Document>

          {/* Screenshot Snipping Marquee Canvas */}
          <SnippingCanvas pageContainerRef={pageContainerRef} />

          {/* Text Selection Floating Popup */}
          <TextSelectionPopup containerRef={pageContainerRef} />

          {/* Interactive Bounding Box Highlight from Citations */}
          <CitationOverlay
            pageWidth={pageSize.width}
            pageHeight={pageSize.height}
          />
        </div>
      </div>

      {/* Bottom Collapsible Page AI Description Drawer */}
      <PageDescriptionPanel
        isOpen={isDescriptionOpen}
        onClose={() => setIsDescriptionOpen(false)}
        docId={docId}
      />
    </div>
  );
};
