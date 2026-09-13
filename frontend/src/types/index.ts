export type ChatProviderType = "OPENAI" | "GEMINI" | "ANTHROPIC" | "OLLAMA";

export interface ProjectThumbnails {
  small?: string;
  medium?: string;
  large?: string;
  [key: string]: string | undefined;
}

export interface Project {
  project_id: string;
  doc_id: string;
  title: string;
  description?: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at?: string | null;
  thumbnails?: ProjectThumbnails | null;
}

export interface ProjectCreatedResponse {
  project_id: string;
  doc_id: string;
}

export interface PageDescriptionResponse {
  document_id: string;
  page_num: number;
  description: string;
}

export interface CitationMetadata {
  ref_id: string;
  page: number;
  bbox: number[]; // [ymin, xmin, ymax, xmax]
  source_name: string;
}

export interface MediaItem {
  media_id: string;
  file_name: string;
  content_type: string;
  file_size_bytes?: number;
  status: string;
  created_at?: string;
}

export interface MessageWithAttachments {
  message_id: string;
  chat_id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  citations?: CitationMetadata[] | null;
  created_at: string;
  token_count?: number | null;
  ai_provider?: string | null;
  ai_model?: string | null;
  thinking_mode?: string | null;
  image_attachments?: MediaItem[];
  doc_attachments?: MediaItem[];
}

export interface ChatSession {
  chat_id: string;
  project_id: string;
  title: string;
  ai_provider: string;
  ai_model: string;
  thinking_mode?: string | null;
  metadata?: Record<string, any> | null;
  is_archived: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface ChatCompletionRequest {
  project_id: string;
  chat_id?: string | null;
  message: string;
  attachment_ids?: string[];
}

export interface ModelCapabilities {
  supports_thinking: boolean;
  allowed_levels: string[];
  max_input_tokens?: number | null;
  max_output_tokens?: number | null;
}

export type ProvidersModelsMap = Record<string, Record<string, ModelCapabilities>>;

export interface UpdateApiKeyResponse {
  message: string;
  provider_name: string;
  is_active: boolean;
}

export interface NotificationDTO {
  user_id?: string;
  event_type?: string;
  message: string;
  payload?: any;
  timestamp?: string;
}
