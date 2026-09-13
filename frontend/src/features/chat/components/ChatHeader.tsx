import React from "react";
import { useWorkspaceStore } from "@/shared/store/useWorkspaceStore";
import { ChatSession, ProvidersModelsMap } from "@/types";
import { Plus, Trash2, Cpu, Sparkles, MessageSquare } from "lucide-react";

interface ChatHeaderProps {
  chats: ChatSession[];
  providersData?: ProvidersModelsMap;
  onNewChat: () => void;
  onDeleteChat: (chatId: string) => void;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  chats,
  providersData,
  onNewChat,
  onDeleteChat,
}) => {
  const activeChatId = useWorkspaceStore((state) => state.activeChatId);
  const setActiveChatId = useWorkspaceStore((state) => state.setActiveChatId);

  const currentProvider = useWorkspaceStore((state) => state.currentProvider);
  const setCurrentProvider = useWorkspaceStore((state) => state.setCurrentProvider);
  const currentModel = useWorkspaceStore((state) => state.currentModel);
  const setCurrentModel = useWorkspaceStore((state) => state.setCurrentModel);
  const thinkingMode = useWorkspaceStore((state) => state.thinkingMode);
  const setThinkingMode = useWorkspaceStore((state) => state.setThinkingMode);

  // Available providers from API or fallback defaults
  const availableProviders = providersData
    ? Object.keys(providersData)
    : ["OPENAI", "GEMINI", "ANTHROPIC", "OLLAMA"];

  // Available models for current provider
  const availableModels =
    providersData && providersData[currentProvider]
      ? Object.keys(providersData[currentProvider])
      : ["gpt-4o", "gpt-4o-mini", "gemini-1.5-pro", "llama3"];

  const currentModelMeta =
    providersData && providersData[currentProvider]
      ? providersData[currentProvider][currentModel]
      : null;

  const supportsThinking = currentModelMeta?.supports_thinking ?? false;
  const allowedThinkingLevels = currentModelMeta?.allowed_levels?.length
    ? ["none", ...currentModelMeta.allowed_levels]
    : ["none", "low", "medium", "high"];

  const handleProviderChange = (newProvider: string) => {
    setCurrentProvider(newProvider);
    if (providersData && providersData[newProvider]) {
      const models = Object.keys(providersData[newProvider]);
      if (models.length > 0) {
        setCurrentModel(models[0]);
      }
    }
  };

  return (
    <div className="flex flex-col border-b border-border bg-card select-none">
      {/* Top row: Chat switcher and New Chat */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/60">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <MessageSquare className="w-4 h-4 text-primary shrink-0" />
          <select
            value={activeChatId || ""}
            onChange={(e) => setActiveChatId(e.target.value ? e.target.value : null)}
            className="text-xs font-semibold bg-background border border-border rounded-lg px-2.5 py-1 text-foreground focus:outline-none focus:ring-1 focus:ring-primary max-w-[200px] truncate"
          >
            <option value="">-- New Conversation --</option>
            {chats.map((chat) => (
              <option key={chat.chat_id} value={chat.chat_id}>
                {chat.title || `Chat ${chat.chat_id.slice(0, 6)}`}
              </option>
            ))}
          </select>

          {activeChatId && (
            <button
              type="button"
              onClick={() => {
                if (confirm("Delete this conversation?")) {
                  onDeleteChat(activeChatId);
                }
              }}
              className="p-1 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors shrink-0"
              title="Delete conversation"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        <button
          type="button"
          onClick={onNewChat}
          className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/95 shadow-xs transition-all shrink-0"
          title="Create a new conversation session"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Chat</span>
        </button>
      </div>

      {/* Bottom row: Provider, Model, and Thinking Mode Selectors */}
      <div className="flex flex-wrap items-center justify-between px-4 py-2 gap-2 bg-muted/25 text-xs">
        <div className="flex items-center gap-2">
          {/* Provider Selector */}
          <div className="flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-muted-foreground" />
            <select
              value={currentProvider}
              onChange={(e) => handleProviderChange(e.target.value)}
              className="border border-border rounded-md px-2 py-0.5 text-xs bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              {availableProviders.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>

          {/* Model Selector */}
          <select
            value={currentModel}
            onChange={(e) => setCurrentModel(e.target.value)}
            className="border border-border rounded-md px-2 py-0.5 text-xs bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary max-w-[150px] truncate"
          >
            {availableModels.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>

        {/* Thinking Mode Control (if supported by model or provider) */}
        {supportsThinking && (
          <div className="flex items-center gap-1.5">
            <Sparkles className="w-3 h-3 text-amber-500" />
            <span className="text-[11px] text-muted-foreground font-medium">
              Reasoning:
            </span>
            <select
              value={thinkingMode}
              onChange={(e) => setThinkingMode(e.target.value)}
              className="border border-border rounded-md px-1.5 py-0.5 text-xs bg-background text-foreground capitalize focus:outline-none focus:ring-1 focus:ring-primary"
            >
              {allowedThinkingLevels.map((lvl) => (
                <option key={lvl} value={lvl}>
                  {lvl}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
    </div>
  );
};
