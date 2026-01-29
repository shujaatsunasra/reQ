'use client';

import React, { useMemo, useState } from 'react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { motion } from 'framer-motion';
import { ShieldCheck, AlertTriangle, XCircle, HelpCircle, Activity, TrendingUp } from 'lucide-react';

interface QCDataPoint {
  qc_flag?: number;
  qc_temp?: number;
  qc_psal?: number;
  qc_pres?: number;
  data_mode?: string;
  float_id?: string;
  timestamp?: string | Date;
}

interface QCDashboardProps {
  data: QCDataPoint[];
  title?: string;
  height?: number;
  className?: string;
}

// QC flag definitions per Argo standards
const QC_FLAGS: Record<number, { label: string; color: string; icon: any; description: string }> = {
  0: { label: 'No QC', color: '#6b7280', icon: HelpCircle, description: 'No QC performed' },
  1: { label: 'Good', color: '#22c55e', icon: ShieldCheck, description: 'Good data' },
  2: { label: 'Probably Good', color: '#3b82f6', icon: ShieldCheck, description: 'Probably good data' },
  3: { label: 'Probably Bad', color: '#f59e0b', icon: AlertTriangle, description: 'Probably bad, potentially correctable' },
  4: { label: 'Bad', color: '#ef4444', icon: XCircle, description: 'Bad data' },
  5: { label: 'Changed', color: '#8b5cf6', icon: Activity, description: 'Value changed' },
  8: { label: 'Interpolated', color: '#06b6d4', icon: TrendingUp, description: 'Estimated/interpolated' },
  9: { label: 'Missing', color: '#374151', icon: HelpCircle, description: 'Missing value' },
};

const DATA_MODES: Record<string, { label: string; color: string; description: string }> = {
  R: { label: 'Real-time', color: '#f59e0b', description: 'Real-time data (within 24-48h)' },
  A: { label: 'Adjusted', color: '#22c55e', description: 'Adjusted data (delayed mode QC)' },
  D: { label: 'Delayed', color: '#3b82f6', description: 'Delayed mode data' },
};

