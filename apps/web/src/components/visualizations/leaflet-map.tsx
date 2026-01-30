'use client';

import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Filter, BarChart3, Pencil, Layers, Clock, Maximize2, HelpCircle } from 'lucide-react';
import { FloatHoverCard } from './float-hover-card';

// Lazy load map components to avoid SSR issues
const MapContainer = dynamic(
  () => import('react-leaflet').then((mod) => mod.MapContainer),
  { ssr: false }
);
const TileLayer = dynamic(
  () => import('react-leaflet').then((mod) => mod.TileLayer),
  { ssr: false }
);
const Marker = dynamic(
  () => import('react-leaflet').then((mod) => mod.Marker),
  { ssr: false }
);
const Popup = dynamic(
  () => import('react-leaflet').then((mod) => mod.Popup),
  { ssr: false }
);
const Polyline = dynamic(
  () => import('react-leaflet').then((mod) => mod.Polyline),
  { ssr: false }
);
const CircleMarker = dynamic(
  () => import('react-leaflet').then((mod) => mod.CircleMarker),
  { ssr: false }
);
const Tooltip = dynamic(
  () => import('react-leaflet').then((mod) => mod.Tooltip),
  { ssr: false }
);

interface FloatPosition {
  float_id: string;
  lat: number;
  lon: number;
  timestamp: string;
  cycle_number: number;
  temperature?: number;
  salinity?: number;
  pressure?: number;
  // Anomaly detection fields
  is_anomaly?: boolean;
  anomaly_type?: 'temperature' | 'salinity' | 'both' | null;
  anomaly_score?: number; // 0-1 score for severity
}

interface TrajectoryData {
  float_id: string;
  positions: FloatPosition[];
  color?: string;
}

interface LeafletMapProps {
  data: {
    trajectories?: TrajectoryData[];
    points?: FloatPosition[];
    center?: [number, number];
    zoom?: number;
    showHeatmap?: boolean;
    colorBy?: 'temperature' | 'salinity' | 'depth';
  };
  height?: string | number;
  className?: string;
  // Callbacks for Quick Actions
  onShowProfile?: (floatId: string) => void;
  onShowTrajectory?: (floatId: string) => void;
  onGoToFloatPage?: (floatId: string) => void;
  onAddToCompare?: (floatId: string) => void;
}

// Color scales for oceanographic data
const getTemperatureColor = (temp: number): string => {
  if (temp < 5) return '#0000ff';
  if (temp < 10) return '#0066ff';
  if (temp < 15) return '#00ccff';
  if (temp < 20) return '#00ff99';
  if (temp < 25) return '#ffff00';
  if (temp < 28) return '#ff9900';
  return '#ff0000';
};

const getSalinityColor = (sal: number): string => {
  if (sal < 33) return '#ff6b6b';
  if (sal < 34) return '#ffd93d';
  if (sal < 35) return '#6bcb77';
  if (sal < 36) return '#4d96ff';
  return '#6f3fc8';
};

const getDepthColor = (pressure: number): string => {
  if (pressure < 100) return '#a8e6cf';
  if (pressure < 500) return '#56ab91';
  if (pressure < 1000) return '#3d7c6b';
  if (pressure < 2000) return '#1e4d40';
  return '#0d2520';
};

