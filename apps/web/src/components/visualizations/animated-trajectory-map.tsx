'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { LeafletMap } from './leaflet-map';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Play,
    Pause,
    RotateCcw,
    FastForward,
    ChevronLeft,
    ChevronRight
} from 'lucide-react';

interface TrajectoryPoint {
    float_id: string;
    lat: number;
    lon: number;
    timestamp: string;
    cycle_number: number;
    temperature?: number;
    salinity?: number;
    pressure?: number;
}

interface TrajectoryData {
    float_id: string;
    positions: TrajectoryPoint[];
    color?: string;
}

interface AnimatedTrajectoryMapProps {
    trajectories: TrajectoryData[];
    className?: string;
    height?: number | string;
    autoPlay?: boolean;
    showControls?: boolean;
}

/**
 * Animated Trajectory Map
 * 
 * Renders float trajectories with animation support:
 * - Play/Pause animation
 * - Speed control (1x, 2x, 5x, 10x)
 * - Time slider for manual control
 * - Trail effect showing recent path
 */
export function AnimatedTrajectoryMap({
    trajectories,
    className = '',
    height = 500,
    autoPlay = false,
    showControls = true,
}: AnimatedTrajectoryMapProps) {
    const [isPlaying, setIsPlaying] = useState(autoPlay);
    const [speed, setSpeed] = useState(1);
    const [currentFrame, setCurrentFrame] = useState(0);
    const [maxFrames, setMaxFrames] = useState(0);
    const animationRef = useRef<NodeJS.Timeout | null>(null);

    // Calculate total frames based on all trajectories
    useEffect(() => {
        const totalPoints = Math.max(
            ...trajectories.map(t => t.positions.length),
            1
        );
        setMaxFrames(totalPoints);
    }, [trajectories]);

    // Get current visible trajectories based on frame
    const getVisibleTrajectories = useCallback((): TrajectoryData[] => {
        return trajectories.map(traj => ({
            ...traj,
            positions: traj.positions.slice(0, Math.min(currentFrame + 1, traj.positions.length))
        }));
    }, [trajectories, currentFrame]);

    // Animation loop
    useEffect(() => {
        if (isPlaying && currentFrame < maxFrames - 1) {
            animationRef.current = setTimeout(() => {
                setCurrentFrame(prev => Math.min(prev + 1, maxFrames - 1));
            }, 500 / speed); // Base speed: 500ms per frame
        } else if (currentFrame >= maxFrames - 1) {
            setIsPlaying(false);
        }

        return () => {
            if (animationRef.current) {
                clearTimeout(animationRef.current);
            }
        };
    }, [isPlaying, currentFrame, maxFrames, speed]);

    const handlePlayPause = () => {
        if (currentFrame >= maxFrames - 1) {
            setCurrentFrame(0);
        }
        setIsPlaying(!isPlaying);
    };

    const handleReset = () => {
        setIsPlaying(false);
        setCurrentFrame(0);
    };

    const handleSpeedChange = () => {
        const speeds = [1, 2, 5, 10];
        const currentIndex = speeds.indexOf(speed);
        setSpeed(speeds[(currentIndex + 1) % speeds.length]);
    };

    const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setIsPlaying(false);
        setCurrentFrame(parseInt(e.target.value, 10));
    };

    const handleStep = (direction: 'prev' | 'next') => {
        setIsPlaying(false);
        setCurrentFrame(prev =>
            direction === 'next'
                ? Math.min(prev + 1, maxFrames - 1)
                : Math.max(prev - 1, 0)
        );
    };

    // Get current timestamp for display
    const getCurrentTimestamp = (): string => {
        for (const traj of trajectories) {
            if (traj.positions[currentFrame]) {
                const date = new Date(traj.positions[currentFrame].timestamp);
                return date.toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric'
                });
            }
        }
        return '';
    };

    return (
        <div className={`relative ${className}`}>
            {/* Map */}
            <LeafletMap
                data={{
                    trajectories: getVisibleTrajectories(),
                    center: trajectories[0]?.positions[0]
                        ? [trajectories[0].positions[0].lat, trajectories[0].positions[0].lon]
                        : [0, 0],
                    zoom: 5,
                }}
                height={height}
            />

            {/* Animation Controls */}
            {showControls && (
                <motion.div
                    className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-gray-900/95 backdrop-blur-md rounded-xl p-3 z-[1000] shadow-xl border border-gray-700"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    <div className="flex items-center gap-3">
                        {/* Reset button */}
                        <button
                            onClick={handleReset}
                            className="p-2 hover:bg-gray-700 rounded-lg transition-colors text-gray-400 hover:text-white"
                            title="Reset"
                        >
                            <RotateCcw size={18} />
                        </button>

                        {/* Previous frame */}
                        <button
                            onClick={() => handleStep('prev')}
                            disabled={currentFrame === 0}
                            className="p-2 hover:bg-gray-700 rounded-lg transition-colors text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
                            title="Previous"
                        >
                            <ChevronLeft size={18} />
                        </button>

                        {/* Play/Pause button */}
                        <button
                            onClick={handlePlayPause}
                            className="p-3 bg-ocean-500 hover:bg-ocean-600 rounded-full transition-colors text-white shadow-lg"
                            title={isPlaying ? 'Pause' : 'Play'}
                        >
                            {isPlaying ? <Pause size={20} /> : <Play size={20} className="ml-0.5" />}
                        </button>

                        {/* Next frame */}
                        <button
                            onClick={() => handleStep('next')}
                            disabled={currentFrame >= maxFrames - 1}
                            className="p-2 hover:bg-gray-700 rounded-lg transition-colors text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
                            title="Next"
                        >
                            <ChevronRight size={18} />
                        </button>

                        {/* Speed control */}
                        <button
                            onClick={handleSpeedChange}
                            className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors text-sm font-medium text-ocean-400"
                            title="Change speed"
                        >
                            {speed}x
                        </button>

                        {/* Separator */}
                        <div className="w-px h-8 bg-gray-700" />

                        {/* Time slider */}
                        <div className="flex flex-col items-center gap-1 min-w-[200px]">
                            <input
                                type="range"
                                min={0}
                                max={maxFrames - 1}
                                value={currentFrame}
                                onChange={handleSliderChange}
                                className="w-full h-1.5 bg-gray-700 rounded-full appearance-none cursor-pointer accent-ocean-500"
                            />
                            <div className="flex justify-between w-full text-xs text-gray-400">
                                <span>{currentFrame + 1} / {maxFrames}</span>
                                <span>{getCurrentTimestamp()}</span>
                            </div>
                        </div>
                    </div>
                </motion.div>
            )}

            {/* Animation indicator */}
            <AnimatePresence>
                {isPlaying && (
                    <motion.div
                        className="absolute top-4 left-4 bg-ocean-500/20 backdrop-blur-sm rounded-lg px-3 py-1.5 z-[1000] flex items-center gap-2"
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                    >
                        <div className="w-2 h-2 bg-ocean-400 rounded-full animate-pulse" />
                        <span className="text-xs text-ocean-300 font-medium">Playing at {speed}x</span>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

export default AnimatedTrajectoryMap;
