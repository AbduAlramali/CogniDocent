import React, { useState, useRef, useEffect } from "react";
import { useWorkspaceStore } from "@/shared/store/useWorkspaceStore";
import { chatsApi } from "@/api";
import { AttachmentTray, LocalFileAttachment } from "./AttachmentTray";
import { Send, Paperclip, Loader2 } from "lucide-react";

interface ChatInputBarProps {
  projectId: string;
  onSendMessage: (text: string, attachmentIds: string[]) => Promise<void>;
  isSending: boolean;
}

export const ChatInputBar: React.FC<ChatInputBarProps> = ({
  projectId,
  onSendMessage,
  isSending,
}) => {
  const [input, setInput] = useState("");
  const [localAttachments, setLocalAttachments] = useState<LocalFileAttachment[]>([]);
  const [isUploadingAttachments, setIsUploadingAttachments] = useState(false);

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

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const newFiles: LocalFileAttachment[] = Array.from(e.target.files).map((f) => {
      const isImg = f.type.startsWith("image/");
      return {
        id: crypto.randomUUID(),
        file: f,
        previewUrl: isImg ? URL.createObjectURL(f) : undefined,
      };
    });
    setLocalAttachments((prev) => [...prev, ...newFiles]);
    e.target.value = "";
  };

  const handleRemoveLocalAttachment = (id: string) => {
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

  const handleSend = async () => {
    const trimmed = input.trim();
    const hasAttachments = pendingSnippets.length > 0 || localAttachments.length > 0;

    if ((!trimmed && !hasAttachments) || isSending || isUploadingAttachments) return;

    setIsUploadingAttachments(true);
    const attachmentIds: string[] = [];

    try {
      // 1. Upload snipped screenshots from the PDF
      for (const snippet of pendingSnippets) {
        const media = await chatsApi.uploadAttachment(
          projectId,
          snippet.blob,
          snippet.filename
        );
        attachmentIds.push(media.media_id);
      }

      // 2. Upload local file attachments
      for (const item of localAttachments) {
        const media = await chatsApi.uploadAttachment(
          projectId,
          item.file,
          item.file.name
        );
        attachmentIds.push(media.media_id);
      }

      // 3. Dispatch message completion
      const messageText = trimmed || (attachmentIds.length > 0 ? "Please analyze the attached image/document." : "");
      await onSendMessage(messageText, attachmentIds);

      // 4. Cleanup
      setInput("");
      clearPendingSnippets();
      localAttachments.forEach((item) => {
        if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
      });
      setLocalAttachments([]);
    } catch (err) {
      console.error("Failed to send message:", err);
    } finally {
      setIsUploadingAttachments(false);
    }
  };

  const isBusy = isSending || isUploadingAttachments;

  return (
    <div className="border-t border-border bg-card">
      {/* Attachment Tray for Snipped Screenshots and Local Files */}
      <AttachmentTray
        localAttachments={localAttachments}
        onRemoveLocalAttachment={handleRemoveLocalAttachment}
      />

      <div className="p-3 flex items-end gap-2">
        {/* Hidden File Input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*,.pdf,.txt,.docx"
          onChange={handleFileSelect}
          className="hidden"
          disabled={isBusy}
        />

        {/* Attachment Button */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={isBusy}
          className="p-2.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors shrink-0 disabled:opacity-40"
          title="Upload file or image attachment"
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
              pendingSnippets.length > 0
                ? "Ask a question about the snipped screenshot..."
                : "Ask anything about this document... (Shift+Enter for new line)"
            }
            disabled={isBusy}
            className="w-full resize-none px-3.5 py-2.5 text-sm bg-background text-foreground border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-all disabled:opacity-60 max-h-40"
          />
        </div>

        {/* Submit Button */}
        <button
          type="button"
          onClick={handleSend}
          disabled={
            (!input.trim() &&
              pendingSnippets.length === 0 &&
              localAttachments.length === 0) ||
            isBusy
          }
          className="p-2.5 rounded-xl bg-primary text-primary-foreground hover:bg-primary/95 disabled:opacity-40 disabled:pointer-events-none transition-all shrink-0 shadow-sm"
          title="Send message"
        >
          {isBusy ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </button>
      </div>
    </div>
  );
};
