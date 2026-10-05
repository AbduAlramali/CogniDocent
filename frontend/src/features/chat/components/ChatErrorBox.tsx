import React, { useState } from "react";
import { MessageWithAttachments } from "@/types";
import { useWorkspaceStore } from "@/shared/store/useWorkspaceStore";
import {
  extractOllamaCommand,
  isLegacyErrorMessage,
  parseLegacyErrorMessage,
} from "@/api/errors";
import {
  AlertTriangle,
  AlertCircle,
  Terminal,
  Settings,
  RotateCcw,
  Copy,
  Check,
  Sparkles,
} from "lucide-react";

interface ChatErrorBoxProps {
  message: MessageWithAttachments;
  onRetry?: () => void;
}

export const ChatErrorBox: React.FC<ChatErrorBoxProps> = ({
  message,
  onRetry,
}) => {
  const [copied, setCopied] = useState(false);
  const setIsSettingsOpen = useWorkspaceStore((state) => state.setIsSettingsOpen);

  // Extract structured error data from message.error_info or fallback legacy parser
  const errorInfo = message.error_info;
  let title = errorInfo?.title;
  let messageText = errorInfo?.message || message.content;
  let category = errorInfo?.category || "";
  let statusCode = errorInfo?.statusCode;
  let suggestion = errorInfo?.suggestion;
  let command = errorInfo?.command;

  if (!errorInfo && isLegacyErrorMessage(message.content)) {
    const parsed = parseLegacyErrorMessage(message.content);
    title = parsed.title;
    messageText = parsed.message;
    command = parsed.command;
  }

  if (!title) {
    title = "Response Generation Failed";
  }

  // Derive contextual flags
  const lowerMsg = messageText.toLowerCase();
  const isLocalModel =
    category === "local_model_not_found" ||
    !!command ||
    lowerMsg.includes("ollama run") ||
    lowerMsg.includes("not downloaded");

  const isAuth =
    category === "authentication_failed" ||
    lowerMsg.includes("api key") ||
    lowerMsg.includes("authentication failed") ||
    lowerMsg.includes("unauthorized");

  const ollamaCmd = command || extractOllamaCommand(messageText) || "ollama run <model>";

  const handleCopyCommand = () => {
    navigator.clipboard.writeText(ollamaCmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div className="flex gap-3 my-4 group flex-row animate-in fade-in slide-in-from-bottom-2 duration-200">
      {/* Red Error Avatar */}
      <div className="w-8 h-8 rounded-xl bg-red-100 dark:bg-red-950/80 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800/70 flex items-center justify-center shrink-0 shadow-xs">
        <AlertTriangle className="w-4 h-4" />
      </div>

      {/* Red Error Bubble Container */}
      <div className="flex flex-col w-full max-w-[85%] rounded-2xl rounded-tl-xs p-4 sm:p-5 border border-red-200 dark:border-red-900/60 bg-red-50/70 dark:bg-red-950/25 text-red-950 dark:text-red-100 shadow-xs">
        {/* Header line: Title badge, status code pill, timestamp */}
        <div className="flex items-center justify-between pb-2 mb-1.5 border-b border-red-200/60 dark:border-red-900/50 text-[11px]">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800/80">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              {title}
            </span>

            {statusCode && statusCode > 0 ? (
              <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-red-200/60 dark:bg-red-900/40 text-red-800 dark:text-red-300 font-bold">
                HTTP {statusCode}
              </span>
            ) : null}
          </div>

          <span className="text-red-600/70 dark:text-red-400/70 font-medium">
            {new Date(message.created_at).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>

        {/* Primary Error Message Body */}
        <p className="text-sm font-medium text-red-900 dark:text-red-200 mt-1 leading-relaxed">
          {messageText}
        </p>

        {/* Contextual Action Widget: Local Model Missing */}
        {isLocalModel && (
          <div className="mt-3.5 rounded-xl bg-neutral-900 text-neutral-100 border border-neutral-800 p-3 font-mono text-xs shadow-inner">
            <div className="flex items-center justify-between text-neutral-400 text-[11px] mb-2 pb-1.5 border-b border-neutral-800">
              <span className="flex items-center gap-1.5 font-medium text-neutral-300">
                <Terminal className="w-3.5 h-3.5 text-red-400" />
                Terminal Command to Pull Model
              </span>
              <button
                type="button"
                onClick={handleCopyCommand}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-neutral-800 hover:bg-neutral-700 text-neutral-200 text-[11px] font-sans font-medium transition-colors cursor-pointer"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-emerald-400">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy Command</span>
                  </>
                )}
              </button>
            </div>
            <div className="p-2.5 rounded-lg bg-black/60 text-emerald-400 select-all overflow-x-auto font-mono text-xs">
              <code>{ollamaCmd}</code>
            </div>
            <p className="text-[11px] text-neutral-400 mt-2 font-sans leading-normal">
              Run this in your terminal to download the model locally, or switch to a cloud provider from the top dropdown.
            </p>
          </div>
        )}

        {/* Contextual Action Widget: API Key Missing or Invalid */}
        {isAuth && (
          <div className="mt-3.5 p-3.5 rounded-xl bg-white/70 dark:bg-black/30 border border-red-200 dark:border-red-900/50 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="text-xs text-red-800 dark:text-red-200">
              <p className="font-semibold">Provider API key required</p>
              <p className="text-red-700/80 dark:text-red-300/80 mt-0.5 leading-normal">
                Please configure a valid API key in Settings to use this AI model.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setIsSettingsOpen(true)}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors shadow-xs shrink-0 cursor-pointer"
            >
              <Settings className="w-3.5 h-3.5" />
              Open Settings
            </button>
          </div>
        )}

        {/* Contextual Suggestion for other error types */}
        {suggestion && !isLocalModel && !isAuth && (
          <div className="mt-3.5 p-3 rounded-xl bg-white/70 dark:bg-black/30 border border-red-200 dark:border-red-900/50 text-xs text-red-800 dark:text-red-200 flex items-start gap-2">
            <Sparkles className="w-3.5 h-3.5 text-red-500 shrink-0 mt-0.5" />
            <span className="leading-relaxed">{suggestion}</span>
          </div>
        )}

        {/* Action Toolbar at Bottom */}
        <div className="mt-3.5 pt-2.5 border-t border-red-200/60 dark:border-red-900/50 flex items-center justify-between gap-2">
          <span className="text-[11px] text-red-700/80 dark:text-red-300/80">
            AI completion could not be completed.
          </span>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-red-100 hover:bg-red-200/80 dark:bg-red-900/40 dark:hover:bg-red-900/70 text-red-800 dark:text-red-200 border border-red-300 dark:border-red-800 transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Retry Request
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
