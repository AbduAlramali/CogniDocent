import React, { useState, useRef, useEffect, useCallback } from "react";
import { useWorkspaceStore } from "@/shared/store/useWorkspaceStore";
import { chatsApi } from "@/api";
import { AttachmentTray, LocalFileAttachment } from "./AttachmentTray";
import { Send, Paperclip, Loader2 } from "lucide-react";

interface ChatInputBarProps {
  projectId: string;
  onSendMessage: (text: string, attachmentIds: string[]) => Promise<void>;
  onSendMessageError?: (err: unknown) => void;
  isSending: boolean;
}

export const ChatInputBar: React.FC<ChatInputBarProps> = ({
  projectId,
  onSendMessage,
  onSendMessageError,
  isSending,
}) => {
  const [input, setInput] = useState("");
  const [localAttachments, setLocalAttachments] = useState<LocalFileAttachment[]>([]);

  const pendingSnippets = useWorkspaceStore((state) => state.pendingSnippets);
  const clearPendingSnippets = useWorkspaceStore(
    (state) => state.clearPendingSnippets
  );
  const quoteToAppend = useWorkspaceStore((state) => state.quoteToAppend);
  const consumeQuoteToAppend = useWorkspaceStore(
    (state) => state.consumeQuoteToAppend
  );

  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Automatically insert quotes selected from PDF text
  useEffect(() => {
    if (quoteToAppend) {
      const quote = consumeQuoteToAppend();
      if (quote) {
        setInput((prev) => (prev ? `${prev}\n\n${quote}` : quote));
        textareaRef.current?.focus();
      }
    }
  }, [quoteToAppend, consumeQuoteToAppend]);

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        160,
        Math.max(42, textareaRef.current.scrollHeight)
      )}px`;
    }
  }, [input]);

  // Upload a single file or snippet immediately and track its state
  const uploadSingleAttachment = useCallback(
    async (attachment: LocalFileAttachment) => {
      try {
        const media = await chatsApi.uploadAttachment(
          projectId,
          attachment.file,
          attachment.fileName
        );
        setLocalAttachments((prev) =>
          prev.map((item) =>
            item.id === attachment.id
              ? {
                  ...item,
                  status: "ready",
                  mediaId: media.media_id,
                  error: undefined,
                }
              : item
          )
        );
      } catch (err: any) {
        const errMsg =
          err?.response?.data?.message ||
          err?.message ||
          "Failed to upload attachment";
        setLocalAttachments((prev) =>
          prev.map((item) =>
            item.id === attachment.id
              ? {
                  ...item,
                  status: "error",
                  error: errMsg,
                }
              : item
          )
        );
      }
    },
    [projectId]
  );

  // Ingest snipped screenshots from PDF viewer into local attachments and immediately upload
  useEffect(() => {
    if (pendingSnippets.length > 0) {
      const newSnippets: LocalFileAttachment[] = pendingSnippets.map((snippet) => ({
        id: snippet.id,
        file: snippet.blob,
        fileName: snippet.filename,
        contentType: "image/png",
        fileSizeBytes: snippet.blob.size,
        previewUrl: snippet.previewUrl,
        status: "uploading",
        isSnipped: true,
        pageNum: snippet.pageNum,
      }));

      setLocalAttachments((prev) => [...prev, ...newSnippets]);
      clearPendingSnippets();

      newSnippets.forEach((snippetItem) => {
        uploadSingleAttachment(snippetItem);
      });
    }
  }, [pendingSnippets, clearPendingSnippets, uploadSingleAttachment]);

  // File input change: immediately add with "uploading" status and start background upload
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;

    const filesArray = Array.from(e.target.files);
    const newItems: LocalFileAttachment[] = filesArray.map((f) => {
      const isImg = f.type.startsWith("image/");
      return {
        id: crypto.randomUUID(),
        file: f,
        fileName: f.name,
        contentType: f.type || "application/octet-stream",
        fileSizeBytes: f.size,
        previewUrl: isImg ? URL.createObjectURL(f) : undefined,
        status: "uploading",
      };
    });

    setLocalAttachments((prev) => [...prev, ...newItems]);
    e.target.value = "";

    newItems.forEach((item) => {
      uploadSingleAttachment(item);
    });
  };

  const handleRemoveAttachment = (id: string) => {
    setLocalAttachments((prev) => {
      const target = prev.find((item) => item.id === id);
      if (target?.previewUrl) URL.revokeObjectURL(target.previewUrl);
      return prev.filter((item) => item.id !== id);
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // State checks for disabling Send button
  const isAnyUploading = localAttachments.some(
    (item) => item.status === "uploading"
  );
  const readyAttachmentIds = localAttachments
    .filter((item) => item.status === "ready" && !!item.mediaId)
    .map((item) => item.mediaId!);

  const hasText = input.trim().length > 0;
  const hasReadyAttachments = readyAttachmentIds.length > 0;
  const isSendDisabled =
    isSending || isAnyUploading || (!hasText && !hasReadyAttachments);

  const handleSend = async () => {
    if (isSendDisabled) return;

    const trimmed = input.trim();
    const messageText =
      trimmed ||
      (hasReadyAttachments
        ? "Please analyze the attached image/document."
        : "");

    try {
      await onSendMessage(messageText, readyAttachmentIds);

      // Clean up after successful dispatch
      setInput("");
      localAttachments.forEach((item) => {
        if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
      });
      setLocalAttachments([]);
    } catch (err) {
      console.error("Failed to send message:", err);
      onSendMessageError?.(err);
    }
  };

  return (
    <div className="border-t border-border bg-card">
      {/* Attachment Tray for Snipped Screenshots and Local Files */}
      <AttachmentTray
        attachments={localAttachments}
        onRemoveAttachment={handleRemoveAttachment}
      />

      <div className="p-3 flex items-end gap-2">
        {/* Hidden File Input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*,.pdf,.txt,.docx,.csv,.json"
          onChange={handleFileSelect}
          className="hidden"
          disabled={isSending}
        />

        {/* Attachment Button */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={isSending}
          className="p-2.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors shrink-0 disabled:opacity-40 cursor-pointer"
          title="Attach files (images, PDF, documents)"
        >
          <Paperclip className="w-5 h-5" />
        </button>

        {/* Message Input Area */}
        <div className="flex-1 min-w-0 relative">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isAnyUploading
                ? "Uploading attachment..."
                : localAttachments.length > 0
                ? "Add a note or ask a question about the attachment..."
                : "Ask anything about this document... (Shift+Enter for new line)"
            }
            disabled={isSending}
            className="w-full resize-none px-3.5 py-2.5 text-sm bg-background text-foreground border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-all disabled:opacity-60 max-h-40"
          />
        </div>

        {/* Submit Button */}
        <button
          type="button"
          onClick={handleSend}
          disabled={isSendDisabled}
          className="p-2.5 rounded-xl bg-primary text-primary-foreground hover:bg-primary/95 disabled:opacity-40 disabled:pointer-events-none transition-all shrink-0 shadow-sm cursor-pointer"
          title={
            isAnyUploading
              ? "Please wait for attachments to finish uploading"
              : "Send message"
          }
        >
          {isSending || isAnyUploading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </button>
      </div>
    </div>
  );
};
