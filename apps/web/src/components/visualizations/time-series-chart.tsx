'use client';

import React, { useMemo, useState } from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Brush,
  ReferenceLine,
} from 'recharts';
import { motion } from 'framer-motion';

interface TimeSeriesDataPoint {
  timestamp: string;
  [key: string]: number | string;
}

interface SeriesConfig {
  key: string;
  name: string;
  color: string;
  unit?: string;
  yAxisId?: 'left' | 'right';
}

interface TimeSeriesChartProps {
  data: TimeSeriesDataPoint[];
  series: SeriesConfig[];
  title?: string;
  subtitle?: string;
  height?: number;
  showBrush?: boolean;
  showArea?: boolean;
  referenceLines?: { value: number; label: string; color?: string }[];
  className?: string;
}

const formatTimestamp = (timestamp: string): string => {
  const date = new Date(timestamp);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

const formatValue = (value: number, unit?: string): string => {
  if (typeof value !== 'number') return String(value);
  const formatted = value.toFixed(2);
  return unit ? `${formatted} ${unit}` : formatted;
};

export function TimeSeriesChart({
  data,
  series,
  title,
  subtitle,
  height = 350,
  showBrush = true,
  showArea = false,
  referenceLines = [],
  className = '',
}: TimeSeriesChartProps) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const [hiddenSeries, setHiddenSeries] = useState<Set<string>>(new Set());

  // Process data for display
  const chartData = useMemo(() => {
    return data.map((point) => ({
      ...point,
      displayDate: formatTimestamp(point.timestamp),
    }));
  }, [data]);

  // Determine if we need dual Y-axes
  const hasRightAxis = useMemo(() => {
    return series.some((s) => s.yAxisId === 'right');
  }, [series]);

  // Toggle series visibility
  const toggleSeries = (key: string) => {
    setHiddenSeries((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || !payload.length) return null;

    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-popover border border-border rounded-lg p-3 shadow-xl"
      >
        <div className="text-xs text-muted-foreground mb-2">{label}</div>
        <div className="space-y-1">
          {payload.map((entry: any, idx: number) => {
            const seriesConfig = series.find((s) => s.key === entry.dataKey);
            return (
              <div key={idx} className="flex items-center gap-2 text-sm">
                <div
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: entry.color }}
                />
                <span className="text-muted-foreground">{seriesConfig?.name || entry.name}:</span>
                <span className="font-medium text-foreground">
                  {formatValue(entry.value, seriesConfig?.unit)}
                </span>
              </div>
            );
          })}
        </div>
      </motion.div>
    );
  };

  // Custom legend with click-to-hide
  const CustomLegend = () => (
    <div className="flex flex-wrap justify-center gap-4 mt-2 bg-muted/50 rounded-lg py-2">
      {series.map((s) => (
        <button
          key={s.key}
          onClick={() => toggleSeries(s.key)}
          className={`flex items-center gap-2 px-2 py-1 rounded text-xs transition-all ${hiddenSeries.has(s.key)
              ? 'opacity-40 line-through'
              : 'opacity-100 hover:bg-muted'
            }`}
        >
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: s.color }}
          />
          <span className="text-foreground font-medium">{s.name}</span>
          {s.unit && <span className="text-muted-foreground">({s.unit})</span>}
        </button>
      ))}
    </div>
  );

  const ChartComponent = showArea ? AreaChart : LineChart;

  return (
    <motion.div
      className={`bg-card border border-border rounded-xl p-4 shadow-sm ${className}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      {/* Header */}
      {(title || subtitle) && (
        <div className="mb-4">
          {title && (
            <h3 className="text-lg font-semibold text-foreground">{title}</h3>
          )}
          {subtitle && (
            <p className="text-sm text-muted-foreground">{subtitle}</p>
          )}
        </div>
      )}

      {/* Chart */}
      <ResponsiveContainer width="100%" height={height}>
        <ChartComponent
          data={chartData}
          margin={{ top: 10, right: 30, left: 10, bottom: 10 }}
          onMouseMove={(e: any) => {
            if (e.activeTooltipIndex !== undefined) {
              setActiveIndex(e.activeTooltipIndex);
            }
          }}
          onMouseLeave={() => setActiveIndex(null)}
        >
          <defs>
            {series.map((s) => (
              <linearGradient
                key={`gradient-${s.key}`}
                id={`gradient-${s.key}`}
                x1="0"
                y1="0"
                x2="0"
                y2="1"
              >
                <stop offset="5%" stopColor={s.color} stopOpacity={0.3} />
                <stop offset="95%" stopColor={s.color} stopOpacity={0} />
              </linearGradient>
            ))}
          </defs>

          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#374151"
            vertical={false}
          />

          <XAxis
            dataKey="displayDate"
            stroke="#6b7280"
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            tickLine={{ stroke: '#4b5563' }}
            axisLine={{ stroke: '#4b5563' }}
          />

          <YAxis
            yAxisId="left"
            stroke="#6b7280"
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            tickLine={{ stroke: '#4b5563' }}
            axisLine={{ stroke: '#4b5563' }}
            tickFormatter={(value) => value.toFixed(1)}
          />

          {hasRightAxis && (
            <YAxis
              yAxisId="right"
              orientation="right"
              stroke="#6b7280"
              tick={{ fill: '#9ca3af', fontSize: 11 }}
              tickLine={{ stroke: '#4b5563' }}
              axisLine={{ stroke: '#4b5563' }}
              tickFormatter={(value) => value.toFixed(1)}
            />
          )}

          <Tooltip content={<CustomTooltip />} />

          {/* Reference lines */}
          {referenceLines.map((ref, idx) => (
            <ReferenceLine
              key={idx}
              y={ref.value}
              yAxisId="left"
              stroke={ref.color || '#ef4444'}
              strokeDasharray="5 5"
              label={{
                value: ref.label,
                position: 'right',
                fill: ref.color || '#ef4444',
                fontSize: 10,
              }}
            />
          ))}

          {/* Data series */}
          {series.map((s) => (
            showArea ? (
              <Area
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.name}
                stroke={s.color}
                fill={`url(#gradient-${s.key})`}
                strokeWidth={2}
                dot={false}
                activeDot={{
                  r: 6,
                  stroke: s.color,
                  strokeWidth: 2,
                  fill: '#1f2937',
                }}
                yAxisId={s.yAxisId || 'left'}
                hide={hiddenSeries.has(s.key)}
                animationDuration={800}
                animationEasing="ease-out"
              />
            ) : (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.name}
                stroke={s.color}
                fill="none"
                strokeWidth={2}
                dot={false}
                activeDot={{
                  r: 6,
                  stroke: s.color,
                  strokeWidth: 2,
                  fill: '#1f2937',
                }}
                yAxisId={s.yAxisId || 'left'}
                hide={hiddenSeries.has(s.key)}
                animationDuration={800}
                animationEasing="ease-out"
              />
            )
          ))}

          {/* Brush for time selection */}
          {showBrush && data.length > 20 && (
            <Brush
              dataKey="displayDate"
              height={30}
              stroke="#0ea5e9"
              fill="#1e293b"
              tickFormatter={(value) => value}
            />
          )}
        </ChartComponent>
      </ResponsiveContainer>

      {/* Custom Legend */}
      <CustomLegend />

      {/* Stats summary */}
      {activeIndex !== null && data[activeIndex] && (
        <motion.div
          className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          {series
            .filter((s) => !hiddenSeries.has(s.key))
            .slice(0, 4)
            .map((s) => {
              const value = data[activeIndex][s.key];
              return (
                <div
                  key={s.key}
                  className="bg-muted border border-border rounded-lg p-2 text-center"
                >
                  <div className="text-xs text-muted-foreground font-medium">{s.name}</div>
                  <div className="text-lg font-semibold" style={{ color: s.color }}>
                    {typeof value === 'number' ? formatValue(value, s.unit) : value}
                  </div>
                </div>
              );
            })}
        </motion.div>
      )}
    </motion.div>
  );
}

export default TimeSeriesChart;
