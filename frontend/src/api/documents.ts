import { apiClient, getBaseApiUrl } from "./client";
import { PageDescriptionResponse } from "../types";

export const documentsApi = {
  getDocumentFileUrl(docId: string): string {
    const base = getBaseApiUrl().replace(/\/$/, "");
    return `${base}/documents/${docId}/file`;
  },

  getThumbnailUrl(docId: string, tier: "small" | "medium" | "large" = "small"): string {
    const base = getBaseApiUrl().replace(/\/$/, "");
    return `${base}/documents/${docId}/thumbnail?tier=${tier}`;
  },

  async getPageDescription(docId: string, pageNum: number): Promise<PageDescriptionResponse> {
    const response = await apiClient.get<PageDescriptionResponse>(
      `/documents/${docId}/pages/${pageNum}/description`
    );
    return response.data;
  },
};
