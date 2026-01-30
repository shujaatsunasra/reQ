"use client";

import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Send, ArrowRight, Waves, Sparkles, Map, BarChart2, Globe } from "lucide-react";
import { useAppStore } from "@/store/app-store";
import { toast } from "sonner";

const PROMPTS = [
  { icon: Globe, label: "Show all floats", query: "Show all ARGO floats on the map" },
  { icon: BarChart2, label: "Temperature trends", query: "Show temperature trends in the Arabian Sea" },
  { icon: Map, label: "Compare regions", query: "Compare salinity profiles between Pacific and Atlantic" },
  { icon: Waves, label: "Find anomalies", query: "Find temperature anomalies in the dataset" },
];

interface LandingPageProps {
  onQuerySubmit: (query: string) => void;
}

export function LandingPage({ onQuerySubmit }: LandingPageProps) {
  const { groqApiKey, huggingfaceApiKey, setGroqApiKey, setHuggingfaceApiKey } = useAppStore();
  const [query, setQuery] = useState("");
  const [showApiSetup, setShowApiSetup] = useState(false);
  const [tempGroqKey, setTempGroqKey] = useState("");
  const [inputFocused, setInputFocused] = useState(false);

  // User has at least one API key configured
  const hasApiKey = groqApiKey.length > 0 || huggingfaceApiKey.length > 0;

  const handleSubmit = useCallback(() => {
    if (!query.trim()) return;

    if (!hasApiKey) {
      setShowApiSetup(true);
      return;
    }

    onQuerySubmit(query.trim());
  }, [query, hasApiKey, onQuerySubmit]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  const handlePromptClick = useCallback((prompt: string) => {
    if (!hasApiKey) {
      setShowApiSetup(true);
      return;
    }
    onQuerySubmit(prompt);
  }, [hasApiKey, onQuerySubmit]);

  const handleSaveKey = useCallback(() => {
    if (tempGroqKey.trim()) {
      setGroqApiKey(tempGroqKey.trim());
      setShowApiSetup(false);
      toast.success("API key saved! You can now start exploring.");
    }
  }, [tempGroqKey, setGroqApiKey]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-background via-background to-muted/30 flex flex-col overflow-hidden">
      {/* Minimal Header */}
      <header className="flex items-center justify-between px-6 h-16">
        <div className="flex items-center gap-2">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 300, damping: 20 }}
            className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center shadow-xl shadow-primary/30"
          >
            <Sparkles className="w-4.5 h-4.5 text-primary-foreground" />
          </motion.div>
          <motion.span
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="font-extrabold text-2xl tracking-tight"
          >
            FloatChat
          </motion.span>
        </div>

        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          onClick={() => setShowApiSetup(true)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${hasApiKey
            ? "bg-green-500/10 text-green-600 dark:text-green-400"
            : "bg-amber-500/10 text-amber-600 dark:text-amber-400 hover:bg-amber-500/20"
            }`}
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
          </svg>
          {hasApiKey ? "Configured" : "Add API Key"}
        </motion.button>
      </header>

      {/* Main content */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 pb-24">
        {/* Hero */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] }}
          className="text-center mb-10"
        >
          {/* Animated badge */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-primary/10 to-primary/5 text-primary text-sm font-medium mb-8 border border-primary/10"
          >
            <motion.div
              animate={{ rotate: [0, 10, -10, 0] }}
              transition={{ duration: 2, repeat: Infinity, repeatDelay: 3 }}
            >
              <Waves className="w-4 h-4" />
            </motion.div>
            Powered by ARGO Float Data
          </motion.div>

          <h1 className="text-5xl md:text-7xl font-black mb-6 tracking-tight text-foreground">
            Explore Ocean Data
          </h1>
          <p className="text-lg text-muted-foreground max-w-lg mx-auto leading-relaxed font-medium">
            Ask questions about oceanographic data using natural language.
            Get instant maps, visualizations, and analysis.
          </p>
        </motion.div>

        {/* Search input with Gemini-style animated gradient border */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15 }}
          className="w-full max-w-2xl mb-8"
        >
          <div className={`relative group transition-all duration-500 ${inputFocused ? 'scale-[1.01]' : ''}`}>
            {/* Animated gradient border - only visible on focus */}
            <div
              className={`absolute -inset-[2px] rounded-2xl transition-opacity duration-300 overflow-hidden ${inputFocused ? 'opacity-100' : 'opacity-0'
                }`}
            >
              <div
                className="absolute inset-0"
                style={{
                  background: 'conic-gradient(from 0deg, #4285f4, #34a853, #fbbc04, #ea4335, #4285f4)',
                  animation: 'spin 3s linear infinite',
                }}
              />
            </div>

            {/* Inner container */}
            <div className="relative bg-card rounded-2xl">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => setInputFocused(true)}
                onBlur={() => setInputFocused(false)}
                placeholder="Ask about ARGO floats, temperature, salinity..."
                className={`w-full px-6 py-5 pr-20 bg-card rounded-2xl text-base font-medium focus:outline-none transition-all duration-300 ${inputFocused
                    ? 'border-transparent'
                    : 'border-2 border-border hover:border-primary/30'
                  }`}
              />
              <motion.button
                onClick={handleSubmit}
                disabled={!query.trim()}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="absolute right-4 top-1/2 -translate-y-1/2 p-3 bg-primary text-primary-foreground rounded-xl hover:bg-primary/90 disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-lg shadow-primary/20"
              >
                <ArrowRight className="w-5 h-5" />
              </motion.button>
            </div>

            {/* Glow effect underneath */}
            <div
              className={`absolute inset-x-8 -bottom-3 h-10 rounded-full blur-2xl transition-opacity duration-500 ${inputFocused ? 'opacity-50' : 'opacity-0'
                }`}
              style={{
                background: 'linear-gradient(90deg, #4285f4, #ea4335, #fbbc04, #34a853)',
              }}
            />
          </div>

          {!hasApiKey && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
              className="text-xs text-amber-500 mt-4 text-center"
            >
              Add your API key to get started →
            </motion.p>
          )}

          {/* Animation keyframes */}
          <style jsx global>{`
            @keyframes spin {
              from { transform: rotate(0deg); }
              to { transform: rotate(360deg); }
            }
          `}</style>
        </motion.div>

        {/* Quick prompts */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: 0.25 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-3 max-w-2xl w-full"
        >
          {PROMPTS.map((prompt, i) => (
            <motion.button
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 + i * 0.05 }}
              onClick={() => handlePromptClick(prompt.query)}
              whileHover={{ scale: 1.02, y: -2 }}
              whileTap={{ scale: 0.98 }}
              className="group flex flex-col items-center gap-3 p-5 bg-card hover:bg-white border-2 border-border hover:border-primary/30 rounded-xl text-sm transition-all shadow-md hover:shadow-xl"
            >
              <div className="w-10 h-10 rounded-lg bg-muted group-hover:bg-primary/10 flex items-center justify-center transition-colors">
                <prompt.icon className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" />
              </div>
              <span className="text-sm font-semibold text-muted-foreground group-hover:text-foreground transition-colors text-center">
                {prompt.label}
              </span>
            </motion.button>
          ))}
        </motion.div>
      </main>

      {/* Footer */}
      <footer className="py-4 text-center text-xs text-muted-foreground">
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          Built for oceanographers, by AI
        </motion.p>
      </footer>

      {/* API Setup Modal */}
      {showApiSetup && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowApiSetup(false)}
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
              <div className="flex items-center gap-3 mb-5">
                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold">Quick Setup</h2>
                  <p className="text-xs text-muted-foreground">Add your API key to start exploring</p>
                </div>
              </div>

              <div className="mb-5">
                <label className="text-sm font-medium mb-2 block">
                  Groq API Key <span className="text-xs text-muted-foreground">(free)</span>
                </label>
                <input
                  type="password"
                  value={tempGroqKey}
                  onChange={(e) => setTempGroqKey(e.target.value)}
                  placeholder="gsk_..."
                  className="w-full px-4 py-3 bg-muted rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                  autoFocus
                />
                <a
                  href="https://console.groq.com/keys"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-primary hover:underline mt-2 inline-block"
                >
                  Get your free API key from Groq Console →
                </a>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => setShowApiSetup(false)}
                  className="flex-1 px-4 py-3 border rounded-xl text-sm font-medium hover:bg-muted transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveKey}
                  disabled={!tempGroqKey.trim()}
                  className="flex-1 px-4 py-3 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  Save & Continue
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </div>
  );
}
