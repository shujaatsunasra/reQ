"use client";

import { useState, useRef, useCallback, useEffect, useMemo } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import dynamic from "next/dynamic";
import {
  Send,
  Loader2,
  Sparkles,
  Copy,
  RotateCcw,
  Map,
  BarChart2,
  Table2,
  X,
  ChevronDown,
  ChevronUp,
  Maximize2,
  Minimize2,
  Download,
  Filter,
  Layers,
  MapPin,
  Thermometer,
  Droplets,
  Calendar,
  Activity,
  CheckCircle2,
  AlertCircle,
  Database,
  Clock,
  Gauge,
  Globe,
  RefreshCw,
  Plus,
  Trash2,
  ArrowRight,
  Command,
  MessageSquare,
  PanelRightOpen,
  PanelRightClose,
  LineChart,
  TrendingUp,
  Workflow,
  Check,
  ImageIcon,
  FileJson,
  GripVertical,
  ArrowUp,
} from "lucide-react";
import { useAppStore } from "@/store/app-store";
import { api } from "@/lib/api";
import { ResizablePanel } from "@/components/ui/resizable-panel";
import { ExportDropdown } from "@/components/ui/export-dropdown";

// Dynamic imports for visualizations
const MapContainer = dynamic(
  () => import("react-leaflet").then((mod) => mod.MapContainer),
  { ssr: false }
);
const TileLayer = dynamic(
  () => import("react-leaflet").then((mod) => mod.TileLayer),
  { ssr: false }
);
const CircleMarker = dynamic(
  () => import("react-leaflet").then((mod) => mod.CircleMarker),
  { ssr: false }
);
const Popup = dynamic(
  () => import("react-leaflet").then((mod) => mod.Popup),
  { ssr: false }
);
const Polyline = dynamic(
  () => import("react-leaflet").then((mod) => mod.Polyline),
  { ssr: false }
);
const Tooltip = dynamic(
  () => import("react-leaflet").then((mod) => mod.Tooltip),
  { ssr: false }
);

// Map bounds handler for auto-centering
const MapBoundsHandler = dynamic(
  () => import("@/components/visualizations/map-bounds-handler").then((mod) => mod.MapBoundsHandler),
  { ssr: false }
);

// Dynamic imports for visualization components
const HovmollerDiagram = dynamic(
  () => import("@/components/visualizations/hovmoller-diagram").then((mod) => mod.HovmollerDiagram),
  { ssr: false, loading: () => <VizLoadingPlaceholder /> }
);
const GeospatialHeatmap = dynamic(
  () => import("@/components/visualizations/geospatial-heatmap").then((mod) => mod.GeospatialHeatmap),
  { ssr: false, loading: () => <VizLoadingPlaceholder /> }
);
const QCDashboard = dynamic(
  () => import("@/components/visualizations/qc-dashboard").then((mod) => mod.QCDashboard),
  { ssr: false, loading: () => <VizLoadingPlaceholder /> }
);
const TSDiagram = dynamic(
  () => import("@/components/visualizations/ts-diagram").then((mod) => mod.TSDiagram),
  { ssr: false, loading: () => <VizLoadingPlaceholder /> }
);
const VerticalProfile = dynamic(
  () => import("@/components/visualizations/vertical-profile").then((mod) => mod.VerticalProfile),
  { ssr: false, loading: () => <VizLoadingPlaceholder /> }
);
const TimeSeriesChart = dynamic(
  () => import("@/components/visualizations/time-series-chart").then((mod) => mod.TimeSeriesChart),
  { ssr: false, loading: () => <VizLoadingPlaceholder /> }
);
const TrajectoryPlot = dynamic(
  () => import("@/components/visualizations/trajectory-plot").then((mod) => mod.TrajectoryPlot),
  { ssr: false, loading: () => <VizLoadingPlaceholder /> }
);

// Loading placeholder for visualizations
function VizLoadingPlaceholder() {
  return (
    <div className="flex items-center justify-center h-64 bg-gradient-to-br from-muted/30 via-muted/10 to-muted/30 rounded-xl border border-border/50 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent animate-shimmer" />
      <div className="relative flex flex-col items-center gap-3 text-muted-foreground">
        <div className="relative">
          <Loader2 className="w-8 h-8 animate-spin text-primary/50" />
          <div className="absolute inset-0 blur-xl bg-primary/20 animate-pulse" />
        </div>
        <span className="text-xs font-medium">Loading visualization...</span>
      </div>
    </div>
  );
}

// Types
interface FloatData {
  id: string;
  lat: number;
  lng: number;
  temp?: number;
  salinity?: number;
  depth?: number;
  date?: string;
  qc_flag?: number;
  qc_temp?: number;
  qc_psal?: number;
  qc_pres?: number;
  data_mode?: string;
  // Anomaly detection fields
  is_anomaly?: boolean;
  anomaly_type?: 'temperature' | 'salinity' | 'both' | null;
  anomaly_score?: number; // 0-1 score for severity
}

interface MessageArtifact {
  id: string;
  type: 'map' | 'chart' | 'table' | 'visualization';
  title: string;
  data: any;
  visualization?: 'heatmap' | 'hovmoller' | 'ts' | 'profile' | 'qc' | 'timeseries' | 'trajectory';
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  isTyping?: boolean;
  artifacts?: MessageArtifact[];
  metadata?: {
    confidence?: number;
    executionTime?: number;
    rowsReturned?: number;
    cached?: boolean;
  };
}

interface UnifiedChatProps {
  isLoading?: boolean;
  initialQuery?: string;
}

// Suggestion prompts
const QUICK_PROMPTS = [
  { label: "Show all floats", query: "Show all ARGO floats on the map" },
  { label: "Temperature trends", query: "Show temperature trends in the Arabian Sea" },
  { label: "Recent profiles", query: "Show profiles from the last 30 days" },
  { label: "Compare regions", query: "Compare temperature between Arabian Sea and Bay of Bengal" },
];

