/**
 * Structured API Error handling based on backend domain exceptions.
 * Reference: backend/src/exception_handlers.py
 */

export type ErrorCategory =
  | "local_model_not_found"   // 404 LocalModelNotFoundError
  | "entity_not_found"        // 404 EntityNotFoundError, TTSVoiceNotFoundError, etc.
  | "authentication_failed"   // 502 LLMAuthenticationError
  | "rate_limit"              // 429 LLMRateLimitError, EmbeddingRateLimitError, TTSRateLimitError
  | "context_limit"           // 400 LLMContextLimitExceededError
  | "bad_request"             // 400 ValueError, ChatServiceError, DocumentError
  | "conflict"                // 409 DuplicateEntityError
  | "payload_too_large"       // 413 ParserResourceLimitError
  | "validation_error"        // 422 RequestValidationError, FastParserError
  | "timeout"                 // 504 OrchestrationTimeoutError, HTTPTimeoutError
  | "provider_error"          // 502 LLMProviderError, EmbeddingProviderError, TTSProviderError
  | "infrastructure_error"    // 500 RepositoryError, KeyStoreError, EncryptionError, etc.
  | "network_error";          // Client network failure / unreachability

export class ApiError extends Error {
  public statusCode: number;
  public details?: any;
  public category: ErrorCategory;
  public suggestion?: string;
  public rawMessage: string;

  constructor(message: string, statusCode: number = 500, details?: any) {
    super(message);
    this.name = "ApiError";
    this.rawMessage = message;
    this.statusCode = statusCode;
    this.details = details;
    this.category = categorizeError(statusCode, message);
    this.suggestion = getErrorSuggestion(this.category, message);
  }

  get isLocalModelNotFound(): boolean {
    return this.category === "local_model_not_found";
  }

  get isAuthenticationError(): boolean {
    return this.category === "authentication_failed";
  }

  get isRateLimit(): boolean {
    return this.category === "rate_limit";
  }

  get isContextLimit(): boolean {
    return this.category === "context_limit";
  }

  get isTimeout(): boolean {
    return this.category === "timeout";
  }

  get isValidationError(): boolean {
    return this.category === "validation_error";
  }

  get isInfrastructureError(): boolean {
    return this.category === "infrastructure_error";
  }
}

export const categorizeError = (statusCode: number, message: string): ErrorCategory => {
  const lowerMsg = message.toLowerCase();

  // 404 Not Found
  if (statusCode === 404) {
    if (
      lowerMsg.includes("not downloaded") ||
      lowerMsg.includes("ollama run") ||
      lowerMsg.includes("model '") ||
      (lowerMsg.includes("model") && lowerMsg.includes("not found"))
    ) {
      return "local_model_not_found";
    }
    return "entity_not_found";
  }

  // 429 Rate Limit
  if (statusCode === 429) {
    return "rate_limit";
  }

  // 400 Bad Request
  if (statusCode === 400) {
    if (
      lowerMsg.includes("context limit") ||
      lowerMsg.includes("token limit") ||
      lowerMsg.includes("maximum context")
    ) {
      return "context_limit";
    }
    return "bad_request";
  }

  // 409 Conflict
  if (statusCode === 409) {
    return "conflict";
  }

  // 413 Payload Too Large
  if (statusCode === 413) {
    return "payload_too_large";
  }

  // 422 Validation
  if (statusCode === 422) {
    return "validation_error";
  }

  // 504 Timeout
  if (statusCode === 504) {
    return "timeout";
  }

  // 502 Bad Gateway / Provider failure
  if (statusCode === 502) {
    if (
      lowerMsg.includes("authentication failed") ||
      lowerMsg.includes("check api key") ||
      lowerMsg.includes("api_key") ||
      lowerMsg.includes("unauthorized")
    ) {
      return "authentication_failed";
    }
    return "provider_error";
  }

  // 500 Infrastructure Errors (KeyStoreError, EncryptionError, Database, etc.)
  if (statusCode === 500) {
    return "infrastructure_error";
  }

  if (statusCode === 0) {
    return "network_error";
  }

  return "infrastructure_error";
};

export const getErrorSuggestion = (
  category: ErrorCategory,
  message: string
): string | undefined => {
  switch (category) {
    case "local_model_not_found": {
      // Extract model name from message e.g. "Model 'llama3' is not downloaded..."
      const match = message.match(/Model '([^']+)'/i) || message.match(/`ollama run ([^`]+)`/i);
      const modelName = match ? match[1] : "<model_name>";
      return `Run \`ollama run ${modelName}\` in your terminal to download it, or select a cloud provider from the top dropdown.`;
    }
    case "authentication_failed":
      return "Open Settings (gear icon in the top bar) to configure a valid API key for this provider.";
    case "rate_limit":
      return "The AI provider throttled this request. Please wait a moment before trying again.";
    case "context_limit":
      return "Try switching chat scope to 'Current Page Only' or select a model with a larger context window.";
    case "timeout":
      return "The request took too long to complete. Please try again.";
    case "payload_too_large":
      return "The document exceeds the maximum page or file size limit supported by the parser.";
    case "infrastructure_error":
      return "An internal service error occurred. Please check server logs or retry shortly.";
    case "network_error":
      return "Unable to connect to backend server. Please verify your network and server status.";
    default:
      return undefined;
  }
};

/**
 * Extracts a copyable ollama command if present in a local model error.
 */
