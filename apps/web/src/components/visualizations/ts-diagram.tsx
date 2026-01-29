'use client';

import React, { useMemo, useState } from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ZAxis,
} from 'recharts';
import { motion } from 'framer-motion';

interface TSDataPoint {
  temperature: number;
  salinity: number;
  pressure?: number;
  density?: number;
  float_id?: string;
  cycle_number?: number;
}

interface TSDiagramProps {
  data: TSDataPoint[];
  title?: string;
  showDensityContours?: boolean;
  showWaterMasses?: boolean;
  colorByDepth?: boolean;
  height?: number;
  className?: string;
}

// Water mass definitions (T-S properties)
const WATER_MASSES = [
  { name: 'AAIW', T: [3, 6], S: [34.2, 34.5], color: '#3b82f6' },  // Antarctic Intermediate Water
  { name: 'NADW', T: [2, 4], S: [34.9, 35.0], color: '#ef4444' },  // North Atlantic Deep Water
  { name: 'AABW', T: [-0.5, 2], S: [34.6, 34.7], color: '#22c55e' },  // Antarctic Bottom Water
  { name: 'MW', T: [11, 13], S: [35.5, 36.5], color: '#f59e0b' },  // Mediterranean Water
  { name: 'SAMW', T: [8, 15], S: [34.5, 35.5], color: '#8b5cf6' },  // Subantarctic Mode Water
];

// Calculate potential density (sigma-theta) simplified
const calculateDensity = (T: number, S: number): number => {
  // Simplified UNESCO equation
  const rho0 = 999.842594;
  const a1 = 6.793952e-2;
  const a2 = -9.095290e-3;
  const a3 = 1.001685e-4;
  const b1 = 8.244930e-1;
  const b2 = -4.089140e-3;
  
  const rhoFresh = rho0 + a1 * T + a2 * T ** 2 + a3 * T ** 3;
  const rho = rhoFresh + (b1 + b2 * T) * S;
  
  return rho - 1000;  // sigma-theta
};

// Get color based on depth
const getDepthColor = (pressure?: number): string => {
  if (!pressure) return '#6b7280';
  if (pressure < 100) return '#fcd34d';
  if (pressure < 500) return '#fb923c';
  if (pressure < 1000) return '#f87171';
  if (pressure < 2000) return '#a855f7';
  return '#3b82f6';
};

