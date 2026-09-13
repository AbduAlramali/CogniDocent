import { apiClient } from "./client";
import { ProvidersModelsMap, UpdateApiKeyResponse } from "../types";

export const providersApi = {
  async listProvidersModels(): Promise<ProvidersModelsMap> {
    const response = await apiClient.get<ProvidersModelsMap>("/providers/models");
    return response.data;
  },

  async updateApiKey(
    providerName: string,
    apiKey: string
  ): Promise<UpdateApiKeyResponse> {
    const response = await apiClient.put<UpdateApiKeyResponse>(
      `/providers/${providerName}/api-key`,
      { api_key: apiKey }
    );
    return response.data;
  },
};
