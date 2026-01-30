'use client';

import React from 'react';
import { motion } from 'framer-motion';
import {
    MapPin,
    Thermometer,
    Droplets,
    Waves,
    Calendar,
    BarChart3,
    Route,
    ExternalLink,
    Plus,
    X
} from 'lucide-react';

interface FloatData {
    float_id: string;
    cycle_number: number;
    lat: number;
    lng: number;
    temperature?: number;
    salinity?: number;
    depth?: number;
    date?: string;
    timestamp?: string;
    qc_flag?: number;
    data_mode?: string;
    is_anomaly?: boolean;
    anomaly_type?: string;
    anomaly_score?: number;
}

interface FloatHoverCardProps {
    data: FloatData;
    onClose?: () => void;
    onShowProfile?: (floatId: string) => void;
    onShowTrajectory?: (floatId: string) => void;
    onGoToFloatPage?: (floatId: string) => void;
    onAddToCompare?: (floatId: string) => void;
    className?: string;
}

// Get quality label and color based on QC flag
const getQualityInfo = (qcFlag?: number): { label: string; color: string; bgColor: string } => {
    switch (qcFlag) {
        case 1:
            return { label: 'Good', color: 'text-emerald-400', bgColor: 'bg-emerald-500' };
        case 2:
            return { label: 'Probably Good', color: 'text-yellow-400', bgColor: 'bg-yellow-500' };
        case 3:
            return { label: 'Questionable', color: 'text-orange-400', bgColor: 'bg-orange-500' };
        case 4:
            return { label: 'Bad', color: 'text-red-400', bgColor: 'bg-red-500' };
        default:
            return { label: 'Unknown', color: 'text-gray-400', bgColor: 'bg-gray-500' };
    }
};

// Format temperature with color coding
const formatTemperature = (temp?: number): { value: string; color: string } => {
    if (temp === undefined) return { value: '--', color: 'text-gray-400' };

    let color = 'text-cyan-400'; // Cold
    if (temp > 15) color = 'text-blue-400';
    if (temp > 20) color = 'text-green-400';
    if (temp > 25) color = 'text-yellow-400';
    if (temp > 28) color = 'text-orange-400';

    return { value: `${temp.toFixed(1)} °C`, color };
};

// Format salinity
const formatSalinity = (sal?: number): { value: string; color: string } => {
    if (sal === undefined) return { value: '--', color: 'text-gray-400' };
    return { value: `${sal.toFixed(2)} ppt`, color: 'text-purple-400' };
};

// Format depth
const formatDepth = (depth?: number): { value: string; color: string } => {
    if (depth === undefined) return { value: '--', color: 'text-gray-400' };
    return { value: `${Math.round(depth)} m`, color: 'text-teal-400' };
};

// Format date
const formatDate = (dateStr?: string): string => {
    if (!dateStr) return '--';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
};

// Format coordinates
const formatCoords = (lat: number, lng: number): string => {
    const latDir = lat >= 0 ? '°' : '°';
    const lngDir = lng >= 0 ? '°' : '°';
    return `${lat.toFixed(3)}${latDir}, ${lng.toFixed(3)}${lngDir}`;
};

