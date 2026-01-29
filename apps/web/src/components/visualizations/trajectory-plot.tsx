'use client';

import React, { useMemo, useState } from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    ReferenceDot,
    Label,
} from 'recharts';
import { motion } from 'framer-motion';

interface TrajectoryPoint {
    latitude: number;
    longitude: number;
    timestamp: string;
    float_id: string;
    cycle_number?: number;
    temperature?: number;
    salinity?: number;
}

interface TrajectoryPlotProps {
    data: TrajectoryPoint[];
    title?: string;
    showDateLabels?: boolean;
    showStationMarkers?: boolean;
    markerInterval?: number; // Show date label every N points
    height?: number;
    className?: string;
    floatId?: string;
}

// Format date for display
const formatDate = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
};

// Format short date
const formatShortDate = (timestamp: string): string => {
    const date = new Date(timestamp);
    return `${date.getMonth() + 1}/${date.getFullYear().toString().slice(-2)}`;
};

/**
 * TrajectoryPlot - Scientific-style float trajectory visualization
 * 
 * Displays float movement as Latitude vs Longitude plot with:
 * - Continuous path line showing trajectory
 * - Date annotations at key points
 * - Station/cycle markers
 * - Proper scientific axis labels
 * 
 * Based on oceanographic literature style (see reference image)
 */
