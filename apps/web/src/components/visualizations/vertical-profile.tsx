'use client';

import React, { useMemo, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { motion } from 'framer-motion';

interface ProfileDataPoint {
  pressure: number;  // dbar (depth proxy)
  temperature?: number;
  salinity?: number;
  density?: number;
  oxygen?: number;
  [key: string]: number | undefined;
}

interface VerticalProfileProps {
  data: ProfileDataPoint[];
  title?: string;
  floatId?: string;
  cycleNumber?: number;
  timestamp?: string;
  showMLD?: boolean;  // Show Mixed Layer Depth
  mldValue?: number;
  height?: number;
  className?: string;
}

const VARIABLE_CONFIG: Record<string, { color: string; unit: string; name: string }> = {
  temperature: { color: '#ef4444', unit: '°C', name: 'Temperature' },
  salinity: { color: '#3b82f6', unit: 'PSU', name: 'Salinity' },
  density: { color: '#22c55e', unit: 'kg/m³', name: 'Density' },
  oxygen: { color: '#f59e0b', unit: 'μmol/kg', name: 'Oxygen' },
};

export function VerticalProfile({
  data,
  title = 'Vertical Profile',
  floatId,
  cycleNumber,
  timestamp,
  showMLD = true,
  mldValue,
  height = 450,
  className = '',
}: VerticalProfileProps) {
  const [activeVariables, setActiveVariables] = useState<Set<string>>(
    new Set(['temperature', 'salinity'])
  );
  const [hoveredDepth, setHoveredDepth] = useState<number | null>(null);

  // Detect available variables
  const availableVariables = useMemo(() => {
    const vars: string[] = [];
    if (data.length > 0) {
      const sample = data[0];
      Object.keys(VARIABLE_CONFIG).forEach((key) => {
        if (sample[key] !== undefined) {
          vars.push(key);
        }
      });
    }
    return vars;
  }, [data]);

  // Sort data by pressure (depth)
  const sortedData = useMemo(() => {
    return [...data].sort((a, b) => a.pressure - b.pressure);
  }, [data]);

  // Toggle variable visibility
  const toggleVariable = (variable: string) => {
    setActiveVariables((prev) => {
      const next = new Set(prev);
      if (next.has(variable)) {
        next.delete(variable);
      } else {
        next.add(variable);
      }
      return next;
    });
  };

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || !payload.length) return null;

    const dataPoint = payload[0].payload;

    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-popover border border-border rounded-lg p-3 shadow-xl"
      >
        <div className="text-xs text-muted-foreground mb-2">
          Depth: {dataPoint.pressure.toFixed(0)} dbar
        </div>
        <div className="space-y-1">
          {availableVariables.map((variable) => {
            if (!activeVariables.has(variable)) return null;
            const config = VARIABLE_CONFIG[variable];
            const value = dataPoint[variable];
            if (value === undefined) return null;

            return (
              <div key={variable} className="flex items-center gap-2 text-sm">
                <div
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: config.color }}
                />
                <span className="text-muted-foreground">{config.name}:</span>
                <span className="font-medium text-foreground">
                  {value.toFixed(2)} {config.unit}
                </span>
              </div>
            );
          })}
        </div>
      </motion.div>
    );
  };

  return (
    <motion.div
      className={`bg-card border border-border rounded-xl p-4 shadow-sm ${className}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      {/* Header */}
      <div className="mb-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-foreground">{title}</h3>
            {(floatId || cycleNumber || timestamp) && (
              <p className="text-sm text-muted-foreground">
                {floatId && <span>Float: {floatId}</span>}
                {cycleNumber && <span className="ml-3">Cycle: {cycleNumber}</span>}
                {timestamp && (
                  <span className="ml-3">
                    {new Date(timestamp).toLocaleDateString()}
                  </span>
                )}
              </p>
            )}
          </div>

          {/* Variable toggles */}
          <div className="flex gap-2">
            {availableVariables.map((variable) => (
              <button
                key={variable}
                onClick={() => toggleVariable(variable)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${activeVariables.has(variable)
                    ? 'bg-opacity-30'
                    : 'bg-gray-800 text-gray-500'
                  }`}
                style={{
                  backgroundColor: activeVariables.has(variable)
                    ? `${VARIABLE_CONFIG[variable].color}30`
                    : undefined,
                  color: activeVariables.has(variable)
                    ? VARIABLE_CONFIG[variable].color
                    : undefined,
                }}
              >
                {VARIABLE_CONFIG[variable].name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart
          data={sortedData}
          layout="vertical"
          margin={{ top: 10, right: 30, left: 60, bottom: 10 }}
          onMouseMove={(e: any) => {
            if (e.activePayload?.[0]) {
              setHoveredDepth(e.activePayload[0].payload.pressure);
            }
          }}
          onMouseLeave={() => setHoveredDepth(null)}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" horizontal={false} />

          {/* Pressure (depth) axis - Y axis because layout is vertical */}
          <YAxis
            type="number"
            dataKey="pressure"
            stroke="#6b7280"
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            tickLine={{ stroke: '#4b5563' }}
            axisLine={{ stroke: '#4b5563' }}
            reversed  // Depth increases downward
            label={{
              value: 'Pressure (dbar)',
              angle: -90,
              position: 'insideLeft',
              style: { fill: '#9ca3af', fontSize: 12 },
            }}
          />

          {/* X axis for values */}
          <XAxis
            type="number"
            stroke="#6b7280"
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            tickLine={{ stroke: '#4b5563' }}
            axisLine={{ stroke: '#4b5563' }}
            domain={['auto', 'auto']}
          />

          <Tooltip content={<CustomTooltip />} />

          {/* MLD reference line */}
          {showMLD && mldValue && (
            <ReferenceLine
              y={mldValue}
              stroke="#fbbf24"
              strokeDasharray="5 5"
              strokeWidth={2}
              label={{
                value: `MLD: ${mldValue}m`,
                position: 'right',
                fill: '#fbbf24',
                fontSize: 11,
              }}
            />
          )}

          {/* Data lines */}
          {availableVariables.map((variable) => (
            activeVariables.has(variable) && (
              <Line
                key={variable}
                type="monotone"
                dataKey={variable}
                stroke={VARIABLE_CONFIG[variable].color}
                strokeWidth={2}
                dot={false}
                activeDot={{
                  r: 5,
                  stroke: VARIABLE_CONFIG[variable].color,
                  strokeWidth: 2,
                  fill: '#1f2937',
                }}
                animationDuration={800}
              />
            )
          ))}
        </LineChart>
      </ResponsiveContainer>

      {/* Legend and stats */}
      <div className="mt-4 flex flex-wrap items-center justify-between gap-4 bg-muted/50 rounded-lg p-2">
        {/* Legend */}
        <div className="flex gap-4">
          {availableVariables.map((variable) => (
            activeVariables.has(variable) && (
              <div key={variable} className="flex items-center gap-2 text-xs">
                <div
                  className="w-3 h-0.5"
                  style={{ backgroundColor: VARIABLE_CONFIG[variable].color }}
                />
                <span className="text-foreground font-medium">
                  {VARIABLE_CONFIG[variable].name} ({VARIABLE_CONFIG[variable].unit})
                </span>
              </div>
            )
          ))}
        </div>

        {/* Quick stats */}
        <div className="flex gap-4 text-xs text-muted-foreground">
          <span>Max depth: {Math.max(...data.map((d) => d.pressure)).toFixed(0)} dbar</span>
          <span>Points: {data.length}</span>
          {mldValue && <span>MLD: {mldValue.toFixed(0)} m</span>}
        </div>
      </div>

      {/* Depth indicator */}
      {hoveredDepth !== null && (
        <motion.div
          className="mt-2 text-center text-sm text-ocean-400"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          Viewing depth: {hoveredDepth.toFixed(0)} dbar (~{(hoveredDepth * 1.02).toFixed(0)} m)
        </motion.div>
      )}
    </motion.div>
  );
}

export default VerticalProfile;