export function FloatHoverCard({
    data,
    onClose,
    onShowProfile,
    onShowTrajectory,
    onGoToFloatPage,
    onAddToCompare,
    className = ''
}: FloatHoverCardProps) {
    const quality = getQualityInfo(data.qc_flag);
    const temp = formatTemperature(data.temperature);
    const sal = formatSalinity(data.salinity);
    const depth = formatDepth(data.depth);
    const dateStr = formatDate(data.date || data.timestamp);

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -10 }}
            transition={{ duration: 0.15 }}
            className={`w-72 bg-gray-900/95 backdrop-blur-md rounded-xl shadow-2xl border border-gray-700/50 overflow-hidden ${className}`}
        >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700/50 bg-gray-800/50">
                <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-full bg-blue-500 flex items-center justify-center">
                        <MapPin className="w-3.5 h-3.5 text-white" />
                    </div>
                    <span className="font-semibold text-white text-sm">
                        Float {data.float_id} - Cycle {data.cycle_number}
                    </span>
                </div>
                {onClose && (
                    <button
                        onClick={onClose}
                        className="p-1 hover:bg-gray-700 rounded transition-colors"
                    >
                        <X className="w-4 h-4 text-gray-400" />
                    </button>
                )}
            </div>

            {/* Basic Info */}
            <div className="px-4 py-3 space-y-2 border-b border-gray-700/30">
                <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Platform Code:</span>
                    <span className="text-white font-medium">{data.float_id}</span>
                </div>
                <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Cycle:</span>
                    <span className="text-white font-medium">{data.cycle_number}</span>
                </div>
                <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Date:</span>
                    <span className="text-white font-medium">{dateStr}</span>
                </div>
                <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Location:</span>
                    <span className="text-white font-medium">{formatCoords(data.lat, data.lng)}</span>
                </div>
            </div>

            {/* Measurements */}
            <div className="px-4 py-3 space-y-2 border-b border-gray-700/30">
                <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                        <Thermometer className="w-4 h-4 text-orange-400" />
                        <span className="text-gray-300">Temperature</span>
                    </div>
                    <span className={`font-semibold ${temp.color}`}>{temp.value}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                        <Droplets className="w-4 h-4 text-purple-400" />
                        <span className="text-gray-300">Salinity</span>
                    </div>
                    <span className={`font-semibold ${sal.color}`}>{sal.value}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                        <Waves className="w-4 h-4 text-teal-400" />
                        <span className="text-gray-300">Depth</span>
                    </div>
                    <span className={`font-semibold ${depth.color}`}>{depth.value}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-gray-400" />
                        <span className="text-gray-300">Date</span>
                    </div>
                    <span className="font-medium text-white">{dateStr}</span>
                </div>
            </div>

            {/* Quick Actions */}
            <div className="px-4 py-3 space-y-1 border-b border-gray-700/30">
                <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">Quick Actions</div>

                <button
                    onClick={() => onShowProfile?.(data.float_id)}
                    className="w-full flex items-center gap-3 px-2 py-2 hover:bg-gray-800 rounded-lg transition-colors text-left"
                >
                    <BarChart3 className="w-4 h-4 text-blue-400" />
                    <div>
                        <div className="text-sm text-white">Show profile data</div>
                        <div className="text-xs text-gray-500">View depth profile charts</div>
                    </div>
                </button>

                <button
                    onClick={() => onShowTrajectory?.(data.float_id)}
                    className="w-full flex items-center gap-3 px-2 py-2 hover:bg-gray-800 rounded-lg transition-colors text-left"
                >
                    <Route className="w-4 h-4 text-green-400" />
                    <div>
                        <div className="text-sm text-white">Show float trajectory</div>
                        <div className="text-xs text-gray-500">View movement path</div>
                    </div>
                </button>

                <button
                    onClick={() => onGoToFloatPage?.(data.float_id)}
                    className="w-full flex items-center gap-3 px-2 py-2 hover:bg-gray-800 rounded-lg transition-colors text-left"
                >
                    <ExternalLink className="w-4 h-4 text-purple-400" />
                    <div>
                        <div className="text-sm text-white">Go to float page</div>
                        <div className="text-xs text-gray-500">View detailed float info</div>
                    </div>
                </button>

                <button
                    onClick={() => onAddToCompare?.(data.float_id)}
                    className="w-full flex items-center gap-3 px-2 py-2 hover:bg-gray-800 rounded-lg transition-colors text-left"
                >
                    <Plus className="w-4 h-4 text-orange-400" />
                    <div>
                        <div className="text-sm text-white">Add to Compare</div>
                        <div className="text-xs text-gray-500">Add to comparison</div>
                    </div>
                </button>
            </div>

            {/* Data Quality */}
            <div className="px-4 py-3 flex items-center justify-between border-b border-gray-700/30">
                <span className="text-sm text-gray-400">Data Quality</span>
                <span className={`px-3 py-1 ${quality.bgColor} text-white text-xs font-medium rounded-full`}>
                    {quality.label}
                </span>
            </div>

            {/* Footer */}
            <div className="px-4 py-2 bg-blue-500/10 text-center">
                <span className="text-xs text-blue-400">
                    Click to select • Shift+Click to multi-select
                </span>
            </div>
        </motion.div>
    );
}

export default FloatHoverCard;
