"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  Download,
  Maximize2,
  Minimize2,
  BarChart3,
  Map,
  Table,
  LineChart,
} from "lucide-react";
import { useAppStore } from "@/store/app-store";
import { VisualizationContainer } from "./visualization-container";
import { DataTable } from "./data-table";

interface ResultsPanelProps {
  onClose: () => void;
}

type ViewMode = "visualizations" | "table" | "raw";

export function ResultsPanel({ onClose }: ResultsPanelProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("visualizations");
  const [expanded, setExpanded] = useState(false);
  const { currentResult } = useAppStore();

  if (!currentResult) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        No results to display
      </div>
    );
  }

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(currentResult.data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `floatchat-export-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-4">
          <h2 className="font-semibold">Results</h2>
          <div className="flex items-center gap-1 bg-muted rounded-lg p-1">
            {[
              { mode: "visualizations", icon: BarChart3, label: "Charts" },
              { mode: "table", icon: Table, label: "Table" },
            ].map(({ mode, icon: Icon, label }) => (
              <button
                key={mode}
                onClick={() => setViewMode(mode as ViewMode)}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-sm transition-colors ${
                  viewMode === mode
                    ? "bg-background shadow-sm"
                    : "text-muted-foreground"
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleExport}
            className="p-2 hover:bg-muted rounded-lg transition-colors"
            title="Export data"
          >
            <Download className="w-4 h-4" />
          </button>
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-2 hover:bg-muted rounded-lg transition-colors"
            title={expanded ? "Minimize" : "Maximize"}
          >
            {expanded ? (
              <Minimize2 className="w-4 h-4" />
            ) : (
              <Maximize2 className="w-4 h-4" />
            )}
          </button>
          <button
            onClick={onClose}
            className="p-2 hover:bg-muted rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Metadata Bar */}
      <div className="flex items-center gap-4 px-4 py-2 border-b bg-muted/50 text-sm">
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              currentResult.confidence > 0.8
                ? "bg-green-500"
                : currentResult.confidence > 0.5
                ? "bg-yellow-500"
                : "bg-red-500"
            }`}
          />
          <span className="text-muted-foreground">
            {Math.round(currentResult.confidence * 100)}% confidence
          </span>
        </div>
        <span className="text-muted-foreground">
          {currentResult.executionTime.toFixed(0)}ms
        </span>
        {Array.isArray(currentResult.data) && (
          <span className="text-muted-foreground">
            {currentResult.data.length} rows
          </span>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        <AnimatePresence mode="wait">
          {viewMode === "visualizations" ? (
            <motion.div
              key="viz"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-4"
            >
              {currentResult.visualizations?.length > 0 ? (
                currentResult.visualizations.map((viz: any, i: number) => (
                  <VisualizationContainer key={i} spec={viz} />
                ))
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <LineChart className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No visualizations available</p>
                  <p className="text-sm mt-1">
                    Try asking for charts or plots in your query
                  </p>
                </div>
              )}
            </motion.div>
          ) : viewMode === "table" ? (
            <motion.div
              key="table"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <DataTable data={currentResult.data} />
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </div>
  );
}
