"use client";

import { useCallback, lazy, Suspense, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { LandingPage } from "@/components/landing/landing-page";
import { Sidebar } from "@/components/layout/sidebar";
import { useAppStore } from "@/store/app-store";

// Lazy load the unified chat with prefetch
const UnifiedChat = lazy(() => import("@/components/views/unified-chat"));

// Elegant loading fallback with micro-animations
function ViewLoading() {
  return (
    <div className="flex items-center justify-center h-screen bg-background">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex flex-col items-center gap-4"
      >
        {/* Animated logo */}
        <motion.div
          className="relative"
          animate={{ rotate: 360 }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
        >
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center">
            <motion.div
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="w-6 h-6 rounded-lg bg-primary/30"
            />
          </div>
        </motion.div>

        {/* Loading dots */}
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-2 h-2 rounded-full bg-primary"
              animate={{
                scale: [1, 1.3, 1],
                opacity: [0.5, 1, 0.5]
              }}
              transition={{
                duration: 0.8,
                repeat: Infinity,
                delay: i * 0.15
              }}
            />
          ))}
        </div>

        <p className="text-sm text-muted-foreground">Loading Vortex...</p>
      </motion.div>
    </div>
  );
}

export default function Home() {
  const {
    hasStartedSession,
    setHasStartedSession,
    groqApiKey,
    huggingfaceApiKey,
    setGroqApiKey,
    setHuggingfaceApiKey
  } = useAppStore();

  const [pendingQuery, setPendingQuery] = useState<string | null>(null);
  const [showApiModal, setShowApiModal] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [tempGroqKey, setTempGroqKey] = useState("");
  const [tempHfKey, setTempHfKey] = useState("");
  const [showGroqKey, setShowGroqKey] = useState(false);
  const [showHfKey, setShowHfKey] = useState(false);

  // Preload view immediately on mount
  useEffect(() => {
    const preload = async () => {
      await import("@/components/views/unified-chat");
    };
    preload();
  }, []);

  useEffect(() => {
    setTempGroqKey(groqApiKey);
    setTempHfKey(huggingfaceApiKey);
  }, [groqApiKey, huggingfaceApiKey]);

  const saveApiKeys = useCallback(() => {
    if (tempGroqKey.trim()) setGroqApiKey(tempGroqKey.trim());
    if (tempHfKey.trim()) setHuggingfaceApiKey(tempHfKey.trim());
    setShowApiModal(false);
    toast.success("API keys saved");
  }, [tempGroqKey, tempHfKey, setGroqApiKey, setHuggingfaceApiKey]);

  const handleQuerySubmit = useCallback(
    (query: string) => {
      setHasStartedSession(true);
      setPendingQuery(query);
    },
    [setHasStartedSession]
  );

  const hasApiKey = groqApiKey.length > 0 || huggingfaceApiKey.length > 0;
  const hasGroqKey = groqApiKey.length > 0;
  const hasHfKey = huggingfaceApiKey.length > 0;

  // Show landing page if no session started
  if (!hasStartedSession) {
    return <LandingPage onQuerySubmit={handleQuerySubmit} />;
  }

  // Show unified chat view
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key="chat"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="h-screen flex"
      >
        {/* Sidebar */}
        <Sidebar
          isOpen={sidebarOpen}
          onToggle={() => setSidebarOpen(!sidebarOpen)}
          onNewChat={() => {
            setHasStartedSession(false);
            setPendingQuery(null);
          }}
          onOpenSettings={() => setShowApiModal(true)}
        />

        {/* Main Content */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Header */}
          <header className="flex items-center justify-between px-4 h-14 border-b bg-background/80 backdrop-blur-md sticky top-0 z-40">
            <motion.button
              onClick={() => setHasStartedSession(false)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="flex items-center gap-2 hover:opacity-80 transition-opacity"
            >
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center shadow-sm">
                <svg className="w-4 h-4 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                </svg>
              </div>
              <span className="font-semibold text-lg tracking-tight">Vortex</span>
            </motion.button>

            <div className="flex items-center gap-2">
              {/* API Key status */}
              <motion.button
                onClick={() => setShowApiModal(true)}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${hasApiKey
                  ? "bg-green-500/10 text-green-600 dark:text-green-400 hover:bg-green-500/20"
                  : "bg-amber-500/10 text-amber-600 dark:text-amber-400 hover:bg-amber-500/20"
                  }`}
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                </svg>
                {hasApiKey ? (
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : "Add Key"}
              </motion.button>

              {/* New chat button */}
              <motion.button
                onClick={() => {
                  setHasStartedSession(false);
                  setPendingQuery(null);
                }}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="p-2 hover:bg-muted rounded-lg transition-colors"
                title="New Chat"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </motion.button>
            </div>
          </header>

          <Suspense fallback={<ViewLoading />}>
            <div className="flex-1 min-h-0">
              <UnifiedChat initialQuery={pendingQuery || undefined} />
            </div>
          </Suspense>
        </div>

        {/* API Key Modal */}
        <AnimatePresence>
          {showApiModal && (
            <>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setShowApiModal(false)}
                className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
              />

              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                transition={{ type: "spring", stiffness: 300, damping: 25 }}
                className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none"
              >
                <div className="bg-card border rounded-2xl shadow-2xl p-6 w-full max-w-md pointer-events-auto">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold">API Configuration</h2>
                    <button
                      onClick={() => setShowApiModal(false)}
                      className="p-1 hover:bg-muted rounded-lg transition-colors"
                    >
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>

                  <p className="text-sm text-muted-foreground mb-5">
                    Configure your LLM providers. Groq is the primary (fast & free).
                    HuggingFace is used as automatic fallback.
                  </p>

                  {/* Groq API Key */}
                  <div className="mb-5">
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-green-500"></span>
                        Groq API Key
                        <span className="text-xs text-muted-foreground">(Primary)</span>
                      </label>
                      {hasGroqKey && (
                        <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </div>
                    <div className="relative">
                      <input
                        type={showGroqKey ? "text" : "password"}
                        value={tempGroqKey}
                        onChange={(e) => setTempGroqKey(e.target.value)}
                        placeholder="gsk_..."
                        className="w-full px-4 py-3 pr-12 bg-muted rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                      />
                      <button
                        onClick={() => setShowGroqKey(!showGroqKey)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-background rounded transition-colors"
                      >
                        <svg className="w-4 h-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={showGroqKey ? "M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" : "M15 12a3 3 0 11-6 0 3 3 0 016 0zM2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"} />
                        </svg>
                      </button>
                    </div>
                    <a
                      href="https://console.groq.com/keys"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-primary hover:underline mt-1.5 inline-block"
                    >
                      Get free Groq API key →
                    </a>
                  </div>

                  {/* HuggingFace API Key */}
                  <div className="mb-5">
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                        HuggingFace API Key
                        <span className="text-xs text-muted-foreground">(Fallback)</span>
                      </label>
                      {hasHfKey && (
                        <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </div>
                    <div className="relative">
                      <input
                        type={showHfKey ? "text" : "password"}
                        value={tempHfKey}
                        onChange={(e) => setTempHfKey(e.target.value)}
                        placeholder="hf_..."
                        className="w-full px-4 py-3 pr-12 bg-muted rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                      />
                      <button
                        onClick={() => setShowHfKey(!showHfKey)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-background rounded transition-colors"
                      >
                        <svg className="w-4 h-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={showHfKey ? "M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" : "M15 12a3 3 0 11-6 0 3 3 0 016 0zM2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"} />
                        </svg>
                      </button>
                    </div>
                    <a
                      href="https://huggingface.co/settings/tokens"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-primary hover:underline mt-1.5 inline-block"
                    >
                      Get free HuggingFace token →
                    </a>
                  </div>

                  {/* Provider Status */}
                  <div className="bg-muted/50 rounded-xl p-3 mb-5">
                    <p className="text-xs font-medium mb-2 text-center">Provider Hierarchy</p>
                    <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
                      <span className={`px-2 py-1 rounded ${tempGroqKey.trim() ? 'bg-green-500/20 text-green-600 dark:text-green-400' : 'bg-muted'}`}>
                        1. Groq {tempGroqKey.trim() ? '✓' : '○'}
                      </span>
                      <span>→</span>
                      <span className={`px-2 py-1 rounded ${tempHfKey.trim() ? 'bg-green-500/20 text-green-600 dark:text-green-400' : 'bg-muted'}`}>
                        2. HuggingFace {tempHfKey.trim() ? '✓' : '○'}
                      </span>
                    </div>
                  </div>

                  <motion.button
                    onClick={saveApiKeys}
                    disabled={!tempGroqKey.trim() && !tempHfKey.trim()}
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                    className="w-full px-4 py-3 bg-primary text-primary-foreground rounded-xl font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  >
                    Save Configuration
                  </motion.button>

                  {hasApiKey && (
                    <p className="text-xs text-green-600 dark:text-green-400 mt-3 flex items-center justify-center gap-1">
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      {hasGroqKey && hasHfKey ? 'Both providers configured' : hasGroqKey ? 'Groq configured' : 'HuggingFace configured'}
                    </p>
                  )}
                </div>
              </motion.div>
            </>
          )}
        </AnimatePresence>
      </motion.div>
    </AnimatePresence>
  );
}
