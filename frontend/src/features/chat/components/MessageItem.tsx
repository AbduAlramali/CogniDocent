import React, { useState, useRef } from "react";
import { MessageWithAttachments } from "@/types";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { CitationPill } from "./CitationPill";
import { ttsApi } from "@/api";
import {
  Bot,
  User,
  Volume2,
  VolumeX,
  Loader2,
  Paperclip,
  Image as ImageIcon,
} from "lucide-react";

interface MessageItemProps {
  message: MessageWithAttachments;
  onCitationClick?: (page: number) => void;
}

export const MessageItem: React.FC<MessageItemProps> = ({
  message,
  onCitationClick,
}) => {
  const isUser = message.role === "user";
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [isLoadingAudio, setIsLoadingAudio] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const handleToggleTTS = async () => {
    if (isPlayingAudio && audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsPlayingAudio(false);
      return;
    }

    setIsLoadingAudio(true);
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
    } catch (err) {
      console.error("TTS synthesis error:", err);
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
            )}
          </div>
        </div>

        {/* Attached Images/Files Preview */}
        {((message.image_attachments && message.image_attachments.length > 0) ||
          (message.doc_attachments && message.doc_attachments.length > 0)) && (
          <div className="mb-3 flex flex-wrap gap-2">
            {message.image_attachments?.map((att) => (
              <div
                key={att.media_id}
                className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-black/10 border border-white/10 text-xs"
              >
                <ImageIcon className="w-3.5 h-3.5 shrink-0" />
                <span className="truncate max-w-[120px]">{att.file_name}</span>
              </div>
            ))}
            {message.doc_attachments?.map((att) => (
              <div
                key={att.media_id}
                className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-black/10 border border-white/10 text-xs"
              >
                <Paperclip className="w-3.5 h-3.5 shrink-0" />
                <span className="truncate max-w-[120px]">{att.file_name}</span>
              </div>
            ))}
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
