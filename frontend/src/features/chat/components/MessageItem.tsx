import React, { useState, useRef } from "react";
import { MessageWithAttachments } from "@/types";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { CitationPill } from "./CitationPill";
import { ChatErrorBox } from "./ChatErrorBox";
import { FileTypeIcon } from "./FileTypeIcon";
import { ttsApi, chatsApi } from "@/api";
import { isLegacyErrorMessage } from "@/api/errors";
import {
  Bot,
  User,
  Volume2,
  VolumeX,
  Loader2,
  AlertCircle,
} from "lucide-react";

interface MessageItemProps {
  message: MessageWithAttachments;
  onCitationClick?: (page: number) => void;
  onRetry?: () => void;
}

export const MessageItem: React.FC<MessageItemProps> = ({
  message,
  onCitationClick,
  onRetry,
}) => {
  // If this message represents an error after sending, render the dedicated Red Error Box
  if (message.is_error || message.error_info || isLegacyErrorMessage(message.content)) {
    return <ChatErrorBox message={message} onRetry={onRetry} />;
  }

  const isUser = message.role === "user";
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [isLoadingAudio, setIsLoadingAudio] = useState(false);
  const [ttsError, setTtsError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const handleToggleTTS = async () => {
    if (isPlayingAudio && audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsPlayingAudio(false);
      return;
    }

    setIsLoadingAudio(true);
    setTtsError(null);
    try {
      const audioBlob = await ttsApi.synthesizeSpeech(message.content);
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audioRef.current = audio;

      audio.onended = () => {
        setIsPlayingAudio(false);
        URL.revokeObjectURL(audioUrl);
      };
      audio.onerror = () => {
        setIsPlayingAudio(false);
      };

      await audio.play();
      setIsPlayingAudio(true);
    } catch (err: any) {
      console.error("TTS synthesis error:", err);
      setTtsError(err.message || "TTS playback failed.");
      setTimeout(() => setTtsError(null), 4000);
    } finally {
      setIsLoadingAudio(false);
    }
  };

  return (
    <div
      className={`flex gap-3 my-4 group ${
        isUser ? "flex-row-reverse" : "flex-row"
      }`}
    >
      {/* Role Avatar */}
      <div
        className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 shadow-xs ${
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-muted-foreground border border-border"
        }`}
      >
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4 text-primary" />}
      </div>

      {/* Message Bubble Container */}
      <div
        className={`flex flex-col max-w-[85%] rounded-2xl p-4 shadow-xs ${
          isUser
            ? "bg-primary text-primary-foreground rounded-tr-xs"
            : "bg-card text-card-foreground border border-border rounded-tl-xs"
        }`}
      >
        {/* Header meta */}
        <div
          className={`flex items-center justify-between text-[11px] mb-2 pb-1.5 border-b ${
            isUser ? "border-primary-foreground/20 text-primary-foreground/80" : "border-border text-muted-foreground"
          }`}
        >
          <span className="font-semibold uppercase tracking-wider">
            {isUser ? "You" : message.ai_model || "CogniDocent AI"}
          </span>

          <div className="flex items-center gap-2">
            <span>
              {new Date(message.created_at).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>

            {/* TTS Listen Button on Assistant Messages */}
            {!isUser && (
              <div className="flex items-center gap-1.5">
                {ttsError && (
                  <span className="text-[10px] text-destructive flex items-center gap-0.5" title={ttsError}>
                    <AlertCircle className="w-3 h-3 shrink-0" />
                    <span className="truncate max-w-[100px]">{ttsError}</span>
                  </span>
                )}
                <button
                  type="button"
                  onClick={handleToggleTTS}
                  disabled={isLoadingAudio}
                  className="p-1 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                  title={isPlayingAudio ? "Stop reading" : "Read aloud (TTS)"}
                >
                  {isLoadingAudio ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : isPlayingAudio ? (
                    <VolumeX className="w-3.5 h-3.5 text-primary" />
                  ) : (
                    <Volume2 className="w-3.5 h-3.5" />
                  )}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Attached Images/Files Preview */}
        {((message.image_attachments && message.image_attachments.length > 0) ||
          (message.doc_attachments && message.doc_attachments.length > 0)) && (
          <div className="mb-3 flex flex-wrap gap-2.5 items-center">
            {/* Image Attachments with backend thumbnails */}
            {message.image_attachments?.map((att) => {
              const fileName = att.filename || att.file_name || "Attachment Image";
              const hasError = att.status === "infected" || att.status === "failed" || !!att.error;
              const errorTooltip =
                att.error ||
                (att.status === "infected"
                  ? "Security alert: Attachment flagged as infected."
                  : att.status === "failed"
                  ? "Attachment processing failed."
                  : undefined);

              return (
                <div
                  key={att.media_id}
                  className="relative group/att shrink-0 rounded-xl overflow-hidden border border-border/80 bg-black/5 dark:bg-white/5 shadow-2xs"
                  title={hasError ? errorTooltip : fileName}
                >
                  {/* Thumbnail Image using backend download endpoint */}
                  <img
                    src={chatsApi.getAttachmentThumbnailUrl(att.media_id, "small")}
                    alt={fileName}
                    className="w-20 h-20 sm:w-24 sm:h-24 object-cover rounded-xl transition-transform duration-200 group-hover/att:scale-105"
                    loading="lazy"
                  />

                  {/* Red Error Badge on top if attachment failed scan */}
                  {hasError && (
                    <div
                      className="absolute -top-1 -right-1 z-10 cursor-help"
                      title={errorTooltip}
                    >
                      <span className="flex h-4 w-4 items-center justify-center rounded-full bg-red-600 text-white shadow-xs">
                        <AlertCircle className="w-3 h-3 text-white" />
                      </span>
                    </div>
                  )}

                  {/* Subtle filename overlay on hover */}
                  <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent p-1.5 opacity-0 group-hover/att:opacity-100 transition-opacity pointer-events-none">
                    <p className="text-[10px] text-white truncate font-medium">
                      {fileName}
                    </p>
                  </div>
                </div>
              );
            })}

            {/* Document / Non-Image Attachments with FileTypeIcon */}
            {message.doc_attachments?.map((att) => {
              const fileName = att.filename || att.file_name || "Document";
              const hasError = att.status === "infected" || att.status === "failed" || !!att.error;
              const errorTooltip =
                att.error ||
                (att.status === "infected"
                  ? "Security alert: Attachment flagged as infected."
                  : att.status === "failed"
                  ? "Attachment processing failed."
                  : undefined);

              return (
                <div
                  key={att.media_id}
                  className={`relative flex items-center gap-2 px-2.5 py-1.5 rounded-xl border text-xs shadow-2xs transition-all ${
                    hasError
                      ? "border-red-500/80 bg-red-500/10 text-red-700 dark:text-red-300 ring-1 ring-red-500/30"
                      : isUser
                      ? "bg-primary-foreground/15 border-primary-foreground/25 text-primary-foreground"
                      : "bg-muted/70 border-border text-foreground"
                  }`}
                  title={hasError ? errorTooltip : fileName}
                >
                  {/* Red Error Badge on top if attachment failed scan */}
                  {hasError && (
                    <div
                      className="absolute -top-1.5 -left-1.5 z-10 cursor-help"
                      title={errorTooltip}
                    >
                      <span className="flex h-4 w-4 items-center justify-center rounded-full bg-red-600 text-white shadow-xs">
                        <AlertCircle className="w-3 h-3 text-white" />
                      </span>
                    </div>
                  )}

                  <div className="shrink-0">
                    <FileTypeIcon
                      fileName={fileName}
                      contentType={att.content_type}
                      className="w-4 h-4"
                    />
                  </div>

                  <div className="flex flex-col min-w-0">
                    <span className="font-medium truncate max-w-[130px] leading-tight">
                      {fileName}
                    </span>
                    {att.file_size_bytes ? (
                      <span className="text-[10px] opacity-75 leading-none mt-0.5">
                        {(att.file_size_bytes / 1024).toFixed(0)} KB
                      </span>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Message Body Content */}
        <div className={isUser ? "text-sm whitespace-pre-wrap leading-relaxed" : ""}>
          {isUser ? (
            message.content
          ) : (
            <MarkdownRenderer
              content={message.content}
              onCitationClick={onCitationClick}
            />
          )}
        </div>

        {/* Citations Pills List */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-3 pt-2.5 border-t border-border flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] font-semibold text-muted-foreground mr-1">
              Sources:
            </span>
            {message.citations.map((c, idx) => (
              <CitationPill
                key={`${c.ref_id}-${idx}`}
                pageNumber={c.page}
                bbox={c.bbox}
                sourceName={c.source_name}
                refId={c.ref_id}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
