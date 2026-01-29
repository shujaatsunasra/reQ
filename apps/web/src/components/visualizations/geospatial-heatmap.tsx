'use client';

import React, { useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import { motion } from 'framer-motion';
import { Map, Thermometer, Droplets, Layers, Settings, Maximize2 } from 'lucide-react';

// Dynamic import for Plotly
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface HeatmapDataPoint {
  lat: number;
  lon: number;
  temperature?: number;
  salinity?: number;
  density?: number;
  [key: string]: number | undefined;
}

interface GeospatialHeatmapProps {
  data: HeatmapDataPoint[];
  parameter?: 'temperature' | 'salinity' | 'density' | 'pressure';
  title?: string;
  height?: number;
  className?: string;
  showContour?: boolean;
  gridResolution?: number; // degrees
  onFullscreen?: () => void;
}

// Color scales
const COLOR_SCALES: Record<string, string> = {
  temperature: 'RdYlBu_r', // Reverse: red=hot, blue=cold
  salinity: 'Blues',
  density: 'Oranges',
  pressure: 'Purples',
};

const PARAMETER_UNITS: Record<string, string> = {
  temperature: '°C',
  salinity: 'PSU',
  density: 'kg/m³',
  pressure: 'dbar',
};

const PARAMETER_LABELS: Record<string, string> = {
  temperature: 'Temperature',
  salinity: 'Salinity',
  density: 'Density',
  pressure: 'Pressure',
};

export function GeospatialHeatmap({
  data,
  parameter = 'temperature',
  title,
  height = 450,
  className = '',
  showContour = true,
  gridResolution = 1.0,
  onFullscreen,
}: GeospatialHeatmapProps) {
  const [useScatterMode, setUseScatterMode] = useState(false);

  // Grid data for heatmap
  const { gridData, latGrid, lonGrid, stats, bounds } = useMemo(() => {
    if (!data.length) {
      return { gridData: [], latGrid: [], lonGrid: [], stats: null, bounds: null };
    }

    // Calculate bounds
    const lats = data.map((d) => d.lat);
    const lons = data.map((d) => d.lon);
    const minLat = Math.floor(Math.min(...lats) / gridResolution) * gridResolution;
    const maxLat = Math.ceil(Math.max(...lats) / gridResolution) * gridResolution;
    const minLon = Math.floor(Math.min(...lons) / gridResolution) * gridResolution;
    const maxLon = Math.ceil(Math.max(...lons) / gridResolution) * gridResolution;

    // Create grid
    const nLat = Math.ceil((maxLat - minLat) / gridResolution) + 1;
    const nLon = Math.ceil((maxLon - minLon) / gridResolution) + 1;

    const latValues: number[] = [];
    const lonValues: number[] = [];

    for (let i = 0; i < nLat; i++) {
      latValues.push(minLat + i * gridResolution);
    }
    for (let j = 0; j < nLon; j++) {
      lonValues.push(minLon + j * gridResolution);
    }

    // Initialize grid with nulls
    const grid: (number | null)[][] = Array(nLat)
      .fill(null)
      .map(() => Array(nLon).fill(null));
    const counts: number[][] = Array(nLat)
      .fill(null)
      .map(() => Array(nLon).fill(0));

    // Aggregate data points
    let minVal = Infinity;
    let maxVal = -Infinity;
    let sum = 0;
    let count = 0;

    data.forEach((d) => {
      const value = d[parameter];
      if (value !== undefined && !isNaN(value)) {
        const latIdx = Math.round((d.lat - minLat) / gridResolution);
        const lonIdx = Math.round((d.lon - minLon) / gridResolution);

        if (latIdx >= 0 && latIdx < nLat && lonIdx >= 0 && lonIdx < nLon) {
          if (grid[latIdx][lonIdx] === null) {
            grid[latIdx][lonIdx] = 0;
          }
          grid[latIdx][lonIdx]! += value;
          counts[latIdx][lonIdx]++;

          minVal = Math.min(minVal, value);
          maxVal = Math.max(maxVal, value);
          sum += value;
          count++;
        }
      }
    });

    // Average the grid cells
    for (let i = 0; i < nLat; i++) {
      for (let j = 0; j < nLon; j++) {
        if (counts[i][j] > 0 && grid[i][j] !== null) {
          grid[i][j] = grid[i][j]! / counts[i][j];
        }
      }
    }

    return {
      gridData: grid,
      latGrid: latValues,
      lonGrid: lonValues,
      bounds: { minLat, maxLat, minLon, maxLon },
      stats:
        count > 0
          ? {
              min: minVal,
              max: maxVal,
              mean: sum / count,
              count,
            }
          : null,
    };
  }, [data, parameter, gridResolution]);

  if (!data.length || !stats) {
    return (
      <div className={`flex items-center justify-center h-64 bg-muted/30 rounded-xl ${className}`}>
        <div className="text-center text-muted-foreground">
          <Map className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>No data available for heatmap</p>
        </div>
      </div>
    );
  }

  // Plotly data for scatter mode (show actual points)
  const scatterData: Plotly.Data[] = useScatterMode
    ? [
        {
          type: 'scattergeo',
          mode: 'markers',
          lat: data.map((d) => d.lat),
          lon: data.map((d) => d.lon),
          marker: {
            size: 8,
            color: data.map((d) => d[parameter] ?? 0),
            colorscale: COLOR_SCALES[parameter] || 'RdYlBu_r',
            cmin: stats.min,
            cmax: stats.max,
            colorbar: {
              title: {
                text: `${PARAMETER_LABELS[parameter]} (${PARAMETER_UNITS[parameter]})`,
                font: { size: 11 },
              },
              thickness: 15,
              len: 0.8,
            },
            line: { width: 0.5, color: 'rgba(0,0,0,0.3)' },
          },
          hovertemplate:
            `<b>Location:</b> %{lat:.2f}°, %{lon:.2f}°<br>` +
            `<b>${PARAMETER_LABELS[parameter]}:</b> %{marker.color:.2f} ${PARAMETER_UNITS[parameter]}` +
            `<extra></extra>`,
        } as Plotly.Data,
      ]
    : [];

  // Plotly data for contour/heatmap mode
  const gridPlotData: Plotly.Data[] = !useScatterMode
    ? [
        {
          type: showContour ? 'contour' : 'heatmap',
          x: lonGrid,
          y: latGrid,
          z: gridData,
          colorscale: COLOR_SCALES[parameter] || 'RdYlBu_r',
          zmin: stats.min,
          zmax: stats.max,
          contours: showContour
            ? {
                coloring: 'heatmap',
                showlabels: true,
                labelfont: { size: 9, color: 'white' },
              }
            : undefined,
          colorbar: {
            title: {
              text: `${PARAMETER_LABELS[parameter]} (${PARAMETER_UNITS[parameter]})`,
              font: { size: 11 },
            },
            thickness: 15,
            len: 0.8,
          },
          hovertemplate:
            `<b>Location:</b> %{y:.1f}°N, %{x:.1f}°E<br>` +
            `<b>${PARAMETER_LABELS[parameter]}:</b> %{z:.2f} ${PARAMETER_UNITS[parameter]}` +
            `<extra></extra>`,
        } as Plotly.Data,
      ]
    : [];

  const layout: Partial<Plotly.Layout> = useScatterMode
    ? {
        title: {
          text: title || `${PARAMETER_LABELS[parameter]} Distribution`,
          font: { size: 14 },
        },
        geo: {
          scope: 'world',
          projection: { type: 'natural earth' },
          showland: true,
          landcolor: 'rgba(40, 40, 40, 0.3)',
          showocean: true,
          oceancolor: 'rgba(20, 50, 80, 0.2)',
          showcoastlines: true,
          coastlinecolor: 'rgba(100, 100, 100, 0.5)',
          showframe: false,
          lonaxis: bounds ? { range: [bounds.minLon - 5, bounds.maxLon + 5] } : undefined,
          lataxis: bounds ? { range: [bounds.minLat - 5, bounds.maxLat + 5] } : undefined,
        },
        margin: { l: 0, r: 40, t: 50, b: 0 },
        paper_bgcolor: 'transparent',
        font: { color: 'currentColor' },
      }
    : {
        title: {
          text: title || `${PARAMETER_LABELS[parameter]} Heatmap`,
          font: { size: 14 },
        },
        xaxis: {
          title: { text: 'Longitude (°E)' },
          showgrid: true,
          gridcolor: 'rgba(128, 128, 128, 0.2)',
        },
        yaxis: {
          title: { text: 'Latitude (°N)' },
          showgrid: true,
          gridcolor: 'rgba(128, 128, 128, 0.2)',
          scaleanchor: 'x',
          scaleratio: 1,
        },
        margin: { l: 60, r: 80, t: 50, b: 50 },
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { color: 'currentColor' },
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
          {parameter === 'temperature' ? (
            <Thermometer className="w-4 h-4 text-red-400" />
          ) : (
            <Droplets className="w-4 h-4 text-blue-400" />
          )}
          <span className="font-medium text-sm">Geospatial Heatmap</span>
          <span className="text-xs text-muted-foreground">
            ({stats.count} points)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setUseScatterMode(!useScatterMode)}
            className={`px-2 py-1 text-xs rounded-md transition-colors ${
              useScatterMode ? 'bg-primary/20 text-primary' : 'hover:bg-muted'
            }`}
            title="Toggle scatter mode"
          >
            {useScatterMode ? 'Scatter' : 'Grid'}
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
        <span>
          Grid: <strong>{gridResolution}°</strong>
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
          data={useScatterMode ? scatterData : gridPlotData}
          layout={layout}
          config={config}
          style={{ width: '100%', height: '100%' }}
          useResizeHandler
        />
      </div>
    </motion.div>
  );
}

export default GeospatialHeatmap;