export function QCDashboard({
  data,
  title = 'Data Quality Overview',
  height = 400,
  className = '',
}: QCDashboardProps) {
  const [selectedView, setSelectedView] = useState<'overall' | 'parameters' | 'modes'>('overall');

  // Process QC statistics
  const stats = useMemo(() => {
    const qcCounts: Record<number, number> = {};
    const modeCounts: Record<string, number> = {};
    const paramQC: Record<string, Record<number, number>> = {
      temperature: {},
      salinity: {},
      pressure: {},
    };

    // Count by time period (monthly)
    const monthlyQC: Record<string, Record<number, number>> = {};

    data.forEach((d) => {
      // Overall QC (use qc_flag or qc_temp as proxy)
      const mainQC = d.qc_flag ?? d.qc_temp ?? 0;
      qcCounts[mainQC] = (qcCounts[mainQC] || 0) + 1;

      // Data mode
      if (d.data_mode) {
        modeCounts[d.data_mode] = (modeCounts[d.data_mode] || 0) + 1;
      }

      // Parameter-specific QC
      if (d.qc_temp !== undefined) {
        paramQC.temperature[d.qc_temp] = (paramQC.temperature[d.qc_temp] || 0) + 1;
      }
      if (d.qc_psal !== undefined) {
        paramQC.salinity[d.qc_psal] = (paramQC.salinity[d.qc_psal] || 0) + 1;
      }
      if (d.qc_pres !== undefined) {
        paramQC.pressure[d.qc_pres] = (paramQC.pressure[d.qc_pres] || 0) + 1;
      }

      // Monthly breakdown
      if (d.timestamp) {
        const date = new Date(d.timestamp);
        const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
        if (!monthlyQC[monthKey]) {
          monthlyQC[monthKey] = {};
        }
        monthlyQC[monthKey][mainQC] = (monthlyQC[monthKey][mainQC] || 0) + 1;
      }
    });

    // Calculate percentages
    const total = data.length;
    const goodCount = (qcCounts[1] || 0) + (qcCounts[2] || 0);
    const goodPercent = total > 0 ? ((goodCount / total) * 100).toFixed(1) : '0';

    return {
      total,
      qcCounts,
      modeCounts,
      paramQC,
      monthlyQC,
      goodCount,
      goodPercent,
    };
  }, [data]);

  // Format data for pie chart
  const pieData = useMemo(() => {
    return Object.entries(stats.qcCounts)
      .map(([flag, count]) => ({
        name: QC_FLAGS[parseInt(flag)]?.label || `QC ${flag}`,
        value: count,
        color: QC_FLAGS[parseInt(flag)]?.color || '#6b7280',
        flag: parseInt(flag),
      }))
      .filter((d) => d.value > 0)
      .sort((a, b) => a.flag - b.flag);
  }, [stats.qcCounts]);

  // Format data for data mode pie
  const modeData = useMemo(() => {
    return Object.entries(stats.modeCounts)
      .map(([mode, count]) => ({
        name: DATA_MODES[mode]?.label || mode,
        value: count,
        color: DATA_MODES[mode]?.color || '#6b7280',
      }))
      .filter((d) => d.value > 0);
  }, [stats.modeCounts]);

  // Format data for parameter bar chart
  const paramBarData = useMemo(() => {
    const params = ['temperature', 'salinity', 'pressure'];
    const result: any[] = [];

    // Get all unique QC flags across parameters
    const allFlags = new Set<number>();
    params.forEach((p) => {
      Object.keys(stats.paramQC[p]).forEach((f) => allFlags.add(parseInt(f)));
    });

    params.forEach((param) => {
      const entry: any = { parameter: param.charAt(0).toUpperCase() + param.slice(1) };
      allFlags.forEach((flag) => {
        entry[QC_FLAGS[flag]?.label || `QC ${flag}`] = stats.paramQC[param][flag] || 0;
      });
      result.push(entry);
    });

    return { data: result, flags: Array.from(allFlags).sort() };
  }, [stats.paramQC]);

  if (!data.length) {
    return (
      <div className={`flex items-center justify-center h-64 bg-muted/30 rounded-xl ${className}`}>
        <div className="text-center text-muted-foreground">
          <ShieldCheck className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>No QC data available</p>
        </div>
      </div>
    );
  }

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || !payload.length) return null;
    const data = payload[0].payload;
    return (
      <div className="bg-popover border rounded-lg p-2 shadow-lg text-sm">
        <p className="font-medium">{data.name}</p>
        <p>
          Count: <strong>{data.value.toLocaleString()}</strong>
        </p>
        <p className="text-muted-foreground text-xs">
          {((data.value / stats.total) * 100).toFixed(1)}% of total
        </p>
      </div>
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-card rounded-xl border overflow-hidden ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-muted/30">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-green-500" />
          <span className="font-medium text-sm">{title}</span>
        </div>
        <div className="flex items-center gap-1 bg-muted rounded-lg p-0.5">
          {(['overall', 'parameters', 'modes'] as const).map((view) => (
            <button
              key={view}
              onClick={() => setSelectedView(view)}
              className={`px-3 py-1 text-xs rounded-md transition-colors ${
                selectedView === view
                  ? 'bg-background shadow text-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {view.charAt(0).toUpperCase() + view.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-4 p-4 border-b">
        <div className="text-center">
          <div className="text-2xl font-bold">{stats.total.toLocaleString()}</div>
          <div className="text-xs text-muted-foreground">Total Records</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-green-500">{stats.goodPercent}%</div>
          <div className="text-xs text-muted-foreground">Good Quality</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-green-500">{stats.goodCount.toLocaleString()}</div>
          <div className="text-xs text-muted-foreground">Good/Prob. Good</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-amber-500">
            {(stats.total - stats.goodCount).toLocaleString()}
          </div>
          <div className="text-xs text-muted-foreground">Flagged Records</div>
        </div>
      </div>

      {/* Chart Area */}
      <div className="p-4" style={{ height: height - 150 }}>
        {selectedView === 'overall' && (
          <div className="flex gap-4 h-full">
            {/* Pie Chart */}
            <div className="flex-1">
              <h4 className="text-xs font-medium text-muted-foreground mb-2 text-center">
                QC Flag Distribution
              </h4>
              <ResponsiveContainer width="100%" height="85%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius="40%"
                    outerRadius="70%"
                    dataKey="value"
                    paddingAngle={2}
                    label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                    labelLine={{ stroke: 'currentColor', strokeWidth: 0.5 }}
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Legend */}
            <div className="w-48 space-y-2">
              <h4 className="text-xs font-medium text-muted-foreground mb-3">QC Flags</h4>
              {pieData.map((item) => {
                const FlagIcon = QC_FLAGS[item.flag]?.icon || HelpCircle;
                return (
                  <div key={item.flag} className="flex items-center gap-2 text-xs">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: item.color }}
                    />
                    <FlagIcon className="w-3 h-3" style={{ color: item.color }} />
                    <span className="flex-1">{item.name}</span>
                    <span className="text-muted-foreground">{item.value.toLocaleString()}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {selectedView === 'parameters' && (
          <div className="h-full">
            <h4 className="text-xs font-medium text-muted-foreground mb-2 text-center">
              QC Flags by Parameter
            </h4>
            <ResponsiveContainer width="100%" height="90%">
              <BarChart data={paramBarData.data} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(128,128,128,0.2)" />
                <XAxis type="number" />
                <YAxis type="category" dataKey="parameter" width={80} />
                <Tooltip />
                <Legend />
                {paramBarData.flags.map((flag) => (
                  <Bar
                    key={flag}
                    dataKey={QC_FLAGS[flag]?.label || `QC ${flag}`}
                    stackId="a"
                    fill={QC_FLAGS[flag]?.color || '#6b7280'}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {selectedView === 'modes' && (
          <div className="flex gap-4 h-full">
            {/* Data Mode Pie */}
            <div className="flex-1">
              <h4 className="text-xs font-medium text-muted-foreground mb-2 text-center">
                Data Mode Distribution
              </h4>
              <ResponsiveContainer width="100%" height="85%">
                <PieChart>
                  <Pie
                    data={modeData}
                    cx="50%"
                    cy="50%"
                    innerRadius="40%"
                    outerRadius="70%"
                    dataKey="value"
                    paddingAngle={2}
                    label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                  >
                    {modeData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Mode Legend */}
            <div className="w-48 space-y-3">
              <h4 className="text-xs font-medium text-muted-foreground mb-3">Data Modes</h4>
              {Object.entries(DATA_MODES).map(([mode, info]) => (
                <div key={mode} className="space-y-1">
                  <div className="flex items-center gap-2 text-xs">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: info.color }}
                    />
                    <span className="font-medium">{info.label}</span>
                    <span className="text-muted-foreground ml-auto">
                      {(stats.modeCounts[mode] || 0).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-[10px] text-muted-foreground pl-5">{info.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}

export default QCDashboard;
