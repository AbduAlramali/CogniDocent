import React, { useState } from "react";
import { providersApi } from "@/api";
import { Key, Eye, EyeOff, Check, X, AlertCircle, Loader2, Cpu } from "lucide-react";

interface SettingsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

interface ProviderConfig {
  name: string;
  label: string;
  placeholder: string;
  description: string;
}

const PROVIDERS: ProviderConfig[] = [
  {
    name: "OPENAI",
    label: "OpenAI",
    placeholder: "sk-proj-...",
    description: "Used for GPT-4o, GPT-4o-mini, embeddings, and vision processing.",
  },
  {
    name: "GEMINI",
    label: "Google Gemini",
    placeholder: "AIzaSy...",
    description: "Used for Gemini 1.5 Pro, Flash, and multimodal reasoning.",
  },
  {
    name: "ANTHROPIC",
    label: "Anthropic Claude",
    placeholder: "sk-ant-...",
    description: "Used for Claude 3.5 Sonnet and Opus models.",
  },
  {
    name: "OLLAMA",
    label: "Ollama (Local)",
    placeholder: "http://localhost:11434 (or API Key if required)",
    description: "Used for local open-weights models and embeddings.",
  },
];

export const SettingsDrawer: React.FC<SettingsDrawerProps> = ({
  isOpen,
  onClose,
}) => {
  const [keys, setKeys] = useState<Record<string, string>>({
    OPENAI: "",
    GEMINI: "",
    ANTHROPIC: "",
    OLLAMA: "",
  });
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [loadingProvider, setLoadingProvider] = useState<string | null>(null);
  const [successStatus, setSuccessStatus] = useState<Record<string, boolean>>({});
  const [errorStatus, setErrorStatus] = useState<Record<string, string | null>>({});

  const handleKeyChange = (provider: string, val: string) => {
    setKeys((prev) => ({ ...prev, [provider]: val }));
    setSuccessStatus((prev) => ({ ...prev, [provider]: false }));
    setErrorStatus((prev) => ({ ...prev, [provider]: null }));
  };

  const toggleShowKey = (provider: string) => {
    setShowKeys((prev) => ({ ...prev, [provider]: !prev[provider] }));
  };

  const handleSaveKey = async (provider: string) => {
    const key = keys[provider]?.trim();
    if (!key) {
      setErrorStatus((prev) => ({
        ...prev,
        [provider]: "API key cannot be empty",
      }));
      return;
    }

    setLoadingProvider(provider);
    setErrorStatus((prev) => ({ ...prev, [provider]: null }));

    try {
      await providersApi.updateApiKey(provider, key);
      setSuccessStatus((prev) => ({ ...prev, [provider]: true }));
      // Clear key input from plaintext memory for safety
      setKeys((prev) => ({ ...prev, [provider]: "" }));
    } catch (err: any) {
      setErrorStatus((prev) => ({
        ...prev,
        [provider]: err.message || "Failed to update API key",
      }));
    } finally {
      setLoadingProvider(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-xs animate-in fade-in duration-200">
      <div
        className="w-full max-w-md bg-card text-card-foreground border-l border-border h-full flex flex-col justify-between shadow-2xl animate-in slide-in-from-right duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
              <Key className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-base">AI Provider Settings</h3>
              <p className="text-xs text-muted-foreground">
                Manage backend encrypted API keys for LLMs.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Provider Keys List */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {PROVIDERS.map((provider) => {
            const isLoading = loadingProvider === provider.name;
            const isSuccess = successStatus[provider.name];
            const error = errorStatus[provider.name];

            return (
              <div
                key={provider.name}
                className="p-4 rounded-xl border border-border bg-muted/20 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-primary" />
                    <span className="text-xs font-bold uppercase tracking-wider text-foreground">
                      {provider.label}
                    </span>
                  </div>

                  {isSuccess && (
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded-md">
                      <Check className="w-3 h-3" />
                      Active & Encrypted
                    </span>
                  )}
                </div>

                <p className="text-xs text-muted-foreground leading-relaxed">
                  {provider.description}
                </p>

                {error && (
                  <div className="p-2 rounded-lg bg-destructive/10 text-destructive text-xs flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                <div className="flex items-center gap-2">
                  <div className="relative flex-1">
                    <input
                      type={showKeys[provider.name] ? "text" : "password"}
                      value={keys[provider.name]}
                      onChange={(e) =>
                        handleKeyChange(provider.name, e.target.value)
                      }
                      placeholder={provider.placeholder}
                      disabled={isLoading}
                      className="w-full px-3 py-2 pr-9 rounded-lg border border-border bg-background text-foreground text-xs focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-all font-mono"
                    />
                    <button
                      type="button"
                      onClick={() => toggleShowKey(provider.name)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showKeys[provider.name] ? (
                        <EyeOff className="w-3.5 h-3.5" />
                      ) : (
                        <Eye className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleSaveKey(provider.name)}
                    disabled={!keys[provider.name]?.trim() || isLoading}
                    className="px-3 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/95 disabled:opacity-40 disabled:pointer-events-none transition-all shadow-xs shrink-0"
                  >
                    {isLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      "Save"
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer info */}
        <div className="p-4 border-t border-border text-center text-[11px] text-muted-foreground bg-muted/20">
          Keys are encrypted with AES-256 before being stored in the backend database.
        </div>
      </div>
    </div>
  );
};
