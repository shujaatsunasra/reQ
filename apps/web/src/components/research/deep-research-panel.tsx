'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Microscope,
    X,
    ChevronRight,
    MapPin,
    Calendar,
    Thermometer,
    Waves,
    Target,
    Sparkles
} from 'lucide-react';

interface DeepResearchPanelProps {
    onStartResearch?: (config: ResearchConfig) => void;
    onClose?: () => void;
    isOpen?: boolean;
}

export interface ResearchConfig {
    focus: string;
    region?: { name: string; bbox?: [number, number, number, number] };
    timeRange?: { start: string; end: string };
    parameters: string[];
    depthRange?: { min: number; max: number };
}

const FOCUS_OPTIONS = [
    { id: 'seasonal', label: 'Seasonal Patterns', icon: Calendar, description: 'Monsoon, winter cooling, summer warming' },
    { id: 'trends', label: 'Long-term Trends', icon: Target, description: 'Multi-year temperature/salinity changes' },
    { id: 'anomalies', label: 'Anomaly Detection', icon: Sparkles, description: 'Unusual patterns and deviations' },
    { id: 'water_mass', label: 'Water Mass Analysis', icon: Waves, description: 'T-S characteristics and mixing' },
];

const REGION_OPTIONS = [
    { id: 'arabian', label: 'Arabian Sea', bbox: [50, 5, 77, 28] as [number, number, number, number] },
    { id: 'bengal', label: 'Bay of Bengal', bbox: [77, 5, 100, 25] as [number, number, number, number] },
    { id: 'indian', label: 'Indian Ocean', bbox: [20, -70, 145, 30] as [number, number, number, number] },
    { id: 'southern', label: 'Southern Ocean', bbox: [20, -70, 145, -40] as [number, number, number, number] },
];

const PARAMETERS = [
    { id: 'temperature', label: 'Temperature', icon: Thermometer },
    { id: 'salinity', label: 'Salinity', icon: Waves },
];

/**
 * Deep Research Panel
 * 
 * 4-step refinement dialog for detailed analysis:
 * 1. Research Focus (what to analyze)
 * 2. Region Selection (where)
 * 3. Time Range (when)
 * 4. Parameters (what variables)
 */
