import { create } from "zustand";
import { Project } from "@/types";

export type ChatScope = "current_page" | "entire_document";

export interface PendingSnippet {
  id: string;
  blob: Blob;
  previewUrl: string;
  filename: string;
  pageNum: number;
}

interface WorkspaceState {
  activeProjectId: string | null;
  activeProject: Project | null;
  activeDocId: string | null;
  activePage: number;
  totalPages: number;
  scale: number;
  chatScope: ChatScope;
  currentProvider: string;
  currentModel: string;
  thinkingMode: string;
  activeChatId: string | null;
  isSettingsOpen: boolean;

  // Annotation & Snipping
  snippingMode: boolean;
  activeBbox: number[] | null; // [ymin, xmin, ymax, xmax]
  quoteToAppend: string | null;
  pendingSnippets: PendingSnippet[];

  // Actions
  setActiveProjectId: (id: string | null) => void;
  setActiveProject: (project: Project | null) => void;
  setActiveDocId: (docId: string | null) => void;
  setActivePage: (page: number) => void;
  setTotalPages: (total: number) => void;
  setScale: (scale: number) => void;
  setChatScope: (scope: ChatScope) => void;
  setCurrentProvider: (provider: string) => void;
  setCurrentModel: (model: string) => void;
  setThinkingMode: (mode: string) => void;
  setActiveChatId: (chatId: string | null) => void;
  setIsSettingsOpen: (open: boolean) => void;

  setSnippingMode: (active: boolean) => void;
  setActiveBbox: (bbox: number[] | null) => void;
  setQuoteToAppend: (quote: string | null) => void;
  consumeQuoteToAppend: () => string | null;
  addPendingSnippet: (snippet: PendingSnippet) => void;
  removePendingSnippet: (id: string) => void;
  clearPendingSnippets: () => void;

  /**
   * Action triggered by CitationPills or direct selection.
   * Jumps the PDF viewer to the specified page index (bounded between 1 and totalPages).
   */
  jumpToPage: (pageNumber: number, bbox?: number[] | null) => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  activeProjectId: null,
  activeProject: null,
  activeDocId: null,
  activePage: 1,
  totalPages: 1,
  scale: 1.0,
  chatScope: "entire_document",
  currentProvider: "OPENAI",
  currentModel: "gpt-4o",
  thinkingMode: "none",
  activeChatId: null,
  isSettingsOpen: false,

  snippingMode: false,
  activeBbox: null,
  quoteToAppend: null,
  pendingSnippets: [],

  setActiveProjectId: (id) => set({ activeProjectId: id, activeChatId: null }),
  setActiveProject: (project) =>
    set({
      activeProject: project,
      activeProjectId: project ? project.project_id : null,
      activeDocId: project ? project.doc_id : null,
    }),
  setActiveDocId: (docId) => set({ activeDocId: docId }),
  setActivePage: (page) => set({ activePage: page }),
  setTotalPages: (total) => set({ totalPages: Math.max(1, total) }),
  setScale: (scale) => set({ scale: Math.max(0.4, Math.min(3.0, scale)) }),
  setChatScope: (scope) => set({ chatScope: scope }),
  setCurrentProvider: (provider) => set({ currentProvider: provider }),
  setCurrentModel: (model) => set({ currentModel: model }),
  setThinkingMode: (mode) => set({ thinkingMode: mode }),
  setActiveChatId: (chatId) => set({ activeChatId: chatId }),
  setIsSettingsOpen: (open) => set({ isSettingsOpen: open }),

  setSnippingMode: (active) => set({ snippingMode: active }),
  setActiveBbox: (bbox) => set({ activeBbox: bbox }),
  setQuoteToAppend: (quote) => set({ quoteToAppend: quote }),
  consumeQuoteToAppend: () => {
    const q = get().quoteToAppend;
    if (q) {
      set({ quoteToAppend: null });
    }
    return q;
  },
  addPendingSnippet: (snippet) =>
    set((state) => ({ pendingSnippets: [...state.pendingSnippets, snippet] })),
  removePendingSnippet: (id) =>
    set((state) => {
      const target = state.pendingSnippets.find((s) => s.id === id);
      if (target?.previewUrl) {
        URL.revokeObjectURL(target.previewUrl);
      }
      return {
        pendingSnippets: state.pendingSnippets.filter((s) => s.id !== id),
      };
    }),
  clearPendingSnippets: () => {
    get().pendingSnippets.forEach((s) => {
      if (s.previewUrl) URL.revokeObjectURL(s.previewUrl);
    });
    set({ pendingSnippets: [] });
  },

  jumpToPage: (pageNumber, bbox = null) =>
    set((state) => ({
      activePage: Math.min(Math.max(1, pageNumber), state.totalPages),
      activeBbox: bbox || null,
    })),
}));
