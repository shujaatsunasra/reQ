import { create } from "zustand";
import { persist } from "zustand/middleware";

export type LLMProvider = "groq" | "huggingface";  // Multi-provider with failover

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  metadata?: {
    confidence?: number;
    executionTime?: number;
    queryType?: string;
    rowsReturned?: number;
    cached?: boolean;
  };
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

interface QueryResult {
  id: string;
  data: any;
  visualizations: any[];
  confidence: number;
  executionTime: number;
  timestamp: Date;
}

interface AppState {
  // UI State
  sidebarOpen: boolean;
  theme: "light" | "dark" | "system";
  hasStartedSession: boolean;

  // Conversation State
  conversations: Conversation[];
  activeConversationId: string | null;
  isLoading: boolean;

  // Results State
  currentResult: QueryResult | null;
  resultHistory: QueryResult[];

  // Settings
  llmProvider: LLMProvider;
  groqApiKey: string;
  huggingfaceApiKey: string;
  autoVisualize: boolean;
  showConfidence: boolean;

  // Actions
  toggleSidebar: () => void;
  setTheme: (theme: "light" | "dark" | "system") => void;
  setHasStartedSession: (value: boolean) => void;

  // Conversation Actions
  createConversation: () => string;
  setActiveConversation: (id: string) => void;
  addMessage: (conversationId: string, message: Omit<Message, "id" | "timestamp">) => void;
  deleteConversation: (id: string) => void;

  // Results Actions
  setCurrentResult: (result: QueryResult | null) => void;
  addToResultHistory: (result: QueryResult) => void;

  // Settings Actions
  setLLMProvider: (provider: LLMProvider) => void;
  setGroqApiKey: (key: string) => void;
  setHuggingfaceApiKey: (key: string) => void;
  setAutoVisualize: (value: boolean) => void;
  setShowConfidence: (value: boolean) => void;
  setIsLoading: (value: boolean) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Initial UI State
      sidebarOpen: true,
      theme: "system",
      hasStartedSession: false,

      // Initial Conversation State
      conversations: [],
      activeConversationId: null,
      isLoading: false,

      // Initial Results State
      currentResult: null,
      resultHistory: [],

      // Initial Settings
      llmProvider: "groq",
      groqApiKey: "",
      huggingfaceApiKey: "",
      autoVisualize: true,
      showConfidence: true,

      // UI Actions
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setTheme: (theme) => set({ theme }),
      setHasStartedSession: (value) => set({ hasStartedSession: value }),

      // Conversation Actions
      createConversation: () => {
        const id = crypto.randomUUID();
        const newConversation: Conversation = {
          id,
          title: "New Conversation",
          messages: [],
          createdAt: new Date(),
          updatedAt: new Date(),
        };
        set((state) => ({
          conversations: [newConversation, ...state.conversations],
          activeConversationId: id,
        }));
        return id;
      },

      setActiveConversation: (id) => set({ activeConversationId: id }),

      addMessage: (conversationId, message) => {
        const newMessage: Message = {
          ...message,
          id: crypto.randomUUID(),
          timestamp: new Date(),
        };
        set((state) => ({
          conversations: state.conversations.map((conv) =>
            conv.id === conversationId
              ? {
                  ...conv,
                  messages: [...conv.messages, newMessage],
                  updatedAt: new Date(),
                  title:
                    conv.messages.length === 0 && message.role === "user"
                      ? message.content.slice(0, 50)
                      : conv.title,
                }
              : conv
          ),
        }));
      },

      deleteConversation: (id) =>
        set((state) => ({
          conversations: state.conversations.filter((c) => c.id !== id),
          activeConversationId:
            state.activeConversationId === id
              ? state.conversations[0]?.id || null
              : state.activeConversationId,
        })),

      // Results Actions
      setCurrentResult: (result) => set({ currentResult: result }),
      addToResultHistory: (result) =>
        set((state) => ({
          resultHistory: [result, ...state.resultHistory].slice(0, 50),
        })),

      // Settings Actions
      setLLMProvider: (provider) => set({ llmProvider: provider }),
      setGroqApiKey: (key) => set({ groqApiKey: key }),
      setHuggingfaceApiKey: (key) => set({ huggingfaceApiKey: key }),
      setAutoVisualize: (value) => set({ autoVisualize: value }),
      setShowConfidence: (value) => set({ showConfidence: value }),
      setIsLoading: (value) => set({ isLoading: value }),
    }),
    {
      name: "floatchat-storage",
      partialize: (state) => ({
        theme: state.theme,
        llmProvider: state.llmProvider,
        groqApiKey: state.groqApiKey,
        huggingfaceApiKey: state.huggingfaceApiKey,
        autoVisualize: state.autoVisualize,
        showConfidence: state.showConfidence,
        conversations: state.conversations,
      }),
    }
  )
);