export function LeafletMap({
  data,
  height = 500,
  className = '',
  onShowProfile,
  onShowTrajectory,
  onGoToFloatPage,
  onAddToCompare
}: LeafletMapProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [selectedFloat, setSelectedFloat] = useState<string | null>(null);
  const [hoveredPoint, setHoveredPoint] = useState<FloatPosition | null>(null);
  const [clickedPoint, setClickedPoint] = useState<FloatPosition | null>(null);
  const [clickPosition, setClickPosition] = useState<{ x: number; y: number } | null>(null);
  const mapRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Default center on Pacific Ocean
  const center = data.center || [0, 180];
  const zoom = data.zoom || 3;

  // Generate trajectory colors
  const trajectoryColors = useMemo(() => {
    const colors = [
      '#3b82f6', '#ef4444', '#22c55e', '#f59e0b', '#8b5cf6',
      '#ec4899', '#14b8a6', '#f97316', '#6366f1', '#84cc16'
    ];
    const colorMap: Record<string, string> = {};
    data.trajectories?.forEach((traj, i) => {
      colorMap[traj.float_id] = traj.color || colors[i % colors.length];
    });
    return colorMap;
  }, [data.trajectories]);

  // Get point color based on colorBy setting or anomaly status
  // Reference design uses blue (#4da6ff) and pink/coral (#ff6b8a) dots
  const getPointColor = (point: FloatPosition): string => {
    // Anomalies get pink/coral highlighting
    if (point.is_anomaly) {
      return '#ff6b8a'; // Pink/coral for anomalies
    }
    if (data.colorBy === 'temperature' && point.temperature !== undefined) {
      // Use blue to pink gradient for temperature
      if (point.temperature < 15) return '#4da6ff'; // Cool - blue
      if (point.temperature < 22) return '#b388ff'; // Medium - purple
      return '#ff6b8a'; // Warm - pink
    }
    if (data.colorBy === 'salinity' && point.salinity !== undefined) {
      return getSalinityColor(point.salinity);
    }
    if (data.colorBy === 'depth' && point.pressure !== undefined) {
      return getDepthColor(point.pressure);
    }
    // Default: randomly assign blue or pink based on some characteristic
    return point.cycle_number % 2 === 0 ? '#4da6ff' : '#ff6b8a';
  };

  // Get marker radius based on anomaly status (anomalies are 3x larger, normal dots are tiny)
  const getMarkerRadius = (point: FloatPosition, isSelected: boolean = false): number => {
    const baseRadius = isSelected ? 4 : 3; // Smaller dots like reference
    if (point.is_anomaly) {
      return baseRadius * 3; // 3x larger for anomalies
    }
    return baseRadius;
  };

  useEffect(() => {
    setIsLoaded(true);
  }, []);

  // Handle marker click - show FloatHoverCard
  const handleMarkerClick = useCallback((point: FloatPosition, event: any) => {
    // Get click position relative to container
    if (containerRef.current && event.originalEvent) {
      const rect = containerRef.current.getBoundingClientRect();
      const x = event.originalEvent.clientX - rect.left;
      const y = event.originalEvent.clientY - rect.top;

      // Adjust position so card doesn't go off screen
      const cardWidth = 288; // w-72 = 18rem = 288px
      const cardHeight = 500; // approximate height
      const adjustedX = Math.min(x, rect.width - cardWidth - 20);
      const adjustedY = Math.min(y, rect.height - cardHeight - 20);

      setClickPosition({ x: Math.max(20, adjustedX), y: Math.max(20, adjustedY) });
    }
    setClickedPoint(point);
  }, []);

  // Close hover card
  const handleCloseHoverCard = useCallback(() => {
    setClickedPoint(null);
    setClickPosition(null);
  }, []);

  if (!isLoaded) {
    return (
      <div
        className={`flex items-center justify-center bg-ocean-900/20 rounded-lg ${className}`}
        style={{ height }}
      >
        <motion.div
          className="flex flex-col items-center gap-3"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <div className="w-8 h-8 border-2 border-ocean-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-ocean-400">Loading map...</span>
        </motion.div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className={`relative ${className}`} style={{ height }} onClick={(e) => { if (e.target === e.currentTarget) handleCloseHoverCard(); }}>
      <MapContainer
        ref={mapRef}
        center={center}
        zoom={zoom}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={true}
        className="z-0"
        zoomControl={false}
      >
        {/* Satellite/Terrain tile layer - ESRI World Imagery */}
        <TileLayer
          attribution='&copy; <a href="https://www.esri.com/">Esri</a> | <a href="https://www.usgs.gov/">USGS</a>'
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        />

        {/* Render trajectories as polylines */}
        {data.trajectories?.map((trajectory) => {
          const positions = trajectory.positions.map((p) => [p.lat, p.lon] as [number, number]);
          const isSelected = selectedFloat === trajectory.float_id;

          return (
            <React.Fragment key={trajectory.float_id}>
              {/* Trajectory line */}
              <Polyline
                positions={positions}
                color={trajectoryColors[trajectory.float_id]}
                weight={isSelected ? 4 : 2}
                opacity={isSelected ? 1 : 0.7}
                dashArray={isSelected ? undefined : '5, 5'}
                eventHandlers={{
                  click: () => setSelectedFloat(trajectory.float_id),
                }}
              />

              {/* Position markers along trajectory */}
              {trajectory.positions.map((pos, idx) => (
                <CircleMarker
                  key={`${trajectory.float_id}-${idx}`}
                  center={[pos.lat, pos.lon]}
                  radius={getMarkerRadius(pos, isSelected)}
                  fillColor={getPointColor(pos)}
                  fillOpacity={pos.is_anomaly ? 1 : 0.8}
                  color={pos.is_anomaly ? '#ffffff' : trajectoryColors[trajectory.float_id]}
                  weight={pos.is_anomaly ? 3 : 1}
                  eventHandlers={{
                    click: (e) => handleMarkerClick(pos, e),
                    mouseover: () => setHoveredPoint(pos),
                    mouseout: () => setHoveredPoint(null),
                  }}
                >
                  <Tooltip>
                    <div className="text-xs">
                      <div className="font-semibold">
                        {pos.float_id}
                        {pos.is_anomaly && (
                          <span className="ml-1 px-1 py-0.5 bg-red-500 text-white text-[10px] rounded">ANOMALY</span>
                        )}
                      </div>
                      <div>Cycle: {pos.cycle_number}</div>
                      <div>Date: {new Date(pos.timestamp).toLocaleDateString()}</div>
                      {pos.temperature && <div>Temp: {pos.temperature.toFixed(2)}°C</div>}
                      {pos.salinity && <div>Sal: {pos.salinity.toFixed(2)} PSU</div>}
                      {pos.is_anomaly && pos.anomaly_type && (
                        <div className="mt-1 text-red-400">
                          ⚠️ {pos.anomaly_type.charAt(0).toUpperCase() + pos.anomaly_type.slice(1)} anomaly
                          {pos.anomaly_score && ` (${Math.round(pos.anomaly_score * 100)}% severity)`}
                        </div>
                      )}
                    </div>
                  </Tooltip>
                </CircleMarker>
              ))}

              {/* Start marker */}
              {positions.length > 0 && (
                <CircleMarker
                  center={positions[0]}
                  radius={8}
                  fillColor="#22c55e"
                  fillOpacity={1}
                  color="#fff"
                  weight={2}
                >
                  <Tooltip permanent={isSelected}>
                    <span className="font-semibold">{trajectory.float_id} (Start)</span>
                  </Tooltip>
                </CircleMarker>
              )}

              {/* End marker */}
              {positions.length > 1 && (
                <CircleMarker
                  center={positions[positions.length - 1]}
                  radius={8}
                  fillColor="#ef4444"
                  fillOpacity={1}
                  color="#fff"
                  weight={2}
                >
                  <Tooltip permanent={isSelected}>
                    <span className="font-semibold">{trajectory.float_id} (Latest)</span>
                  </Tooltip>
                </CircleMarker>
              )}
            </React.Fragment>
          );
        })}

        {/* Render individual points if no trajectories */}
        {!data.trajectories && data.points?.map((point, idx) => (
          <CircleMarker
            key={`point-${idx}`}
            center={[point.lat, point.lon]}
            radius={getMarkerRadius(point)}
            fillColor={getPointColor(point)}
            fillOpacity={point.is_anomaly ? 1 : 0.8}
            color={point.is_anomaly ? '#ffffff' : '#fff'}
            weight={point.is_anomaly ? 3 : 1}
            eventHandlers={{
              click: (e) => handleMarkerClick(point, e),
            }}
          >
            <Tooltip>
              <div className="text-xs">
                <div className="font-semibold">{point.float_id}</div>
                <div>{point.temperature?.toFixed(1)}°C • {point.salinity?.toFixed(1)} PSU</div>
              </div>
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>

      {/* Floating Map Toolbar - Left side, vertical */}
      <motion.div
        className="absolute left-4 top-1/2 -translate-y-1/2 flex flex-col gap-2 z-[1000]"
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.2 }}
      >
        {[
          { icon: Search, label: 'Search floats' },
          { icon: Filter, label: 'Filter data' },
          { icon: BarChart3, label: 'View charts' },
          { icon: Pencil, label: 'Draw/annotate' },
          { icon: Layers, label: 'Toggle layers' },
          { icon: Clock, label: 'Time slider' },
          { icon: Maximize2, label: 'Fullscreen' },
          { icon: HelpCircle, label: 'Help' },
        ].map(({ icon: Icon, label }) => (
          <motion.button
            key={label}
            whileHover={{ scale: 1.1, x: 4 }}
            whileTap={{ scale: 0.95 }}
            className="w-10 h-10 rounded-xl bg-gray-900/90 backdrop-blur-sm flex items-center justify-center text-gray-300 hover:bg-primary/90 hover:text-white transition-colors shadow-lg border border-gray-700/50"
            title={label}
          >
            <Icon className="w-5 h-5" />
          </motion.button>
        ))}
      </motion.div>

      {/* Float selection legend */}
      {data.trajectories && data.trajectories.length > 0 && (
        <motion.div
          className="absolute top-4 right-4 bg-gray-900/90 backdrop-blur-sm rounded-lg p-3 z-[1000] max-h-60 overflow-y-auto"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <div className="text-xs font-semibold text-gray-400 mb-2">Float Trajectories</div>
          <div className="space-y-1">
            {data.trajectories.map((traj) => (
              <button
                key={traj.float_id}
                onClick={() => setSelectedFloat(
                  selectedFloat === traj.float_id ? null : traj.float_id
                )}
                className={`flex items-center gap-2 w-full px-2 py-1 rounded text-xs transition-colors ${selectedFloat === traj.float_id
                  ? 'bg-ocean-500/30 text-ocean-300'
                  : 'hover:bg-gray-800 text-gray-300'
                  }`}
              >
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: trajectoryColors[traj.float_id] }}
                />
                <span>{traj.float_id}</span>
                <span className="text-gray-500 ml-auto">
                  {traj.positions.length} pts
                </span>
              </button>
            ))}
          </div>
        </motion.div>
      )}

      {/* Color scale legend */}
      {data.colorBy && (
        <motion.div
          className="absolute bottom-4 left-4 bg-gray-900/90 backdrop-blur-sm rounded-lg p-3 z-[1000]"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="text-xs font-semibold text-gray-400 mb-2">
            {data.colorBy === 'temperature' ? 'Temperature (°C)' :
              data.colorBy === 'salinity' ? 'Salinity (PSU)' : 'Depth (dbar)'}
          </div>
          <div className="flex items-center gap-1">
            {data.colorBy === 'temperature' && (
              <>
                <span className="text-xs text-gray-500">0</span>
                <div className="h-3 w-24 rounded" style={{
                  background: 'linear-gradient(to right, #0000ff, #0066ff, #00ccff, #00ff99, #ffff00, #ff9900, #ff0000)'
                }} />
                <span className="text-xs text-gray-500">30</span>
              </>
            )}
            {data.colorBy === 'salinity' && (
              <>
                <span className="text-xs text-gray-500">32</span>
                <div className="h-3 w-24 rounded" style={{
                  background: 'linear-gradient(to right, #ff6b6b, #ffd93d, #6bcb77, #4d96ff, #6f3fc8)'
                }} />
                <span className="text-xs text-gray-500">37</span>
              </>
            )}
            {data.colorBy === 'depth' && (
              <>
                <span className="text-xs text-gray-500">0</span>
                <div className="h-3 w-24 rounded" style={{
                  background: 'linear-gradient(to right, #a8e6cf, #56ab91, #3d7c6b, #1e4d40, #0d2520)'
                }} />
                <span className="text-xs text-gray-500">2000</span>
              </>
            )}
          </div>
        </motion.div>
      )}

      {/* Hovered point info */}
      <AnimatePresence>
        {hoveredPoint && (
          <motion.div
            className="absolute bottom-4 right-4 bg-gray-900/90 backdrop-blur-sm rounded-lg p-3 z-[1000]"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
          >
            <div className="text-xs">
              <div className="font-semibold text-ocean-400">{hoveredPoint.float_id}</div>
              <div className="text-gray-400">
                {hoveredPoint.lat.toFixed(3)}°, {hoveredPoint.lon.toFixed(3)}°
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* FloatHoverCard overlay - appears on marker click */}
      <AnimatePresence>
        {clickedPoint && clickPosition && (
          <div
            className="absolute z-[2000]"
            style={{ left: clickPosition.x, top: clickPosition.y }}
          >
            <FloatHoverCard
              data={{
                float_id: clickedPoint.float_id,
                cycle_number: clickedPoint.cycle_number,
                lat: clickedPoint.lat,
                lng: clickedPoint.lon,
                temperature: clickedPoint.temperature,
                salinity: clickedPoint.salinity,
                depth: clickedPoint.pressure,
                date: clickedPoint.timestamp,
                qc_flag: (clickedPoint as any).qc_flag,
                is_anomaly: clickedPoint.is_anomaly,
                anomaly_type: clickedPoint.anomaly_type ?? undefined,
                anomaly_score: clickedPoint.anomaly_score,
              }}
              onClose={handleCloseHoverCard}
              onShowProfile={(floatId) => {
                onShowProfile?.(floatId);
                handleCloseHoverCard();
              }}
              onShowTrajectory={(floatId) => {
                onShowTrajectory?.(floatId);
                handleCloseHoverCard();
              }}
              onGoToFloatPage={(floatId) => {
                onGoToFloatPage?.(floatId);
                handleCloseHoverCard();
              }}
              onAddToCompare={(floatId) => {
                onAddToCompare?.(floatId);
                handleCloseHoverCard();
              }}
            />
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default LeafletMap;