export function DeepResearchPanel({
    onStartResearch,
    onClose,
    isOpen = false,
}: DeepResearchPanelProps) {
    const [step, setStep] = useState(1);
    const [config, setConfig] = useState<Partial<ResearchConfig>>({
        parameters: ['temperature'],
    });

    const handleFocusSelect = (focusId: string) => {
        setConfig(prev => ({ ...prev, focus: focusId }));
        setStep(2);
    };

    const handleRegionSelect = (regionId: string) => {
        const region = REGION_OPTIONS.find(r => r.id === regionId);
        if (region) {
            setConfig(prev => ({
                ...prev,
                region: { name: region.label, bbox: region.bbox }
            }));
        }
        setStep(3);
    };

    const handleTimeSelect = (preset: string) => {
        const now = new Date();
        let start: Date;

        switch (preset) {
            case 'month':
                start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
                break;
            case 'year':
                start = new Date(now.getFullYear() - 1, now.getMonth(), 1);
                break;
            case '5years':
                start = new Date(now.getFullYear() - 5, 0, 1);
                break;
            default:
                start = new Date(2019, 0, 1); // All time
        }

        setConfig(prev => ({
            ...prev,
            timeRange: {
                start: start.toISOString().split('T')[0],
                end: now.toISOString().split('T')[0],
            }
        }));
        setStep(4);
    };

    const handleParameterToggle = (paramId: string) => {
        setConfig(prev => {
            const current = prev.parameters || [];
            if (current.includes(paramId)) {
                return { ...prev, parameters: current.filter(p => p !== paramId) };
            }
            return { ...prev, parameters: [...current, paramId] };
        });
    };

    const handleStartResearch = () => {
        if (config.focus && config.parameters?.length) {
            onStartResearch?.(config as ResearchConfig);
            onClose?.();
        }
    };

    const handleBack = () => {
        setStep(prev => Math.max(1, prev - 1));
    };

    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <motion.div
                className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={onClose}
            >
                <motion.div
                    className="bg-gray-900 rounded-2xl border border-gray-700 shadow-2xl w-full max-w-lg overflow-hidden"
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.9, opacity: 0 }}
                    onClick={(e) => e.stopPropagation()}
                >
                    {/* Header */}
                    <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-ocean-500/20 rounded-lg">
                                <Microscope className="text-ocean-400" size={20} />
                            </div>
                            <div>
                                <h2 className="font-semibold text-white">Deep Research Mode</h2>
                                <p className="text-xs text-gray-400">Step {step} of 4</p>
                            </div>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-400"
                        >
                            <X size={20} />
                        </button>
                    </div>

                    {/* Progress bar */}
                    <div className="h-1 bg-gray-800">
                        <motion.div
                            className="h-full bg-ocean-500"
                            initial={{ width: 0 }}
                            animate={{ width: `${(step / 4) * 100}%` }}
                        />
                    </div>

                    {/* Content */}
                    <div className="p-6">
                        <AnimatePresence mode="wait">
                            {/* Step 1: Research Focus */}
                            {step === 1 && (
                                <motion.div
                                    key="step1"
                                    initial={{ opacity: 0, x: 20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, x: -20 }}
                                    className="space-y-4"
                                >
                                    <div className="flex items-center gap-2 text-gray-300">
                                        <Target size={18} />
                                        <span className="font-medium">What's your research focus?</span>
                                    </div>

                                    <div className="grid gap-3">
                                        {FOCUS_OPTIONS.map(option => (
                                            <button
                                                key={option.id}
                                                onClick={() => handleFocusSelect(option.id)}
                                                className="flex items-center gap-4 p-4 bg-gray-800/50 hover:bg-gray-800 rounded-xl border border-gray-700 hover:border-ocean-500 transition-all group text-left"
                                            >
                                                <div className="p-2 bg-gray-700 group-hover:bg-ocean-500/20 rounded-lg transition-colors">
                                                    <option.icon size={20} className="text-gray-400 group-hover:text-ocean-400" />
                                                </div>
                                                <div className="flex-1">
                                                    <div className="font-medium text-white">{option.label}</div>
                                                    <div className="text-xs text-gray-500">{option.description}</div>
                                                </div>
                                                <ChevronRight size={18} className="text-gray-600 group-hover:text-ocean-400" />
                                            </button>
                                        ))}
                                    </div>
                                </motion.div>
                            )}

                            {/* Step 2: Region Selection */}
                            {step === 2 && (
                                <motion.div
                                    key="step2"
                                    initial={{ opacity: 0, x: 20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, x: -20 }}
                                    className="space-y-4"
                                >
                                    <div className="flex items-center gap-2 text-gray-300">
                                        <MapPin size={18} />
                                        <span className="font-medium">Select region</span>
                                    </div>

                                    <div className="grid grid-cols-2 gap-3">
                                        {REGION_OPTIONS.map(region => (
                                            <button
                                                key={region.id}
                                                onClick={() => handleRegionSelect(region.id)}
                                                className="p-4 bg-gray-800/50 hover:bg-gray-800 rounded-xl border border-gray-700 hover:border-ocean-500 transition-all text-center"
                                            >
                                                <div className="font-medium text-white">{region.label}</div>
                                            </button>
                                        ))}
                                    </div>

                                    <button
                                        onClick={handleBack}
                                        className="text-sm text-gray-500 hover:text-gray-300"
                                    >
                                        ← Back
                                    </button>
                                </motion.div>
                            )}

                            {/* Step 3: Time Range */}
                            {step === 3 && (
                                <motion.div
                                    key="step3"
                                    initial={{ opacity: 0, x: 20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, x: -20 }}
                                    className="space-y-4"
                                >
                                    <div className="flex items-center gap-2 text-gray-300">
                                        <Calendar size={18} />
                                        <span className="font-medium">Time period</span>
                                    </div>

                                    <div className="grid grid-cols-2 gap-3">
                                        {[
                                            { id: 'month', label: 'Last Month' },
                                            { id: 'year', label: 'Last Year' },
                                            { id: '5years', label: 'Last 5 Years' },
                                            { id: 'all', label: 'All Time' },
                                        ].map(option => (
                                            <button
                                                key={option.id}
                                                onClick={() => handleTimeSelect(option.id)}
                                                className="p-4 bg-gray-800/50 hover:bg-gray-800 rounded-xl border border-gray-700 hover:border-ocean-500 transition-all text-center"
                                            >
                                                <div className="font-medium text-white">{option.label}</div>
                                            </button>
                                        ))}
                                    </div>

                                    <button
                                        onClick={handleBack}
                                        className="text-sm text-gray-500 hover:text-gray-300"
                                    >
                                        ← Back
                                    </button>
                                </motion.div>
                            )}

                            {/* Step 4: Parameters */}
                            {step === 4 && (
                                <motion.div
                                    key="step4"
                                    initial={{ opacity: 0, x: 20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, x: -20 }}
                                    className="space-y-4"
                                >
                                    <div className="flex items-center gap-2 text-gray-300">
                                        <Thermometer size={18} />
                                        <span className="font-medium">What to analyze?</span>
                                    </div>

                                    <div className="space-y-2">
                                        {PARAMETERS.map(param => (
                                            <button
                                                key={param.id}
                                                onClick={() => handleParameterToggle(param.id)}
                                                className={`flex items-center gap-3 w-full p-4 rounded-xl border transition-all ${config.parameters?.includes(param.id)
                                                        ? 'bg-ocean-500/20 border-ocean-500 text-ocean-300'
                                                        : 'bg-gray-800/50 border-gray-700 text-gray-300 hover:bg-gray-800'
                                                    }`}
                                            >
                                                <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${config.parameters?.includes(param.id)
                                                        ? 'border-ocean-500 bg-ocean-500'
                                                        : 'border-gray-600'
                                                    }`}>
                                                    {config.parameters?.includes(param.id) && (
                                                        <span className="text-white text-xs">✓</span>
                                                    )}
                                                </div>
                                                <param.icon size={18} />
                                                <span className="font-medium">{param.label}</span>
                                            </button>
                                        ))}
                                    </div>

                                    {/* Summary */}
                                    <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
                                        <div className="text-xs text-gray-500 mb-2">Research Summary</div>
                                        <div className="space-y-1 text-sm">
                                            <div><span className="text-gray-500">Focus:</span> <span className="text-white">{FOCUS_OPTIONS.find(f => f.id === config.focus)?.label}</span></div>
                                            <div><span className="text-gray-500">Region:</span> <span className="text-white">{config.region?.name}</span></div>
                                            <div><span className="text-gray-500">Time:</span> <span className="text-white">{config.timeRange?.start} to {config.timeRange?.end}</span></div>
                                        </div>
                                    </div>

                                    <div className="flex items-center justify-between pt-2">
                                        <button
                                            onClick={handleBack}
                                            className="text-sm text-gray-500 hover:text-gray-300"
                                        >
                                            ← Back
                                        </button>

                                        <button
                                            onClick={handleStartResearch}
                                            disabled={!config.parameters?.length}
                                            className="px-6 py-2 bg-ocean-500 hover:bg-ocean-600 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg font-medium text-white transition-colors flex items-center gap-2"
                                        >
                                            <Microscope size={18} />
                                            Start Research
                                        </button>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
}

export default DeepResearchPanel;