export function TSDiagram({
  data,
  title = 'T-S Diagram',
  showDensityContours = true,
  showWaterMasses = true,
  colorByDepth = true,
  height = 450,
  className = '',
}: TSDiagramProps) {
  const [hoveredPoint, setHoveredPoint] = useState<TSDataPoint | null>(null);

  // Calculate T-S bounds
  const bounds = useMemo(() => {
    const temps = data.map((d) => d.temperature);
    const sals = data.map((d) => d.salinity);
    return {
      tempMin: Math.floor(Math.min(...temps)) - 1,
      tempMax: Math.ceil(Math.max(...temps)) + 1,
      salMin: Math.floor(Math.min(...sals) * 10) / 10 - 0.2,
      salMax: Math.ceil(Math.max(...sals) * 10) / 10 + 0.2,
    };
  }, [data]);

  // Generate density contour lines
  const densityContours = useMemo(() => {
    if (!showDensityContours) return [];
    
    const contours: { sigma: number; points: { x: number; y: number }[] }[] = [];
    const sigmaValues = [24, 25, 26, 27, 28, 29];
    
    sigmaValues.forEach((sigma) => {
      const points: { x: number; y: number }[] = [];
      for (let S = bounds.salMin; S <= bounds.salMax; S += 0.1) {
        // Solve for T given S and sigma (simplified)
        for (let T = bounds.tempMin; T <= bounds.tempMax; T += 0.5) {
          if (Math.abs(calculateDensity(T, S) - sigma) < 0.2) {
            points.push({ x: S, y: T });
            break;
          }
        }
      }
      if (points.length > 2) {
        contours.push({ sigma, points });
      }
    });
    
    return contours;
  }, [bounds, showDensityContours]);

  // Prepare data with colors
  const chartData = useMemo(() => {
    return data.map((d, i) => ({
      ...d,
      fill: colorByDepth ? getDepthColor(d.pressure) : '#3b82f6',
      z: d.pressure || 100,
    }));
  }, [data, colorByDepth]);

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || !payload.length) return null;

    const point = payload[0].payload as TSDataPoint;

    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-gray-900/95 backdrop-blur-sm rounded-lg p-3 border border-ocean-500/30 shadow-xl"
      >
        <div className="space-y-1 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-gray-400">Temperature:</span>
            <span className="font-medium text-red-400">{point.temperature.toFixed(2)}°C</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-400">Salinity:</span>
            <span className="font-medium text-blue-400">{point.salinity.toFixed(3)} PSU</span>
          </div>
          {point.pressure && (
            <div className="flex items-center gap-2">
              <span className="text-gray-400">Pressure:</span>
              <span className="font-medium text-purple-400">{point.pressure.toFixed(0)} dbar</span>
            </div>
          )}
          <div className="flex items-center gap-2">
            <span className="text-gray-400">σ-θ:</span>
            <span className="font-medium text-green-400">
              {calculateDensity(point.temperature, point.salinity).toFixed(2)} kg/m³
            </span>
          </div>
          {point.float_id && (
            <div className="text-xs text-gray-500 pt-1 border-t border-gray-700">
              {point.float_id} {point.cycle_number && `(Cycle ${point.cycle_number})`}
            </div>
          )}
        </div>
      </motion.div>
    );
  };

  return (
    <motion.div
      className={`bg-gray-900/30 rounded-xl p-4 ${className}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          <p className="text-sm text-gray-400">Temperature-Salinity relationship</p>
        </div>
        <div className="text-xs text-gray-500">
          {data.length} points
        </div>
      </div>

      {/* Chart container with density contours as background */}
      <div className="relative">
        {/* Density contour labels (SVG overlay would be better) */}
        {showDensityContours && (
          <div className="absolute top-2 right-2 bg-gray-800/80 rounded px-2 py-1 text-xs text-gray-400">
            σ-θ contours
          </div>
        )}

        <ResponsiveContainer width="100%" height={height}>
          <ScatterChart margin={{ top: 20, right: 20, bottom: 40, left: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            
            <XAxis
              type="number"
              dataKey="salinity"
              domain={[bounds.salMin, bounds.salMax]}
              stroke="#6b7280"
              tick={{ fill: '#9ca3af', fontSize: 11 }}
              tickLine={{ stroke: '#4b5563' }}
              axisLine={{ stroke: '#4b5563' }}
              label={{
                value: 'Salinity (PSU)',
                position: 'bottom',
                offset: -5,
                style: { fill: '#9ca3af', fontSize: 12 },
              }}
            />
            
            <YAxis
              type="number"
              dataKey="temperature"
              domain={[bounds.tempMin, bounds.tempMax]}
              stroke="#6b7280"
              tick={{ fill: '#9ca3af', fontSize: 11 }}
              tickLine={{ stroke: '#4b5563' }}
              axisLine={{ stroke: '#4b5563' }}
              label={{
                value: 'Temperature (°C)',
                angle: -90,
                position: 'insideLeft',
                style: { fill: '#9ca3af', fontSize: 12 },
              }}
            />

            <ZAxis type="number" dataKey="z" range={[30, 150]} />

            <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />

            <Scatter
              data={chartData}
              shape="circle"
              animationDuration={800}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* Legends */}
      <div className="mt-4 flex flex-wrap gap-6">
        {/* Depth color legend */}
        {colorByDepth && (
          <div>
            <div className="text-xs text-gray-400 mb-1">Depth (dbar)</div>
            <div className="flex items-center gap-1">
              <span className="text-xs text-gray-500">0</span>
              <div className="flex h-3">
                <div className="w-6 bg-yellow-400 rounded-l" />
                <div className="w-6 bg-orange-400" />
                <div className="w-6 bg-red-400" />
                <div className="w-6 bg-purple-500" />
                <div className="w-6 bg-blue-500 rounded-r" />
              </div>
              <span className="text-xs text-gray-500">2000+</span>
            </div>
          </div>
        )}

        {/* Water mass legend */}
        {showWaterMasses && (
          <div>
            <div className="text-xs text-gray-400 mb-1">Water Masses</div>
            <div className="flex flex-wrap gap-2">
              {WATER_MASSES.map((wm) => (
                <div key={wm.name} className="flex items-center gap-1">
                  <div
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: wm.color }}
                  />
                  <span className="text-xs text-gray-500">{wm.name}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-gray-800/50 rounded-lg p-2 text-center">
          <div className="text-xs text-gray-400">Temp Range</div>
          <div className="text-sm font-medium text-red-400">
            {bounds.tempMin.toFixed(1)} - {bounds.tempMax.toFixed(1)}°C
          </div>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-2 text-center">
          <div className="text-xs text-gray-400">Salinity Range</div>
          <div className="text-sm font-medium text-blue-400">
            {bounds.salMin.toFixed(2)} - {bounds.salMax.toFixed(2)} PSU
          </div>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-2 text-center">
          <div className="text-xs text-gray-400">σ-θ Range</div>
          <div className="text-sm font-medium text-green-400">
            {Math.min(...data.map((d) => calculateDensity(d.temperature, d.salinity))).toFixed(2)} -
            {Math.max(...data.map((d) => calculateDensity(d.temperature, d.salinity))).toFixed(2)}
          </div>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-2 text-center">
          <div className="text-xs text-gray-400">Depth Range</div>
          <div className="text-sm font-medium text-purple-400">
            {data.some((d) => d.pressure)
              ? `${Math.min(...data.filter((d) => d.pressure).map((d) => d.pressure!)).toFixed(0)} - 
                 ${Math.max(...data.filter((d) => d.pressure).map((d) => d.pressure!)).toFixed(0)} dbar`
              : 'N/A'}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export default TSDiagram;