export const extractOllamaCommand = (message: string): string | null => {
  const match = message.match(/`ollama run ([^`]+)`/i) || message.match(/Model '([^']+)'/i);
  if (match) {
    return `ollama run ${match[1]}`;
  }
  return null;
};

/**
 * Formats an API error into GitHub-flavored Markdown for chat message feeds.
 */
export const formatApiErrorToMarkdown = (err: unknown): string => {
  const apiError = toApiError(err);
  const suggestion = apiError.suggestion;

  switch (apiError.category) {
    case "local_model_not_found": {
      const ollamaCmd = extractOllamaCommand(apiError.message) || "ollama run <model>";
      return [
        `> ⚠️ **Local Model Not Downloaded**`,
        `>`,
        `> ${apiError.message}`,
        `>`,
        `> **Terminal Command to Download:**`,
        `> \`\`\`bash`,
        `> ${ollamaCmd}`,
        `> \`\`\``,
        `>`,
        `> *Tip: You can also switch to another model or provider in the dropdown above.*`,
      ].join("\n");
    }

    case "authentication_failed":
      return [
        `> 🔑 **API Key Missing or Invalid**`,
        `>`,
        `> ${apiError.message}`,
        `>`,
        `> Please open **Settings** in the top navigation bar to configure a valid API key for this provider.`,
      ].join("\n");

    case "rate_limit":
      return [
        `> ⏳ **Rate Limit Exceeded**`,
        `>`,
        `> ${apiError.message}`,
        `>`,
        `> ${suggestion || "Please wait a moment before sending another message."}`,
      ].join("\n");

    case "context_limit":
      return [
        `> 📏 **Context Limit Exceeded**`,
        `>`,
        `> ${apiError.message}`,
        `>`,
        `> ${suggestion || "Try switching to Current Page Only scope or choosing a larger model."}`,
      ].join("\n");

    case "timeout":
      return [
        `> ⏱️ **Request Timed Out**`,
        `>`,
        `> ${apiError.message}`,
        `>`,
        `> The AI service took too long to respond. Please try again.`,
      ].join("\n");

    case "payload_too_large":
      return [
        `> 📦 **Payload Too Large**`,
        `>`,
        `> ${apiError.message}`,
      ].join("\n");

    case "validation_error":
      return [
        `> ⚠️ **Validation Error**`,
        `>`,
        `> ${apiError.message}`,
      ].join("\n");

    case "infrastructure_error":
      return [
        `> 🛠️ **System Error**`,
        `>`,
        `> ${apiError.message}`,
        `>`,
        `> An internal service error occurred. Please try again later.`,
      ].join("\n");

    default:
      return [
        `> ⚠️ **Error**`,
        `>`,
        `> ${apiError.message}`,
      ].join("\n");
  }
};

/**
 * Normalizes any error object into an ApiError instance.
 */
export const toApiError = (err: unknown): ApiError => {
  if (err instanceof ApiError) {
    return err;
  }

  if (typeof err === "object" && err !== null && "response" in err) {
    const axiosErr = err as any;
    const statusCode = axiosErr.response?.status || 500;
    const data = axiosErr.response?.data;
    const message =
      data?.message ||
      data?.detail ||
      axiosErr.message ||
      "An unexpected server error occurred";
    const details = data?.details;
    return new ApiError(message, statusCode, details);
  }

  if (err instanceof Error) {
    return new ApiError(err.message, 500);
  }

  return new ApiError(String(err || "An unknown error occurred"), 500);
};

/**
 * Returns a human-friendly title for each error category.
 */
export const getErrorTitle = (category: ErrorCategory): string => {
  switch (category) {
    case "local_model_not_found":
      return "Local Model Not Downloaded";
    case "authentication_failed":
      return "API Key Missing or Invalid";
    case "rate_limit":
      return "Rate Limit Exceeded";
    case "context_limit":
      return "Context Window Exceeded";
    case "timeout":
      return "Request Timed Out";
    case "payload_too_large":
      return "Payload Too Large";
    case "validation_error":
      return "Validation Error";
    case "provider_error":
      return "AI Provider Error";
    case "infrastructure_error":
      return "Service Infrastructure Error";
    case "network_error":
      return "Connection Failed";
    default:
      return "Response Generation Failed";
  }
};

/**
 * Checks if a message content string represents a legacy markdown error block.
 */
export const isLegacyErrorMessage = (content: string): boolean => {
  return (
    content.startsWith("> ⚠️") ||
    content.startsWith("> 🔑") ||
    content.startsWith("> ⏳") ||
    content.startsWith("> 📏") ||
    content.startsWith("> ⏱️") ||
    content.startsWith("> 🛠️") ||
    content.startsWith("> 📦")
  );
};

/**
 * Parses legacy markdown blockquote errors into structured title and clean message.
 */
export const parseLegacyErrorMessage = (
  content: string
): { title: string; message: string; command?: string } => {
  const lines = content
    .split("\n")
    .map((l) => l.replace(/^>\s?/, "").trim())
    .filter(Boolean);

  const firstLine = lines[0] || "Response Generation Failed";
  const title = firstLine.replace(/[*_#]/g, "").replace(/^[^a-zA-Z0-9]+/, "").trim();

  // Find actual error message line
  const msgLines = lines.filter(
    (l) =>
      !l.startsWith("**") &&
      !l.startsWith("```") &&
      !l.startsWith("*Tip:") &&
      !l.startsWith("Please open") &&
      !l.startsWith("Run `") &&
      l !== firstLine
  );

  const message = msgLines.join(" ") || title;
  const command = extractOllamaCommand(content) || undefined;

  return {
    title: title || "Response Generation Failed",
    message,
    command,
  };
};