// Detect what visualization is needed from the query
function detectVisualizationNeed(query: string, response: any): { needsMap: boolean; needsViz: boolean; vizType?: string } {
  const lowerQuery = query.toLowerCase();
  const lowerResponse = (response?.response || '').toLowerCase();

  // Map keywords
  const mapKeywords = ['show floats', 'on the map', 'location', 'where', 'region', 'area', 'ocean', 'sea', 'trajectory', 'path'];
  const needsMap = mapKeywords.some(k => lowerQuery.includes(k) || lowerResponse.includes(k));

  // Visualization keywords
  if (lowerQuery.includes('trajectory') || lowerQuery.includes('path') || lowerQuery.includes('movement') || lowerQuery.includes('float track')) {
    return { needsMap, needsViz: true, vizType: 'trajectory' };
  }
  if (lowerQuery.includes('hovmöller') || lowerQuery.includes('hovmoller') || lowerQuery.includes('depth-time')) {
    return { needsMap, needsViz: true, vizType: 'hovmoller' };
  }
  if (lowerQuery.includes('t-s') || lowerQuery.includes('ts diagram') || lowerQuery.includes('temperature-salinity')) {
    return { needsMap, needsViz: true, vizType: 'ts' };
  }
  if (lowerQuery.includes('quality') || lowerQuery.includes('qc') || lowerQuery.includes('flag')) {
    return { needsMap, needsViz: true, vizType: 'qc' };
  }
  if (lowerQuery.includes('heatmap') || lowerQuery.includes('heat map') || lowerQuery.includes('distribution')) {
    return { needsMap: true, needsViz: true, vizType: 'heatmap' };
  }
  if (lowerQuery.includes('profile') || lowerQuery.includes('vertical')) {
    return { needsMap, needsViz: true, vizType: 'profile' };
  }
  if (lowerQuery.includes('time series') || lowerQuery.includes('trend') || lowerQuery.includes('over time')) {
    return { needsMap, needsViz: true, vizType: 'timeseries' };
  }
  if (lowerQuery.includes('compare') || lowerQuery.includes('comparison')) {
    return { needsMap, needsViz: true, vizType: 'timeseries' };
  }

  // If data returned, show map by default
  const hasData = response?.data?.profiles?.length > 0;
  return { needsMap: needsMap || hasData, needsViz: false };
}

