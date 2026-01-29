'use client';

import React, { useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import { motion } from 'framer-motion';
import { Calendar, Layers, Settings, Download, Maximize2 } from 'lucide-react';

// Dynamic import for Plotly to avoid SSR issues
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface HovmollerDataPoint {
  timestamp: string | Date;
  depth: number;
  temperature?: number;
  salinity?: number;
  [key: string]: string | number | Date | undefined;
}

interface HovmollerDiagramProps {
  data: HovmollerDataPoint[];
  parameter?: 'temperature' | 'salinity' | 'density' | 'oxygen';
  title?: string;
  height?: number;
  className?: string;
  onFullscreen?: () => void;
}

// Color scales for different parameters
const COLOR_SCALES: Record<string, string[][]> = {
  temperature: [
    ['0', '#313695'],
    ['0.1', '#4575b4'],
    ['0.2', '#74add1'],
    ['0.3', '#abd9e9'],
    ['0.4', '#e0f3f8'],
    ['0.5', '#ffffbf'],
    ['0.6', '#fee090'],
    ['0.7', '#fdae61'],
    ['0.8', '#f46d43'],
    ['0.9', '#d73027'],
    ['1', '#a50026'],
  ],
  salinity: [
    ['0', '#f7fbff'],
    ['0.2', '#c6dbef'],
    ['0.4', '#6baed6'],
    ['0.6', '#2171b5'],
    ['0.8', '#08519c'],
    ['1', '#08306b'],
  ],
  density: [
    ['0', '#fff5eb'],
    ['0.2', '#fdd0a2'],
    ['0.4', '#fdae6b'],
    ['0.6', '#f16913'],
    ['0.8', '#d94801'],
    ['1', '#7f2704'],
  ],
  oxygen: [
    ['0', '#fff7ec'],
    ['0.2', '#fee8c8'],
    ['0.4', '#fdd49e'],
    ['0.6', '#fc8d59'],
    ['0.8', '#d7301f'],
    ['1', '#7f0000'],
  ],
};

const PARAMETER_UNITS: Record<string, string> = {
  temperature: '°C',
  salinity: 'PSU',
  density: 'kg/m³',
  oxygen: 'μmol/kg',
};

const PARAMETER_LABELS: Record<string, string> = {
  temperature: 'Temperature',
  salinity: 'Salinity',
  density: 'Density (σ-θ)',
  oxygen: 'Dissolved Oxygen',
};

export function HovmollerDiagram({
  data,
  parameter = 'temperature',
  title,
  height = 400,
  className = '',
  onFullscreen,
}: HovmollerDiagramProps) {
  const [showContours, setShowContours] = useState(true);
  const [interpolate, setInterpolate] = useState(true);

  // Process data into grid format for contour plot
  const { gridData, times, depths, stats } = useMemo(() => {
    if (!data.length) {
      return { gridData: [], times: [], depths: [], stats: null };
    }

    // Get unique times and depths, sorted
    const uniqueTimes = Array.from(new Set(data.map((d) => 
      typeof d.timestamp === 'string' ? d.timestamp : d.timestamp.toISOString()
    ))).sort();
    
    const uniqueDepths = Array.from(new Set(data.map((d) => d.depth))).sort((a, b) => a - b);

    // Create lookup for quick access
    const dataMap = new Map<string, number>();
    let minVal = Infinity;
    let maxVal = -Infinity;
    let sum = 0;
    let count = 0;

    data.forEach((d) => {
      const value = d[parameter] as number | undefined;
      if (value !== undefined && !isNaN(value)) {
        const timeKey = typeof d.timestamp === 'string' ? d.timestamp : d.timestamp.toISOString();
        dataMap.set(`${timeKey}_${d.depth}`, value);
        minVal = Math.min(minVal, value);
        maxVal = Math.max(maxVal, value);
        sum += value;
        count++;
      }
    });

    // Build 2D grid
    const grid: (number | null)[][] = uniqueDepths.map((depth) =>
      uniqueTimes.map((time) => dataMap.get(`${time}_${depth}`) ?? null)
    );

    return {
      gridData: grid,
      times: uniqueTimes,
      depths: uniqueDepths,
      stats: count > 0 ? {
        min: minVal,
        max: maxVal,
        mean: sum / count,
        count,
      } : null,
    };
  }, [data, parameter]);

  // Format time labels for x-axis
  const timeLabels = useMemo(() => {
    return times.map((t) => {
      const date = new Date(t);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
  }, [times]);

  if (!data.length || !stats) {
    return (
      <div className={`flex items-center justify-center h-64 bg-muted/30 rounded-xl ${className}`}>
        <div className="text-center text-muted-foreground">
          <Layers className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>No data available for Hovmöller diagram</p>
        </div>
      </div>
    );
  }

  const plotData: Plotly.Data[] = [
    {
      type: showContours ? 'contour' : 'heatmap',
      x: times,
      y: depths,
      z: gridData,
      colorscale: COLOR_SCALES[parameter] || COLOR_SCALES.temperature,
      contours: showContours ? {
        coloring: 'heatmap',
        showlabels: true,
        labelfont: { size: 10, color: 'white' },
      } : undefined,
      colorbar: {
        title: {
          text: `${PARAMETER_LABELS[parameter]} (${PARAMETER_UNITS[parameter]})`,
          font: { size: 12 },
        },
        thickness: 15,
        len: 0.9,
      },
      hovertemplate: 
        `<b>Date:</b> %{x|%Y-%m-%d}<br>` +
        `<b>Depth:</b> %{y}m<br>` +
        `<b>${PARAMETER_LABELS[parameter]}:</b> %{z:.2f} ${PARAMETER_UNITS[parameter]}` +
        `<extra></extra>`,
      zsmooth: interpolate ? 'best' : false,
    } as Plotly.Data,
  ];

  const layout: Partial<Plotly.Layout> = {
    title: {
      text: title || `${PARAMETER_LABELS[parameter]} Hovmöller Diagram`,
      font: { size: 14 },
    },
    xaxis: {
      title: { text: 'Time' },
      tickformat: '%b %d',
      tickangle: -45,
      showgrid: true,
      gridcolor: 'rgba(128, 128, 128, 0.2)',
    },
    yaxis: {
      title: { text: 'Depth (m)' },
      autorange: 'reversed', // Depth increases downward
      showgrid: true,
      gridcolor: 'rgba(128, 128, 128, 0.2)',
    },
    margin: { l: 60, r: 80, t: 50, b: 70 },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: {
      color: 'currentColor',
    },
  };

  const config: Partial<Plotly.Config> = {
    responsive: true,
    displayModeBar: true,
    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
    displaylogo: false,
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-card rounded-xl border overflow-hidden ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-primary" />
          <span className="font-medium text-sm">Hovmöller Diagram</span>
          <span className="text-xs text-muted-foreground">
            ({stats.count} data points)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowContours(!showContours)}
            className={`px-2 py-1 text-xs rounded-md transition-colors ${
              showContours ? 'bg-primary/20 text-primary' : 'hover:bg-muted'
            }`}
            title="Toggle contours"
          >
            Contours
          </button>
          <button
            onClick={() => setInterpolate(!interpolate)}
            className={`px-2 py-1 text-xs rounded-md transition-colors ${
              interpolate ? 'bg-primary/20 text-primary' : 'hover:bg-muted'
            }`}
            title="Toggle interpolation"
          >
            Smooth
          </button>
          {onFullscreen && (
            <button
              onClick={onFullscreen}
              className="p-1 hover:bg-muted rounded-md transition-colors"
              title="Fullscreen"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Stats bar */}
      <div className="flex items-center gap-4 px-4 py-2 bg-muted/20 text-xs border-b">
        <span className="flex items-center gap-1">
          <Calendar className="w-3 h-3 text-muted-foreground" />
          {times.length} time points
        </span>
        <span>
          Min: <strong>{stats.min.toFixed(2)}</strong> {PARAMETER_UNITS[parameter]}
        </span>
        <span>
          Max: <strong>{stats.max.toFixed(2)}</strong> {PARAMETER_UNITS[parameter]}
        </span>
        <span>
          Mean: <strong>{stats.mean.toFixed(2)}</strong> {PARAMETER_UNITS[parameter]}
        </span>
      </div>

      {/* Plot */}
      <div style={{ height }}>
        <Plot
          data={plotData}
          layout={layout}
          config={config}
          style={{ width: '100%', height: '100%' }}
          useResizeHandler
        />
      </div>
    </motion.div>
  );
}

export default HovmollerDiagram;
