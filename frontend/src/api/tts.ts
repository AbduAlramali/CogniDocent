import { apiClient } from "./client";

export const ttsApi = {
  async synthesizeSpeech(text: string, voice: string = "alloy"): Promise<Blob> {
    const response = await apiClient.post(
      "/tts/synthesize",
      { text, voice },
      { responseType: "blob" }
    );
    return response.data;
  },
};
