import React, { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useWorkspaceStore } from "@/shared/store/useWorkspaceStore";
import { chatsApi, providersApi } from "@/api";
import { MessageWithAttachments } from "@/types";
import { ChatHeader } from "./ChatHeader";
import { MessageItem } from "./MessageItem";
import { ChatInputBar } from "./ChatInputBar";
import { Bot, Loader2, Sparkles } from "lucide-react";

export const ChatContainer: React.FC = () => {
  const queryClient = useQueryClient();
  const activeProjectId = useWorkspaceStore((state) => state.activeProjectId);
  const activeChatId = useWorkspaceStore((state) => state.activeChatId);
  const setActiveChatId = useWorkspaceStore((state) => state.setActiveChatId);
  const jumpToPage = useWorkspaceStore((state) => state.jumpToPage);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [localMessages, setLocalMessages] = useState<MessageWithAttachments[]>([]);

  // 1. Fetch chat sessions for current project
  const { data: chats = [] } = useQuery({
    queryKey: ["chats", activeProjectId],
    queryFn: () => (activeProjectId ? chatsApi.listChats(activeProjectId) : []),
    enabled: !!activeProjectId,
  });

  // 2. Fetch supported AI providers and models
  const { data: providersData } = useQuery({
    queryKey: ["providers-models"],
    queryFn: () => providersApi.listProvidersModels(),
    staleTime: 1000 * 60 * 10, // 10 minutes cache
  });

  // 3. Fetch messages for active chat session
  const { data: serverMessages = [] } = useQuery({
    queryKey: ["messages", activeChatId],
    queryFn: () => (activeChatId ? chatsApi.listMessages(activeChatId) : []),
    enabled: !!activeChatId,
  });

  // Synchronize server messages to local messages when chat session changes
  useEffect(() => {
    if (activeChatId) {
      setLocalMessages(serverMessages);
    } else {
      setLocalMessages([]);
    }
  }, [activeChatId, serverMessages]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [localMessages]);

  // 4. Send Completion Mutation
  const sendMutation = useMutation({
    mutationFn: (payload: { message: string; attachmentIds: string[] }) => {
      if (!activeProjectId) throw new Error("No active project");
      return chatsApi.sendCompletion({
        project_id: activeProjectId,
        chat_id: activeChatId,
        message: payload.message,
        attachment_ids: payload.attachmentIds,
      });
    },
    onSuccess: (assistantMessage) => {
      // If a new chat session was generated automatically, set it as active
      if (!activeChatId && assistantMessage.chat_id) {
        setActiveChatId(assistantMessage.chat_id);
      }
      setLocalMessages((prev) => [...prev, assistantMessage]);
      queryClient.invalidateQueries({ queryKey: ["chats", activeProjectId] });
      queryClient.invalidateQueries({ queryKey: ["messages", assistantMessage.chat_id] });
    },
    onError: (err: any) => {
      // Append an assistant error notification
      const errorMsg: MessageWithAttachments = {
        message_id: crypto.randomUUID(),
        chat_id: activeChatId || "error",
        role: "assistant",
        content: `**Error**: ${err.message || "Failed to generate completion."}`,
        created_at: new Date().toISOString(),
      };
      setLocalMessages((prev) => [...prev, errorMsg]);
    },
  });

  const handleSendMessage = async (text: string, attachmentIds: string[]) => {
    // 1. Optimistically append user message
    const optimisticUserMsg: MessageWithAttachments = {
      message_id: crypto.randomUUID(),
      chat_id: activeChatId || "pending",
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };
    setLocalMessages((prev) => [...prev, optimisticUserMsg]);

    // 2. Trigger API completion
    await sendMutation.mutateAsync({ message: text, attachmentIds });
  };

  const handleNewChat = () => {
    setActiveChatId(null);
    setLocalMessages([]);
  };

  const handleDeleteChat = async (chatId: string) => {
    try {
      await chatsApi.deleteChat(chatId);
      queryClient.invalidateQueries({ queryKey: ["chats", activeProjectId] });
      if (activeChatId === chatId) {
        handleNewChat();
      }
    } catch (err) {
      console.error("Failed to delete chat:", err);
    }
  };

  if (!activeProjectId) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center text-muted-foreground">
        <Bot className="w-12 h-12 text-primary/40 mb-3" />
        <p className="text-sm">Select a project to begin chatting with documents.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-background text-foreground overflow-hidden">
      {/* Top Header Controls: Chat Selector, Provider & Model dropdowns */}
      <ChatHeader
        chats={chats}
        providersData={providersData}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
      />

      {/* Main Messages Feed */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {localMessages.length === 0 && !sendMutation.isPending && (
          <div className="py-20 text-center text-muted-foreground max-w-sm mx-auto flex flex-col items-center">
            <div className="w-12 h-12 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mb-4">
              <Sparkles className="w-6 h-6" />
            </div>
            <h4 className="text-base font-bold text-foreground">AI Research Assistant</h4>
            <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">
              Ask questions about the document, snip charts from the PDF on the left, or highlight text to quote and verify claims.
            </p>
          </div>
        )}

        {/* Message Feed */}
        {localMessages.map((msg) => (
          <MessageItem
            key={msg.message_id}
            message={msg}
            onCitationClick={(page) => jumpToPage(page)}
          />
        ))}

        {/* Streaming / Generating Indicator */}
        {sendMutation.isPending && (
          <div className="flex gap-3 my-4 items-center animate-in fade-in">
            <div className="w-8 h-8 rounded-xl bg-muted text-primary border border-border flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4" />
            </div>
            <div className="flex items-center gap-2 px-4 py-3 rounded-2xl bg-card border border-border text-xs text-muted-foreground shadow-xs">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
              <span>Analyzing document and generating response...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Bottom Composer Bar */}
      <ChatInputBar
        projectId={activeProjectId}
        onSendMessage={handleSendMessage}
        isSending={sendMutation.isPending}
      />
    </div>
  );
};
