import { apiClient, getBaseApiUrl } from "./client";
import {
  ChatCompletionRequest,
  ChatSession,
  MediaItem,
  MessageWithAttachments,
} from "../types";
import { computeFileHash } from "../shared/utils/crypto";

export const chatsApi = {
  async listChats(
    projectId: string,
    includeArchived: boolean = false
  ): Promise<ChatSession[]> {
    const response = await apiClient.get<ChatSession[]>("/chats", {
      params: {
        project_id: projectId,
        include_archived: includeArchived,
      },
    });
    return response.data;
  },

  async deleteChat(chatId: string): Promise<void> {
    await apiClient.delete(`/chats/${chatId}`);
  },

  async listMessages(chatId: string): Promise<MessageWithAttachments[]> {
    const response = await apiClient.get<MessageWithAttachments[]>(
      `/chats/${chatId}/messages`
    );
    return response.data;
  },

  async sendCompletion(
    payload: ChatCompletionRequest
  ): Promise<MessageWithAttachments> {
    const response = await apiClient.post<MessageWithAttachments>(
      "/chats/completion",
      payload
    );
    return response.data;
  },

  async uploadAttachment(
    projectId: string,
    file: File | Blob,
    filename: string = "attachment.png"
  ): Promise<MediaItem> {
    const fileHash = await computeFileHash(file);
    const formData = new FormData();
    formData.append("file", file, filename);
    formData.append("project_id", projectId);
    formData.append("file_hash", fileHash);

    const response = await apiClient.post<MediaItem>(
      "/chats/attachments",
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );
    return response.data;
  },

  getAttachmentThumbnailUrl(
    mediaId: string,
    tier: "small" | "medium" | "large" = "small"
  ): string {
    const base = getBaseApiUrl().replace(/\/$/, "");
    return `${base}/chats/attachments/${mediaId}/thumbnail?tier=${tier}`;
  },

  async getAttachmentThumbnails(
    mediaId: string
  ): Promise<Record<string, string>> {
    const response = await apiClient.get<Record<string, string>>(
      `/chats/attachments/${mediaId}/thumbnails`
    );
    return response.data;
  },
};
