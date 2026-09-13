import React from "react";
import { useWorkspaceStore } from "@/shared/store/useWorkspaceStore";
import { File, X, Crop } from "lucide-react";

export interface LocalFileAttachment {
  id: string;
  file: File;
  previewUrl?: string;
}

interface AttachmentTrayProps {
  localAttachments: LocalFileAttachment[];
  onRemoveLocalAttachment: (id: string) => void;
}

export const AttachmentTray: React.FC<AttachmentTrayProps> = ({
  localAttachments,
  onRemoveLocalAttachment,
}) => {
  const pendingSnippets = useWorkspaceStore((state) => state.pendingSnippets);
  const removePendingSnippet = useWorkspaceStore(
    (state) => state.removePendingSnippet
  );

  const totalAttachments = pendingSnippets.length + localAttachments.length;
  if (totalAttachments === 0) return null;

  return (
    <div className="px-4 py-2 bg-muted/40 border-t border-border flex items-center gap-2 overflow-x-auto select-none">
      {/* Clipped Screenshots from PDF */}
      {pendingSnippets.map((snippet) => (
        <div
          key={snippet.id}
          className="relative flex items-center gap-2 pl-1.5 pr-2 py-1 rounded-xl bg-card border border-primary/40 shadow-xs group shrink-0"
        >
          <div className="relative w-8 h-8 rounded-lg overflow-hidden border border-border bg-muted shrink-0">
            <img
              src={snippet.previewUrl}
              alt={snippet.filename}
              className="w-full h-full object-cover"
            />
          </div>
          <div className="text-[11px] leading-tight">
            <span className="font-semibold text-primary flex items-center gap-1">
              <Crop className="w-3 h-3" />
              Page {snippet.pageNum} Snip
            </span>
            <span className="text-[10px] text-muted-foreground block truncate max-w-[90px]">
              {snippet.filename}
            </span>
          </div>
          <button
            type="button"
            onClick={() => removePendingSnippet(snippet.id)}
            className="p-1 rounded-md hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors ml-1"
            title="Remove snipped image"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}

      {/* Uploaded Local Files */}
      {localAttachments.map((item) => (
        <div
          key={item.id}
          className="relative flex items-center gap-2 pl-1.5 pr-2 py-1 rounded-xl bg-card border border-border shadow-xs group shrink-0"
        >
          {item.previewUrl ? (
            <div className="w-8 h-8 rounded-lg overflow-hidden border border-border bg-muted shrink-0">
              <img
                src={item.previewUrl}
                alt={item.file.name}
                className="w-full h-full object-cover"
              />
            </div>
          ) : (
            <div className="w-8 h-8 rounded-lg bg-muted text-muted-foreground flex items-center justify-center shrink-0">
              <File className="w-4 h-4" />
            </div>
          )}
          <div className="text-[11px] leading-tight">
            <span className="font-medium text-foreground block truncate max-w-[100px]">
              {item.file.name}
            </span>
            <span className="text-[10px] text-muted-foreground">
              {(item.file.size / 1024).toFixed(0)} KB
            </span>
          </div>
          <button
            type="button"
            onClick={() => onRemoveLocalAttachment(item.id)}
            className="p-1 rounded-md hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors ml-1"
            title="Remove attachment"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
};
