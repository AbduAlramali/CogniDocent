import React from "react";
import { FileTypeIcon } from "./FileTypeIcon";
import { X, Crop, Loader2, AlertCircle } from "lucide-react";

export type AttachmentUploadStatus = "uploading" | "ready" | "error";

export interface LocalFileAttachment {
  id: string;
  file: File | Blob;
  fileName: string;
  contentType: string;
  fileSizeBytes: number;
  previewUrl?: string;
  status: AttachmentUploadStatus;
  mediaId?: string;
  error?: string;
  isSnipped?: boolean;
  pageNum?: number;
}

interface AttachmentTrayProps {
  attachments: LocalFileAttachment[];
  onRemoveAttachment: (id: string) => void;
}

export const AttachmentTray: React.FC<AttachmentTrayProps> = ({
  attachments,
  onRemoveAttachment,
}) => {
  if (attachments.length === 0) return null;

  return (
    <div className="px-4 py-2.5 bg-muted/40 border-t border-border flex items-center gap-2.5 overflow-x-auto select-none">
      {attachments.map((item) => {
        const isImage =
          !!item.previewUrl || item.contentType.startsWith("image/");
        const hasError = item.status === "error";
        const isUploading = item.status === "uploading";

        return (
          <div
            key={item.id}
            title={
              hasError
                ? `Upload Error: ${item.error || "Failed to upload file"}`
                : item.fileName
            }
            className={`relative flex items-center gap-2 pl-1.5 pr-2 py-1 rounded-xl bg-card shadow-xs group shrink-0 transition-all border ${
              hasError
                ? "border-red-500/80 bg-red-500/5 ring-1 ring-red-500/30"
                : item.isSnipped
                ? "border-primary/40"
                : "border-border"
            }`}
          >
            {/* Loading Spinner Overlay while uploading */}
            {isUploading && (
              <div
                className="absolute inset-0 bg-background/80 backdrop-blur-xs rounded-xl flex items-center justify-center z-10"
                title="Uploading attachment..."
              >
                <Loader2 className="w-4 h-4 animate-spin text-primary" />
              </div>
            )}

            {/* Red Error Icon Badge on top if upload failed */}
            {hasError && (
              <div
                className="absolute -top-1.5 -left-1.5 z-20"
                title={item.error || "Upload failed. Hover to view details."}
              >
                <span className="flex h-4 w-4 items-center justify-center rounded-full bg-red-600 text-white shadow-xs">
                  <AlertCircle className="w-3 h-3 text-white" />
                </span>
              </div>
            )}

            {/* Visual: Image itself or File Type Icon */}
            {isImage && item.previewUrl ? (
              <div className="relative w-9 h-9 rounded-lg overflow-hidden border border-border bg-muted shrink-0">
                <img
                  src={item.previewUrl}
                  alt={item.fileName}
                  className="w-full h-full object-cover"
                />
              </div>
            ) : (
              <div className="w-9 h-9 rounded-lg bg-muted border border-border text-muted-foreground flex items-center justify-center shrink-0">
                <FileTypeIcon
                  fileName={item.fileName}
                  contentType={item.contentType}
                  className="w-5 h-5"
                />
              </div>
            )}

            {/* Attachment Meta */}
            <div className="text-[11px] leading-tight">
              {item.isSnipped ? (
                <span className="font-semibold text-primary flex items-center gap-1">
                  <Crop className="w-3 h-3" />
                  Page {item.pageNum} Snip
                </span>
              ) : (
                <span className="font-medium text-foreground block truncate max-w-[110px]">
                  {item.fileName}
                </span>
              )}

              <span
                className={`text-[10px] block truncate max-w-[110px] ${
                  hasError ? "text-red-500 font-medium" : "text-muted-foreground"
                }`}
              >
                {hasError
                  ? item.error || "Upload failed"
                  : item.fileSizeBytes > 0
                  ? `${(item.fileSizeBytes / 1024).toFixed(0)} KB`
                  : item.fileName}
              </span>
            </div>

            {/* Remove Attachment Button */}
            <button
              type="button"
              onClick={() => onRemoveAttachment(item.id)}
              disabled={isUploading}
              className="p-1 rounded-md hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors ml-1 disabled:opacity-30 disabled:pointer-events-none"
              title="Remove attachment"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
};