export default function UnifiedChat({ isLoading: externalLoading, initialQuery }: UnifiedChatProps) {
  const prefersReducedMotion = useReducedMotion();
  const {
    conversations,
    activeConversationId,
    createConversation,
    addMessage: addStoreMessage,
    setCurrentResult,
    addToResultHistory,
    groqApiKey,
    huggingfaceApiKey,
  } = useAppStore();

  // Local state
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [artifactPanelOpen, setArtifactPanelOpen] = useState(false);
  const [activeArtifact, setActiveArtifact] = useState<MessageArtifact | null>(null);
  const [artifactFullscreen, setArtifactFullscreen] = useState(false);
  const [floatData, setFloatData] = useState<FloatData[]>([]);
  const [selectedFloat, setSelectedFloat] = useState<FloatData | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [inputFocused, setInputFocused] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const initialQueryProcessed = useRef(false);

  // Initialize
  useEffect(() => {
    setMapReady(true);
  }, []);

  // Auto-scroll
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: prefersReducedMotion ? "auto" : "smooth" });
    }
  }, [messages, prefersReducedMotion]);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 150)}px`;
    }
  }, [input]);

  // Process initial query (with guard against StrictMode double execution)
  useEffect(() => {
    if (initialQuery && messages.length === 0 && !initialQueryProcessed.current) {
      initialQueryProcessed.current = true;
      handleQuerySubmit(initialQuery);
    }
  }, [initialQuery]);

  // Hide suggestions after first message
  useEffect(() => {
    if (messages.length > 0) {
      setShowSuggestions(false);
    }
  }, [messages.length]);

  // Query mutation
  const queryMutation = useMutation({
    mutationFn: async (query: string) => {
      // Build conversation history from previous messages (exclude typing indicators)
      const history = messages
        .filter(m => !m.isTyping && m.content)
        .slice(-10) // Keep last 10 messages for context
        .map(m => ({
          role: m.role as 'user' | 'assistant',
          content: m.content
        }));

      return api.query({
        query,
        groq_api_key: groqApiKey || undefined,
        huggingface_api_key: huggingfaceApiKey || undefined,
        conversation_history: history.length > 0 ? history : undefined,
        options: {
          include_visualizations: true,
        }
      });
    },
    onSuccess: (data, query) => {
      // Process float data if returned
      let artifacts: MessageArtifact[] = [];

      if (data.data?.profiles && data.data.profiles.length > 0) {
        const profiles = data.data.profiles.map((p: any) => ({
          id: p.float_id || p.id,
          lat: p.latitude || p.lat,
          lng: p.longitude || p.lng || p.lon,
          temp: p.temperature,
          salinity: p.salinity,
          depth: p.depth || p.depth_max,
          date: p.date || p.timestamp,
          qc_flag: p.qc_flag ?? p.qc_temp,
          qc_temp: p.qc_temp,
          qc_psal: p.qc_psal,
          qc_pres: p.qc_pres,
          data_mode: p.data_mode,
        }));
        setFloatData(profiles);

        // Detect what visualization to show
        const vizNeeds = detectVisualizationNeed(query, data);

        if (vizNeeds.needsMap) {
          artifacts.push({
            id: crypto.randomUUID(),
            type: 'map',
            title: `${profiles.length} ARGO Floats`,
            data: profiles,
          });
        }

        if (vizNeeds.needsViz && vizNeeds.vizType) {
          artifacts.push({
            id: crypto.randomUUID(),
            type: 'visualization',
            title: vizNeeds.vizType === 'timeseries' ? 'Time Series' :
              vizNeeds.vizType === 'ts' ? 'T-S Diagram' :
                vizNeeds.vizType === 'profile' ? 'Vertical Profiles' :
                  vizNeeds.vizType === 'qc' ? 'Quality Control' :
                    vizNeeds.vizType === 'hovmoller' ? 'Hovmöller Diagram' :
                      vizNeeds.vizType === 'trajectory' ? 'Float Trajectory' :
                        'Heatmap',
            data: profiles,
            visualization: vizNeeds.vizType as any,
          });
        }
      }

      // Add assistant message
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.response || "Analysis complete.",
        timestamp: new Date(),
        artifacts: artifacts.length > 0 ? artifacts : undefined,
        metadata: {
          confidence: data.confidence,
          executionTime: data.execution_time_ms,
          rowsReturned: data.data?.profiles?.length || 0,
          cached: data.cache_hit,
        },
      };

      setMessages(prev => prev.map(m =>
        m.isTyping ? assistantMessage : m
      ));

      // Persist assistant message to store
      if (activeConversationId) {
        addStoreMessage(activeConversationId, {
          role: "assistant",
          content: data.response || "Analysis complete."
        });
      }

      // Auto-open artifact panel if we have artifacts
      if (artifacts.length > 0) {
        setActiveArtifact(artifacts[0]);
        setArtifactPanelOpen(true);
      }

      // Store results
      if (data.data || data.visualizations) {
        const result = {
          id: crypto.randomUUID(),
          data: data.data,
          visualizations: data.visualizations || [],
          confidence: data.confidence,
          executionTime: data.execution_time_ms,
          timestamp: new Date(),
        };
        setCurrentResult(result);
        addToResultHistory(result);
      }

      setIsLoading(false);
    },
    onError: (error) => {
      setMessages(prev => prev.map(m =>
        m.isTyping ? {
          id: crypto.randomUUID(),
          role: "assistant" as const,
          content: `I encountered an issue: ${error instanceof Error ? error.message : "Please try again."}`,
          timestamp: new Date(),
        } : m
      ));
      setIsLoading(false);
      toast.error("Query failed");
    },
  });

  const handleQuerySubmit = useCallback((query: string) => {
    if (!query.trim() || isLoading) return;

    // Create conversation if none active
    let convId = activeConversationId;
    if (!convId) {
      convId = createConversation();
    }

    // Add user message
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: query.trim(),
      timestamp: new Date(),
    };

    // Persist user message to store
    addStoreMessage(convId, { role: "user", content: query.trim() });

    // Add typing indicator
    const typingMessage: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      timestamp: new Date(),
      isTyping: true,
    };

    setMessages(prev => [...prev, userMessage, typingMessage]);
    setIsLoading(true);
    setInput("");

    queryMutation.mutate(query.trim());
  }, [isLoading, queryMutation, activeConversationId, createConversation, addStoreMessage]);

  const handleSubmit = useCallback(() => {
    handleQuerySubmit(input);
  }, [input, handleQuerySubmit]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  const handleCopy = useCallback((content: string) => {
    navigator.clipboard.writeText(content);
    toast.success("Copied to clipboard");
  }, []);

  const handleRetry = useCallback((messageContent: string) => {
    // Find the user message before this assistant message
    const userMessages = messages.filter(m => m.role === 'user');
    const lastUserMessage = userMessages[userMessages.length - 1];
    if (lastUserMessage) {
      handleQuerySubmit(lastUserMessage.content);
    }
  }, [messages, handleQuerySubmit]);

  // Get marker color based on temperature - blue/pink palette
  const getMarkerColor = useCallback((float: FloatData): string => {
    // Blue/pink palette like reference design
    if (float.is_anomaly) {
      return '#ff6b8a'; // Pink for anomalies
    }
    if (float.temp !== undefined) {
      if (float.temp < 15) return '#4da6ff'; // Cool - blue
      if (float.temp < 22) return '#b388ff'; // Medium - purple  
      return '#ff6b8a'; // Warm - pink
    }
    return '#4da6ff'; // Default blue
  }, []);

  const loading = isLoading || externalLoading;

  // Animation variants
  const messageVariants = {
    initial: { opacity: 0, y: 20, scale: 0.98 },
    animate: { opacity: 1, y: 0, scale: 1 },
    exit: { opacity: 0, y: -10, scale: 0.98 },
  };

  const artifactPanelVariants = {
    initial: { width: 0, opacity: 0 },
    animate: { width: artifactFullscreen ? "100%" : 500, opacity: 1 },
    exit: { width: 0, opacity: 0 },
  };

  return (
    <div className="h-full flex bg-background">
      {/* Main Chat Area */}
      <div className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ${artifactPanelOpen && !artifactFullscreen ? 'pr-0' : ''
        }`}>
        {/* Messages */}
        <main
          ref={scrollContainerRef}
          className="flex-1 overflow-y-auto scroll-smooth"
        >
          <div className="max-w-3xl mx-auto px-4 py-6">
            {/* Empty state with suggestions */}
            {messages.length === 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
                className="flex flex-col items-center justify-center min-h-[50vh] text-center"
              >
                <motion.div
                  initial={{ scale: 0.8 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", stiffness: 200, damping: 15 }}
                  className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center mb-6"
                >
                  <Sparkles className="w-8 h-8 text-primary" />
                </motion.div>
                <h2 className="text-2xl font-semibold mb-2">Explore Ocean Data</h2>
                <p className="text-muted-foreground mb-8 max-w-md">
                  Ask questions about ARGO floats using natural language. I'll show you maps, charts, and analysis.
                </p>

                {/* Suggestion chips */}
                <div className="flex flex-wrap justify-center gap-2 max-w-lg">
                  {QUICK_PROMPTS.map((prompt, i) => (
                    <motion.button
                      key={i}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.1 + i * 0.05 }}
                      onClick={() => handleQuerySubmit(prompt.query)}
                      className="group flex items-center gap-2 px-4 py-2.5 bg-card hover:bg-muted border rounded-xl text-sm transition-all hover:shadow-md hover:-translate-y-0.5"
                    >
                      <span>{prompt.label}</span>
                      <ArrowRight className="w-3 h-3 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
                    </motion.button>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Messages */}
            <AnimatePresence mode="popLayout">
              {messages.map((message, index) => (
                <motion.div
                  key={message.id}
                  variants={messageVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                  transition={{
                    type: "spring",
                    stiffness: 300,
                    damping: 25,
                    delay: prefersReducedMotion ? 0 : 0.02
                  }}
                  className={`flex ${message.role === "user" ? "justify-end" : "justify-start"} mb-6`}
                >
                  <div className={`max-w-[85%] ${message.role === "user" ? "" : "w-full"}`}>
                    {/* User message */}
                    {message.role === "user" && (
                      <div className="bg-primary text-primary-foreground rounded-2xl rounded-br-md px-4 py-3">
                        <p className="text-sm leading-relaxed whitespace-pre-wrap">
                          {message.content}
                        </p>
                      </div>
                    )}

                    {/* Assistant message */}
                    {message.role === "assistant" && (
                      <div className="space-y-3">
                        {/* Avatar row */}
                        <div className="flex items-center gap-2">
                          <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ type: "spring", stiffness: 400, damping: 15 }}
                            className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center"
                          >
                            <Sparkles className="w-3.5 h-3.5 text-primary" />
                          </motion.div>
                          <span className="text-xs text-muted-foreground font-medium">Vortex</span>
                          {message.metadata?.cached && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-500/10 text-green-500">
                              Cached
                            </span>
                          )}
                        </div>

                        {/* Typing indicator with status */}
                        {message.isTyping && (
                          <div className="flex items-center gap-3 px-1 py-2">
                            <div className="flex items-center gap-1">
                              <motion.span
                                className="w-2 h-2 rounded-full bg-primary"
                                animate={{ scale: [1, 1.3, 1], opacity: [0.5, 1, 0.5] }}
                                transition={{ repeat: Infinity, duration: 0.8, delay: 0 }}
                              />
                              <motion.span
                                className="w-2 h-2 rounded-full bg-primary"
                                animate={{ scale: [1, 1.3, 1], opacity: [0.5, 1, 0.5] }}
                                transition={{ repeat: Infinity, duration: 0.8, delay: 0.2 }}
                              />
                              <motion.span
                                className="w-2 h-2 rounded-full bg-primary"
                                animate={{ scale: [1, 1.3, 1], opacity: [0.5, 1, 0.5] }}
                                transition={{ repeat: Infinity, duration: 0.8, delay: 0.4 }}
                              />
                            </div>
                            <motion.span
                              initial={{ opacity: 0 }}
                              animate={{ opacity: 1 }}
                              className="text-xs text-muted-foreground"
                            >
                              Analyzing data...
                            </motion.span>
                          </div>
                        )}

                        {/* Content */}
                        {!message.isTyping && (
                          <>
                            <div className="text-sm leading-relaxed text-foreground prose prose-sm dark:prose-invert max-w-none prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5 prose-headings:my-3">
                              <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                components={{
                                  table: ({ children }) => (
                                    <div className="overflow-x-auto my-4 rounded-lg border border-border">
                                      <table className="min-w-full divide-y divide-border">
                                        {children}
                                      </table>
                                    </div>
                                  ),
                                  thead: ({ children }) => (
                                    <thead className="bg-muted/50">{children}</thead>
                                  ),
                                  tbody: ({ children }) => (
                                    <tbody className="divide-y divide-border bg-card">{children}</tbody>
                                  ),
                                  tr: ({ children }) => (
                                    <tr className="hover:bg-muted/30 transition-colors">{children}</tr>
                                  ),
                                  th: ({ children }) => (
                                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-foreground uppercase tracking-wide">
                                      {children}
                                    </th>
                                  ),
                                  td: ({ children }) => (
                                    <td className="px-4 py-2.5 text-sm text-foreground whitespace-nowrap">
                                      {children}
                                    </td>
                                  ),
                                }}
                              >
                                {message.content}
                              </ReactMarkdown>
                            </div>

                            {/* Artifacts preview - horizontal tiles */}
                            {message.artifacts && message.artifacts.length > 0 && (
                              <div className="flex flex-col gap-2 mt-4">
                                {message.artifacts.map((artifact) => {
                                  // Generate dynamic filename based on artifact type
                                  const getFilename = () => {
                                    switch (artifact.type) {
                                      case 'map': return `float_locations_${(artifact.data as any)?.length || 0}.geojson`;
                                      case 'visualization':
                                        if (artifact.visualization === 'timeseries') return 'temperature_trends.csv';
                                        if (artifact.visualization === 'profile') return 'depth_profile.csv';
                                        if (artifact.visualization === 'ts') return 'ts_diagram.json';
                                        if (artifact.visualization === 'qc') return 'qc_dashboard.json';
                                        if (artifact.visualization === 'trajectory') return 'float_trajectory.geojson';
                                        return 'visualization.json';
                                      case 'chart': return 'chart_data.json';
                                      case 'table': return 'data_export.csv';
                                      default: return 'data.json';
                                    }
                                  };

                                  const getDescription = () => {
                                    const count = Array.isArray(artifact.data) ? artifact.data.length :
                                      (artifact.data as any)?.profiles?.length ||
                                      (artifact.data as any)?.length || 0;
                                    switch (artifact.type) {
                                      case 'map': return `Displaying ${count} float positions on interactive map`;
                                      case 'visualization':
                                        if (artifact.visualization === 'timeseries') return 'Temperature & salinity trends over time';
                                        if (artifact.visualization === 'profile') return 'Vertical depth profile measurements';
                                        if (artifact.visualization === 'ts') return 'Temperature-salinity relationship diagram';
                                        if (artifact.visualization === 'qc') return 'Data quality control dashboard';
                                        if (artifact.visualization === 'trajectory') return 'Float movement trajectory path';
                                        return 'Interactive data visualization';
                                      case 'chart': return 'Statistical data analysis chart';
                                      case 'table': return `${count} records in tabular format`;
                                      default: return artifact.title;
                                    }
                                  };

                                  const getIcon = () => {
                                    switch (artifact.type) {
                                      case 'map': return <Globe className="w-5 h-5" />;
                                      case 'visualization':
                                        if (artifact.visualization === 'timeseries') return <TrendingUp className="w-5 h-5" />;
                                        if (artifact.visualization === 'profile') return <Activity className="w-5 h-5" />;
                                        if (artifact.visualization === 'ts') return <Workflow className="w-5 h-5" />;
                                        if (artifact.visualization === 'qc') return <CheckCircle2 className="w-5 h-5" />;
                                        if (artifact.visualization === 'trajectory') return <MapPin className="w-5 h-5" />;
                                        return <LineChart className="w-5 h-5" />;
                                      case 'chart': return <BarChart2 className="w-5 h-5" />;
                                      case 'table': return <Table2 className="w-5 h-5" />;
                                      default: return <FileJson className="w-5 h-5" />;
                                    }
                                  };

                                  return (
                                    <motion.button
                                      key={artifact.id}
                                      initial={{ opacity: 0, y: 10 }}
                                      animate={{ opacity: 1, y: 0 }}
                                      whileHover={{ scale: 1.005, x: 2 }}
                                      whileTap={{ scale: 0.995 }}
                                      onClick={() => {
                                        setActiveArtifact(artifact);
                                        setArtifactPanelOpen(true);
                                      }}
                                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border bg-muted/30 hover:bg-muted/60 transition-all group ${activeArtifact?.id === artifact.id ? 'ring-2 ring-primary bg-primary/5' : ''
                                        }`}
                                    >
                                      {/* Icon */}
                                      <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary/20 transition-colors">
                                        {getIcon()}
                                      </div>

                                      {/* Title and description */}
                                      <div className="flex-1 text-left min-w-0">
                                        <div className="text-sm font-medium text-foreground truncate">
                                          {artifact.title}
                                        </div>
                                        <div className="text-xs text-muted-foreground truncate mt-0.5">
                                          {getDescription()}
                                        </div>
                                      </div>

                                      {/* Filename on right */}
                                      <div className="flex-shrink-0 text-right">
                                        <span className="text-xs font-mono text-muted-foreground/70 group-hover:text-muted-foreground transition-colors">
                                          {getFilename()}
                                        </span>
                                      </div>
                                    </motion.button>
                                  );
                                })}
                              </div>
                            )}

                            {/* Actions only - metadata removed */}
                            <div className="flex items-center gap-3 mt-3 pt-3 border-t border-border/30">
                              <div className="flex-1" />
                              <div className="flex items-center gap-1">
                                <button
                                  onClick={() => handleCopy(message.content)}
                                  className="p-1.5 hover:bg-muted rounded-lg transition-colors group"
                                  title="Copy"
                                >
                                  <Copy className="w-3.5 h-3.5 text-muted-foreground group-hover:text-foreground transition-colors" />
                                </button>
                                <button
                                  onClick={() => handleRetry(message.content)}
                                  className="p-1.5 hover:bg-muted rounded-lg transition-colors group"
                                  title="Retry"
                                >
                                  <RotateCcw className="w-3.5 h-3.5 text-muted-foreground group-hover:text-foreground transition-colors" />
                                </button>
                              </div>
                            </div>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            <div ref={messagesEndRef} className="h-4" />
          </div>
        </main>

        {/* Input Area */}
        <footer className="border-t bg-background/80 backdrop-blur-sm p-4">
          <div className="max-w-3xl mx-auto">
            <motion.div
              className={`relative flex items-end gap-2 bg-card border rounded-2xl p-2 transition-all duration-200 ${inputFocused ? 'ring-2 ring-primary/30 border-primary/50' : ''
                }`}
              animate={{
                boxShadow: inputFocused ? '0 4px 20px rgba(0,0,0,0.08)' : '0 2px 10px rgba(0,0,0,0.04)'
              }}
            >
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => setInputFocused(true)}
                onBlur={() => setInputFocused(false)}
                placeholder="Ask about oceanographic data..."
                className="flex-1 px-3 py-2 bg-transparent resize-none focus:outline-none text-sm min-h-[44px] max-h-[150px]"
                rows={1}
                disabled={loading}
              />
              <motion.button
                onClick={handleSubmit}
                disabled={!input.trim() || loading}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="p-2.5 bg-primary text-primary-foreground rounded-xl hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <ArrowUp className="w-4 h-4" />
                )}
              </motion.button>
            </motion.div>
            <p className="text-[11px] text-center text-muted-foreground mt-2">
              Press Enter to send • AI-powered ocean data analysis
            </p>
          </div>
        </footer>
      </div>

      {/* Artifact Panel */}
      <AnimatePresence mode="wait">
        {artifactPanelOpen && activeArtifact && !artifactFullscreen && (
          <ResizablePanel
            defaultWidth={500}
            minWidth={350}
            maxWidth={700}
            storageKey="vortex-artifact-width"
            side="right"
            className="h-full border-l bg-card flex flex-col overflow-hidden"
          >
            {/* Panel Header */}
            <div className="flex items-center justify-between px-4 h-12 border-b bg-background/50 backdrop-blur-sm shrink-0">
              <div className="flex items-center gap-2">
                {activeArtifact.type === 'map' && <Map className="w-4 h-4 text-blue-500" />}
                {activeArtifact.type === 'visualization' && <LineChart className="w-4 h-4 text-amber-500" />}
                <span className="font-medium text-sm">{activeArtifact.title}</span>
              </div>
              <div className="flex items-center gap-1">
                {/* Export Dropdown */}
                <ExportDropdown
                  elementId={`artifact-content-${activeArtifact.id}`}
                  data={activeArtifact.data as any[]}
                  filename={activeArtifact.title?.replace(/\s+/g, '_').toLowerCase() || 'export'}
                  type={activeArtifact.type === 'map' ? 'map' : 'chart'}
                />
                <button
                  onClick={() => setArtifactFullscreen(true)}
                  className="p-1.5 hover:bg-muted rounded-lg transition-colors"
                  title="Fullscreen"
                >
                  <Maximize2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => {
                    setArtifactPanelOpen(false);
                    setArtifactFullscreen(false);
                  }}
                  className="p-1.5 hover:bg-muted rounded-lg transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Panel Content */}
            <div id={`artifact-content-${activeArtifact.id}`} className="flex-1 overflow-hidden flex flex-col" style={{ minHeight: 0 }}>
              {/* Map Artifact */}
              {activeArtifact.type === 'map' && mapReady && (
                <div className="flex-1 relative" style={{ minHeight: '400px' }}>
                  <MapContainer
                    key={`split-map-${activeArtifact.id}`}
                    center={[20, 65]}
                    zoom={4}
                    minZoom={2}
                    maxZoom={18}
                    style={{ height: "100%", width: "100%", position: 'absolute', top: 0, left: 0, right: 0, bottom: 0 }}
                    zoomControl={false}
                  >
                    {/* ESRI Satellite Imagery */}
                    <TileLayer
                      attribution='&copy; <a href="https://www.esri.com/">Esri</a> | <a href="https://www.usgs.gov/">USGS</a>'
                      url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                    />
                    <MapBoundsHandler data={activeArtifact.data as FloatData[]} padding={0.15} />
                    {(activeArtifact.data as FloatData[]).map((float) => (
                      <CircleMarker
                        key={`${float.id}-${float.date || ''}`}
                        center={[float.lat, float.lng]}
                        radius={float.is_anomaly ? 9 : 3}
                        pathOptions={{
                          color: float.is_anomaly ? '#ffffff' : getMarkerColor(float),
                          fillColor: getMarkerColor(float),
                          fillOpacity: float.is_anomaly ? 1 : 0.8,
                          weight: float.is_anomaly ? 2 : 1,
                        }}
                        eventHandlers={{
                          click: () => setSelectedFloat(float),
                        }}
                      >
                        <Tooltip>
                          <div className="text-xs">
                            <div className="font-semibold">Float {float.id}</div>
                            <div>{float.temp?.toFixed(1)}°C • {float.salinity?.toFixed(1)} PSU</div>
                          </div>
                        </Tooltip>
                      </CircleMarker>
                    ))}
                  </MapContainer>
                </div>
              )}

              {/* Visualization Artifacts */}
              {activeArtifact.type === 'visualization' && (
                <div className="p-4">
                  {activeArtifact.visualization === 'timeseries' && (
                    <TimeSeriesChart
                      data={(activeArtifact.data as FloatData[])
                        .filter(f => f.date && f.temp !== undefined)
                        .sort((a, b) => new Date(a.date!).getTime() - new Date(b.date!).getTime())
                        .map(f => ({
                          timestamp: f.date!,
                          temperature: f.temp ?? 0,
                          salinity: f.salinity ?? 0,
                        }))}
                      series={[
                        { key: 'temperature', name: 'Temperature', color: '#ef4444', unit: '°C', yAxisId: 'left' },
                        { key: 'salinity', name: 'Salinity', color: '#3b82f6', unit: 'PSU', yAxisId: 'right' },
                      ]}
                      title="Temperature & Salinity Over Time"
                      height={350}
                    />
                  )}

                  {activeArtifact.visualization === 'ts' && (
                    <TSDiagram
                      data={(activeArtifact.data as FloatData[])
                        .filter(f => f.temp !== undefined && f.salinity !== undefined)
                        .map(f => ({
                          temperature: f.temp!,
                          salinity: f.salinity!,
                          pressure: f.depth,
                          float_id: f.id,
                        }))}
                      height={400}
                    />
                  )}

                  {activeArtifact.visualization === 'profile' && (
                    <VerticalProfile
                      data={(activeArtifact.data as FloatData[])
                        .filter(f => f.depth !== undefined)
                        .map(f => ({
                          pressure: f.depth!,
                          temperature: f.temp,
                          salinity: f.salinity,
                        }))}
                      height={400}
                    />
                  )}

                  {activeArtifact.visualization === 'qc' && (
                    <QCDashboard
                      data={(activeArtifact.data as FloatData[]).map(f => ({
                        qc_flag: f.qc_flag,
                        qc_temp: f.qc_temp ?? f.qc_flag,
                        qc_psal: f.qc_psal,
                        qc_pres: f.qc_pres,
                        data_mode: f.data_mode,
                        timestamp: f.date,
                        float_id: f.id,
                      }))}
                      height={400}
                    />
                  )}

                  {activeArtifact.visualization === 'heatmap' && (
                    <GeospatialHeatmap
                      data={(activeArtifact.data as FloatData[]).map(f => ({
                        lat: f.lat,
                        lon: f.lng,
                        temperature: f.temp,
                        salinity: f.salinity,
                      }))}
                      parameter="temperature"
                      height={350}
                    />
                  )}

                  {activeArtifact.visualization === 'hovmoller' && (
                    <HovmollerDiagram
                      data={(activeArtifact.data as FloatData[])
                        .filter(f => f.date && f.depth)
                        .map(f => ({
                          timestamp: f.date!,
                          depth: f.depth!,
                          temperature: f.temp,
                          salinity: f.salinity,
                        }))}
                      parameter="temperature"
                      height={350}
                    />
                  )}

                  {activeArtifact.visualization === 'trajectory' && (
                    <TrajectoryPlot
                      data={(activeArtifact.data as FloatData[])
                        .filter(f => f.lat && f.lng && f.date)
                        .map(f => ({
                          latitude: f.lat,
                          longitude: f.lng,
                          timestamp: f.date!,
                          float_id: f.id,
                          temperature: f.temp,
                          salinity: f.salinity,
                        }))}
                      showDateLabels={true}
                      markerInterval={10}
                      height={400}
                    />
                  )}
                </div>
              )}
            </div>
            {/* Selected Float Details Panel - Shows when a float is clicked */}
            {activeArtifact.type === 'map' && (
              <AnimatePresence>
                {selectedFloat ? (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 20 }}
                    transition={{ duration: 0.2, ease: 'easeOut' }}
                    className="border-t bg-card/95 backdrop-blur-sm shrink-0"
                  >
                    {/* Float Header */}
                    <div className="flex items-center justify-between px-4 py-3 border-b border-border/50">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                          <MapPin className="w-5 h-5 text-primary" />
                        </div>
                        <div>
                          <div className="font-semibold text-sm">Float {selectedFloat.id}</div>
                          <div className="text-xs text-muted-foreground">
                            {selectedFloat.lat.toFixed(3)}°, {selectedFloat.lng.toFixed(3)}°
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => setSelectedFloat(null)}
                        className="p-1.5 hover:bg-muted rounded-lg transition-colors"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>

                    {/* Measurements Grid */}
                    <div className="grid grid-cols-3 gap-px bg-border/50">
                      <div className="px-4 py-3 bg-card">
                        <div className="flex items-center gap-2 mb-1">
                          <Thermometer className="w-4 h-4 text-orange-400" />
                          <span className="text-xs text-muted-foreground">Temperature</span>
                        </div>
                        <div className="text-lg font-semibold text-orange-400">
                          {selectedFloat.temp?.toFixed(1) ?? '--'}°C
                        </div>
                      </div>
                      <div className="px-4 py-3 bg-card">
                        <div className="flex items-center gap-2 mb-1">
                          <Droplets className="w-4 h-4 text-purple-400" />
                          <span className="text-xs text-muted-foreground">Salinity</span>
                        </div>
                        <div className="text-lg font-semibold text-purple-400">
                          {selectedFloat.salinity?.toFixed(2) ?? '--'} PSU
                        </div>
                      </div>
                      <div className="px-4 py-3 bg-card">
                        <div className="flex items-center gap-2 mb-1">
                          <Calendar className="w-4 h-4 text-blue-400" />
                          <span className="text-xs text-muted-foreground">Date</span>
                        </div>
                        <div className="text-sm font-semibold text-blue-400">
                          {selectedFloat.date ? new Date(selectedFloat.date).toLocaleDateString() : '--'}
                        </div>
                      </div>
                    </div>

                    {/* Quick Actions */}
                    <div className="px-4 py-3 flex gap-2">
                      <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => {
                          const query = `Show depth profile for float ${selectedFloat.id}`;
                          setSelectedFloat(null);
                          setArtifactPanelOpen(false);
                          handleQuerySubmit(query);
                        }}
                        className="flex-1 px-3 py-2 text-xs font-medium bg-primary/10 text-primary rounded-lg hover:bg-primary/20 transition-colors flex items-center justify-center gap-2"
                      >
                        <BarChart2 className="w-4 h-4" />
                        View Profile
                      </motion.button>
                      <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => {
                          const query = `Show trajectory for float ${selectedFloat.id}`;
                          setSelectedFloat(null);
                          setArtifactPanelOpen(false);
                          handleQuerySubmit(query);
                        }}
                        className="flex-1 px-3 py-2 text-xs font-medium bg-muted text-foreground rounded-lg hover:bg-muted/80 transition-colors flex items-center justify-center gap-2"
                      >
                        <TrendingUp className="w-4 h-4" />
                        Trajectory
                      </motion.button>
                      <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => {
                          const data = JSON.stringify(selectedFloat, null, 2);
                          navigator.clipboard.writeText(data);
                          toast.success(`Copied Float ${selectedFloat.id} data to clipboard`);
                        }}
                        className="flex-1 px-3 py-2 text-xs font-medium bg-muted text-foreground rounded-lg hover:bg-muted/80 transition-colors flex items-center justify-center gap-2"
                      >
                        <Download className="w-4 h-4" />
                        Export
                      </motion.button>
                    </div>
                  </motion.div>
                ) : (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="border-t bg-card shrink-0"
                  >
                    {/* Quick Stats Grid */}
                    {(() => {
                      const floats = activeArtifact.data as FloatData[];
                      const temps = floats.filter(f => f.temp != null).map(f => f.temp!);
                      const sals = floats.filter(f => f.salinity != null).map(f => f.salinity!);
                      const avgTemp = temps.length > 0 ? (temps.reduce((a, b) => a + b, 0) / temps.length) : null;
                      const avgSal = sals.length > 0 ? (sals.reduce((a, b) => a + b, 0) / sals.length) : null;
                      const minTemp = temps.length > 0 ? Math.min(...temps) : null;
                      const maxTemp = temps.length > 0 ? Math.max(...temps) : null;

                      return (
                        <>
                          {/* Stats Row */}
                          <div className="grid grid-cols-4 gap-px bg-border/30">
                            <div className="px-3 py-3 bg-card text-center">
                              <div className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1">Floats</div>
                              <div className="text-lg font-bold text-foreground">{floats.length}</div>
                            </div>
                            <div className="px-3 py-3 bg-card text-center">
                              <div className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1">Avg Temp</div>
                              <div className="text-lg font-bold text-orange-400">{avgTemp?.toFixed(1) ?? '--'}°C</div>
                            </div>
                            <div className="px-3 py-3 bg-card text-center">
                              <div className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1">Avg Salinity</div>
                              <div className="text-lg font-bold text-purple-400">{avgSal?.toFixed(1) ?? '--'} PSU</div>
                            </div>
                            <div className="px-3 py-3 bg-card text-center">
                              <div className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1">Temp Range</div>
                              <div className="text-sm font-bold text-blue-400">
                                {minTemp != null ? `${minTemp.toFixed(0)}° - ${maxTemp?.toFixed(0)}°` : '--'}
                              </div>
                            </div>
                          </div>

                          {/* Quick Actions / Suggested Queries */}
                          <div className="px-3 py-2 border-t border-border/30">
                            <div className="text-[10px] text-muted-foreground mb-2 uppercase tracking-wide">Quick Actions</div>
                            <div className="flex flex-wrap gap-1.5">
                              <motion.button
                                whileHover={{ scale: 1.03 }}
                                whileTap={{ scale: 0.97 }}
                                onClick={() => {
                                  setArtifactPanelOpen(false);
                                  handleQuerySubmit("Show temperature trends for these floats");
                                }}
                                className="px-2.5 py-1.5 text-[11px] font-medium bg-orange-500/10 text-orange-400 rounded-lg hover:bg-orange-500/20 transition-colors flex items-center gap-1.5"
                              >
                                <Thermometer className="w-3 h-3" />
                                Temperature Trends
                              </motion.button>
                              <motion.button
                                whileHover={{ scale: 1.03 }}
                                whileTap={{ scale: 0.97 }}
                                onClick={() => {
                                  setArtifactPanelOpen(false);
                                  handleQuerySubmit("Show salinity analysis for these floats");
                                }}
                                className="px-2.5 py-1.5 text-[11px] font-medium bg-purple-500/10 text-purple-400 rounded-lg hover:bg-purple-500/20 transition-colors flex items-center gap-1.5"
                              >
                                <Droplets className="w-3 h-3" />
                                Salinity Analysis
                              </motion.button>
                              <motion.button
                                whileHover={{ scale: 1.03 }}
                                whileTap={{ scale: 0.97 }}
                                onClick={() => {
                                  setArtifactPanelOpen(false);
                                  handleQuerySubmit("Detect anomalies in this data");
                                }}
                                className="px-2.5 py-1.5 text-[11px] font-medium bg-red-500/10 text-red-400 rounded-lg hover:bg-red-500/20 transition-colors flex items-center gap-1.5"
                              >
                                <AlertCircle className="w-3 h-3" />
                                Find Anomalies
                              </motion.button>
                              <motion.button
                                whileHover={{ scale: 1.03 }}
                                whileTap={{ scale: 0.97 }}
                                onClick={() => {
                                  setArtifactPanelOpen(false);
                                  handleQuerySubmit("Show depth profiles for these floats");
                                }}
                                className="px-2.5 py-1.5 text-[11px] font-medium bg-blue-500/10 text-blue-400 rounded-lg hover:bg-blue-500/20 transition-colors flex items-center gap-1.5"
                              >
                                <Activity className="w-3 h-3" />
                                Depth Profiles
                              </motion.button>
                            </div>
                          </div>

                          {/* Legend + Hint */}
                          <div className="px-3 py-2 border-t border-border/30 flex items-center justify-between">
                            <div className="flex items-center gap-1.5 text-[10px]">
                              <span className="text-blue-400 font-medium">Cold</span>
                              <div className="w-16 h-1.5 rounded-full" style={{
                                background: 'linear-gradient(to right, #4da6ff, #b388ff, #ff6b8a)'
                              }} />
                              <span className="text-pink-400 font-medium">Hot</span>
                            </div>
                            <span className="text-[10px] text-muted-foreground/60 flex items-center gap-1">
                              <MapPin className="w-3 h-3" />
                              Click a point for details
                            </span>
                          </div>
                        </>
                      );
                    })()}
                  </motion.div>
                )}
              </AnimatePresence>
            )}
          </ResizablePanel>
        )}
      </AnimatePresence>

      {/* Fullscreen Artifact Panel */}
      <AnimatePresence mode="wait">
        {artifactPanelOpen && activeArtifact && artifactFullscreen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-card flex flex-col overflow-hidden"
          >
            {/* Panel Header */}
            <div className="flex items-center justify-between px-4 h-12 border-b bg-background/50 backdrop-blur-sm shrink-0">
              <div className="flex items-center gap-2">
                {activeArtifact.type === 'map' && <Map className="w-4 h-4 text-blue-500" />}
                {activeArtifact.type === 'visualization' && <LineChart className="w-4 h-4 text-amber-500" />}
                <span className="font-medium text-sm">{activeArtifact.title}</span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setArtifactFullscreen(false)}
                  className="p-1.5 hover:bg-muted rounded-lg transition-colors"
                  title="Exit fullscreen"
                >
                  <Minimize2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => {
                    setArtifactPanelOpen(false);
                    setArtifactFullscreen(false);
                  }}
                  className="p-1.5 hover:bg-muted rounded-lg transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Panel Content */}
            <div className="flex-1 overflow-hidden flex flex-col min-h-0">
              {/* Map Artifact */}
              {activeArtifact.type === 'map' && mapReady && (
                <div className="flex-1 min-h-0">
                  <MapContainer
                    center={[20, 65]}
                    zoom={4}
                    minZoom={2}
                    maxZoom={18}
                    style={{ height: "100%", width: "100%" }}
                    zoomControl={false}
                  >
                    {/* ESRI Satellite Imagery */}
                    <TileLayer
                      attribution='&copy; <a href="https://www.esri.com/">Esri</a> | <a href="https://www.usgs.gov/">USGS</a>'
                      url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                    />
                    <MapBoundsHandler data={activeArtifact.data as FloatData[]} padding={0.15} />
                    {(activeArtifact.data as FloatData[]).map((float) => (
                      <CircleMarker
                        key={`${float.id}-${float.date || ''}`}
                        center={[float.lat, float.lng]}
                        radius={float.is_anomaly ? 9 : 3}
                        pathOptions={{
                          color: float.is_anomaly ? '#ffffff' : getMarkerColor(float),
                          fillColor: getMarkerColor(float),
                          fillOpacity: float.is_anomaly ? 1 : 0.8,
                          weight: float.is_anomaly ? 2 : 1,
                        }}
                        eventHandlers={{
                          click: () => setSelectedFloat(float),
                        }}
                      >
                        <Tooltip>
                          <div className="text-xs">
                            <div className="font-semibold">Float {float.id}</div>
                            <div>{float.temp?.toFixed(1)}°C • {float.salinity?.toFixed(1)} PSU</div>
                          </div>
                        </Tooltip>
                      </CircleMarker>
                    ))}
                  </MapContainer>
                </div>
              )}

              {/* Visualization Artifacts */}
              {activeArtifact.type === 'visualization' && (
                <div className="p-6">
                  {activeArtifact.visualization === 'timeseries' && (
                    <TimeSeriesChart
                      data={(activeArtifact.data as FloatData[])
                        .filter(f => f.date && f.temp !== undefined)
                        .sort((a, b) => new Date(a.date!).getTime() - new Date(b.date!).getTime())
                        .map(f => ({
                          timestamp: f.date!,
                          temperature: f.temp ?? 0,
                          salinity: f.salinity ?? 0,
                        }))}
                      series={[
                        { key: 'temperature', name: 'Temperature', color: '#ef4444', unit: '°C', yAxisId: 'left' },
                        { key: 'salinity', name: 'Salinity', color: '#3b82f6', unit: 'PSU', yAxisId: 'right' },
                      ]}
                      title="Temperature & Salinity Over Time"
                      height={500}
                    />
                  )}

                  {activeArtifact.visualization === 'ts' && (
                    <TSDiagram
                      data={(activeArtifact.data as FloatData[])
                        .filter(f => f.temp !== undefined && f.salinity !== undefined)
                        .map(f => ({
                          temperature: f.temp!,
                          salinity: f.salinity!,
                          pressure: f.depth,
                          float_id: f.id,
                        }))}
                      height={500}
                    />
                  )}

                  {activeArtifact.visualization === 'profile' && (
                    <VerticalProfile
                      data={(activeArtifact.data as FloatData[])
                        .filter(f => f.depth !== undefined)
                        .map(f => ({
                          pressure: f.depth!,
                          temperature: f.temp,
                          salinity: f.salinity,
                        }))}
                      height={500}
                    />
                  )}

                  {activeArtifact.visualization === 'qc' && (
                    <QCDashboard
                      data={(activeArtifact.data as FloatData[]).map(f => ({
                        qc_flag: f.qc_flag,
                        qc_temp: f.qc_temp ?? f.qc_flag,
                        qc_psal: f.qc_psal,
                        qc_pres: f.qc_pres,
                        data_mode: f.data_mode,
                        timestamp: f.date,
                        float_id: f.id,
                      }))}
                      height={500}
                    />
                  )}

                  {activeArtifact.visualization === 'heatmap' && (
                    <GeospatialHeatmap
                      data={(activeArtifact.data as FloatData[]).map(f => ({
                        lat: f.lat,
                        lon: f.lng,
                        temperature: f.temp,
                        salinity: f.salinity,
                      }))}
                      parameter="temperature"
                      height={500}
                    />
                  )}

                  {activeArtifact.visualization === 'hovmoller' && (
                    <HovmollerDiagram
                      data={(activeArtifact.data as FloatData[])
                        .filter(f => f.date && f.depth)
                        .map(f => ({
                          timestamp: f.date!,
                          depth: f.depth!,
                          temperature: f.temp,
                          salinity: f.salinity,
                        }))}
                      parameter="temperature"
                      height={500}
                    />
                  )}
                </div>
              )}
            </div>

            {/* Panel Footer - Controls */}
            {activeArtifact.type === 'map' && (
              <div className="border-t p-3 bg-background/50 shrink-0">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1 text-[10px]">
                      <span className="text-blue-400">Cold</span>
                      <div className="w-16 h-2 rounded-full" style={{
                        background: 'linear-gradient(to right, hsl(240, 80%, 50%), hsl(180, 80%, 50%), hsl(120, 80%, 50%), hsl(60, 80%, 50%), hsl(0, 80%, 50%)'
                      }} />
                      <span className="text-red-400">Hot</span>
                    </div>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {(activeArtifact.data as FloatData[]).length} floats
                  </span>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Map toggle button when panel is closed */}
      {!artifactPanelOpen && floatData.length > 0 && (
        <motion.button
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 20 }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => {
            setActiveArtifact({
              id: 'manual-map',
              type: 'map',
              title: `${floatData.length} ARGO Floats`,
              data: floatData,
            });
            setArtifactPanelOpen(true);
          }}
          className="fixed right-6 bottom-24 p-4 bg-primary text-primary-foreground rounded-xl shadow-lg hover:bg-primary/90 transition-all z-40"
        >
          <Map className="w-5 h-5" />
        </motion.button>
      )}
    </div>
  );
}

// Helper component for ChevronRight
function ChevronRight({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
  );
}