export function TrajectoryPlot({
    data,
    title,
    showDateLabels = true,
    showStationMarkers = true,
    markerInterval = 10, // Every 10th point gets a date label
    height = 450,
    className = '',
    floatId,
}: TrajectoryPlotProps) {
    const [hoveredPoint, setHoveredPoint] = useState<TrajectoryPoint | null>(null);

    // Sort data by timestamp and prepare for plotting
    const chartData = useMemo(() => {
        const sorted = [...data].sort((a, b) =>
            new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        );

        return sorted.map((point, index) => ({
            ...point,
            x: point.longitude,
            y: point.latitude,
            index,
            isLabelPoint: index === 0 || index === sorted.length - 1 || index % markerInterval === 0,
            label: formatDate(point.timestamp),
        }));
    }, [data, markerInterval]);

    // Calculate plot bounds with padding
    const bounds = useMemo(() => {
        if (chartData.length === 0) {
            return { lonMin: -180, lonMax: 180, latMin: -90, latMax: 90 };
        }

        const lons = chartData.map(d => d.x);
        const lats = chartData.map(d => d.y);

        const lonPadding = (Math.max(...lons) - Math.min(...lons)) * 0.1 || 1;
        const latPadding = (Math.max(...lats) - Math.min(...lats)) * 0.1 || 1;

        return {
            lonMin: Math.floor((Math.min(...lons) - lonPadding) * 10) / 10,
            lonMax: Math.ceil((Math.max(...lons) + lonPadding) * 10) / 10,
            latMin: Math.floor((Math.min(...lats) - latPadding) * 10) / 10,
            latMax: Math.ceil((Math.max(...lats) + latPadding) * 10) / 10,
        };
    }, [chartData]);

    // Get key milestone points for date labels
    const milestonePoints = useMemo(() => {
        if (!showDateLabels || chartData.length === 0) return [];

        const milestones = chartData.filter(d => d.isLabelPoint);
        return milestones;
    }, [chartData, showDateLabels]);

    // Calculate total distance traveled (simplified)
    const totalDistance = useMemo(() => {
        let distance = 0;
        for (let i = 1; i < chartData.length; i++) {
            const dx = chartData[i].x - chartData[i - 1].x;
            const dy = chartData[i].y - chartData[i - 1].y;
            distance += Math.sqrt(dx * dx + dy * dy);
        }
        return distance;
    }, [chartData]);

    // Time span
    const timeSpan = useMemo(() => {
        if (chartData.length < 2) return 'N/A';
        const start = new Date(chartData[0].timestamp);
        const end = new Date(chartData[chartData.length - 1].timestamp);
        const months = (end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24 * 30);
        if (months < 12) return `${Math.round(months)} months`;
        return `${(months / 12).toFixed(1)} years`;
    }, [chartData]);

    // Custom tooltip
    const CustomTooltip = ({ active, payload }: any) => {
        if (!active || !payload || !payload.length) return null;

        const point = payload[0].payload as any;

        return (
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-gray-900/95 backdrop-blur-sm rounded-lg p-3 border border-blue-500/30 shadow-xl"
            >
                <div className="space-y-1 text-sm">
                    <div className="font-semibold text-blue-400">
                        {point.float_id || floatId || 'Float'}
                    </div>
                    <div className="text-gray-300">{formatDate(point.timestamp)}</div>
                    <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs mt-2">
                        <span className="text-gray-400">Latitude:</span>
                        <span className="font-medium text-white">{point.y.toFixed(3)}°N</span>
                        <span className="text-gray-400">Longitude:</span>
                        <span className="font-medium text-white">{point.x.toFixed(3)}°E</span>
                        {point.cycle_number && (
                            <>
                                <span className="text-gray-400">Cycle:</span>
                                <span className="font-medium text-white">#{point.cycle_number}</span>
                            </>
                        )}
                        {point.temperature && (
                            <>
                                <span className="text-gray-400">Temp:</span>
                                <span className="font-medium text-red-400">{point.temperature.toFixed(1)}°C</span>
                            </>
                        )}
                    </div>
                </div>
            </motion.div>
        );
    };

    // Custom dot to show at specific points
    const CustomizedDot = (props: any) => {
        const { cx, cy, payload } = props;

        if (!showStationMarkers) return null;

        // Start point (green)
        if (payload.index === 0) {
            return (
                <g>
                    <circle cx={cx} cy={cy} r={8} fill="#22c55e" stroke="#fff" strokeWidth={2} />
                    <text x={cx + 12} y={cy - 8} fill="#22c55e" fontSize={11} fontWeight="bold">
                        {formatDate(payload.timestamp)}
                    </text>
                </g>
            );
        }

        // End point (red)
        if (payload.index === chartData.length - 1) {
            return (
                <g>
                    <circle cx={cx} cy={cy} r={8} fill="#ef4444" stroke="#fff" strokeWidth={2} />
                    <text x={cx + 12} y={cy - 8} fill="#ef4444" fontSize={11} fontWeight="bold">
                        {formatDate(payload.timestamp)}
                    </text>
                </g>
            );
        }

        // Milestone points (show date labels)
        if (showDateLabels && payload.isLabelPoint) {
            return (
                <g>
                    <circle cx={cx} cy={cy} r={5} fill="#3b82f6" stroke="#fff" strokeWidth={1.5} />
                    <text x={cx + 8} y={cy - 5} fill="#9ca3af" fontSize={10}>
                        {formatShortDate(payload.timestamp)}
                    </text>
                </g>
            );
        }

        return null;
    };

    const displayTitle = title || `Float ${floatId || chartData[0]?.float_id || ''} Trajectory`;

    return (
        <motion.div
            className={`bg-card border border-border rounded-xl p-4 shadow-sm ${className}`}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
        >
            {/* Header */}
            <div className="mb-4 flex items-center justify-between">
                <div>
                    <h3 className="text-lg font-semibold text-foreground">{displayTitle}</h3>
                    <p className="text-sm text-muted-foreground">
                        Spatial trajectory over {timeSpan}
                    </p>
                </div>
                <div className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded-md">
                    {chartData.length} positions
                </div>
            </div>

            {/* Main Chart */}
            <div className="relative bg-white rounded-lg">
                <ResponsiveContainer width="100%" height={height}>
                    <LineChart
                        data={chartData}
                        margin={{ top: 30, right: 40, bottom: 50, left: 60 }}
                    >
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />

                        <XAxis
                            type="number"
                            dataKey="x"
                            domain={[bounds.lonMin, bounds.lonMax]}
                            stroke="#374151"
                            tick={{ fill: '#374151', fontSize: 11 }}
                            tickLine={{ stroke: '#6b7280' }}
                            axisLine={{ stroke: '#6b7280' }}
                            tickFormatter={(value) => `${value}°`}
                        >
                            <Label
                                value="Longitude (°E)"
                                position="bottom"
                                offset={15}
                                style={{ fill: '#374151', fontSize: 13, fontWeight: 500 }}
                            />
                        </XAxis>

                        <YAxis
                            type="number"
                            dataKey="y"
                            domain={[bounds.latMin, bounds.latMax]}
                            stroke="#374151"
                            tick={{ fill: '#374151', fontSize: 11 }}
                            tickLine={{ stroke: '#6b7280' }}
                            axisLine={{ stroke: '#6b7280' }}
                            tickFormatter={(value) => `${value}°`}
                        >
                            <Label
                                value="Latitude (°N)"
                                angle={-90}
                                position="insideLeft"
                                offset={-10}
                                style={{ fill: '#374151', fontSize: 13, fontWeight: 500, textAnchor: 'middle' }}
                            />
                        </YAxis>

                        <Tooltip content={<CustomTooltip />} />

                        <Line
                            type="linear"
                            dataKey="y"
                            stroke="#2563eb"
                            strokeWidth={2}
                            dot={<CustomizedDot />}
                            activeDot={{ r: 6, fill: '#2563eb', stroke: '#fff', strokeWidth: 2 }}
                            isAnimationActive={true}
                            animationDuration={1500}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>

            {/* Legend */}
            <div className="mt-4 flex flex-wrap gap-4 items-center justify-center bg-muted/50 rounded-lg py-2">
                <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full bg-green-500 border-2 border-white shadow" />
                    <span className="text-xs font-medium text-foreground">Start</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full bg-red-500 border-2 border-white shadow" />
                    <span className="text-xs font-medium text-foreground">Latest</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-blue-500 border border-white shadow" />
                    <span className="text-xs font-medium text-foreground">Milestone</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-6 h-0.5 bg-blue-600" />
                    <span className="text-xs font-medium text-foreground">Path</span>
                </div>
            </div>

            {/* Stats */}
            <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-blue-50 dark:bg-blue-950/50 border border-blue-200 dark:border-blue-800 rounded-lg p-2 text-center">
                    <div className="text-xs text-muted-foreground font-medium">Lat Range</div>
                    <div className="text-sm font-semibold text-blue-600 dark:text-blue-400">
                        {bounds.latMin.toFixed(1)}° – {bounds.latMax.toFixed(1)}°N
                    </div>
                </div>
                <div className="bg-green-50 dark:bg-green-950/50 border border-green-200 dark:border-green-800 rounded-lg p-2 text-center">
                    <div className="text-xs text-muted-foreground font-medium">Lon Range</div>
                    <div className="text-sm font-semibold text-green-600 dark:text-green-400">
                        {bounds.lonMin.toFixed(1)}° – {bounds.lonMax.toFixed(1)}°E
                    </div>
                </div>
                <div className="bg-purple-50 dark:bg-purple-950/50 border border-purple-200 dark:border-purple-800 rounded-lg p-2 text-center">
                    <div className="text-xs text-muted-foreground font-medium">Time Span</div>
                    <div className="text-sm font-semibold text-purple-600 dark:text-purple-400">{timeSpan}</div>
                </div>
                <div className="bg-orange-50 dark:bg-orange-950/50 border border-orange-200 dark:border-orange-800 rounded-lg p-2 text-center">
                    <div className="text-xs text-muted-foreground font-medium">Positions</div>
                    <div className="text-sm font-semibold text-orange-600 dark:text-orange-400">{chartData.length}</div>
                </div>
            </div>
        </motion.div>
    );
}

export default TrajectoryPlot;
