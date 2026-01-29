'use client';

import React, { Suspense, useMemo, useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { motion } from 'framer-motion';

// Dynamically import Plotly to avoid SSR issues
const Plot = dynamic(() => import('react-plotly.js'), { 
  ssr: false,
  loading: () => <VisualizationSkeleton />
});

// Lazy load heavy visualization components
const LeafletMap = dynamic(
  () => import('@/components/visualizations/leaflet-map').then(mod => mod.LeafletMap),
  { ssr: false, loading: () => <VisualizationSkeleton /> }
);

const TimeSeriesChart = dynamic(
  () => import('@/components/visualizations/time-series-chart').then(mod => mod.TimeSeriesChart),
  { ssr: false, loading: () => <VisualizationSkeleton /> }
);

const VerticalProfile = dynamic(
  () => import('@/components/visualizations/vertical-profile').then(mod => mod.VerticalProfile),
  { ssr: false, loading: () => <VisualizationSkeleton /> }
);

const TSDiagram = dynamic(
  () => import('@/components/visualizations/ts-diagram').then(mod => mod.TSDiagram),
  { ssr: false, loading: () => <VisualizationSkeleton /> }
);

// Visualization types
type VisualizationType = 
  | 'trajectory_map'
  | 'heatmap'
  | 'vertical_profile'
  | 'time_series'
  | 'ts_diagram'
  | 'hovmoller'
  | 'scatter'
  | 'bar'
  | 'line'
  | 'qc_dashboard'
  | 'plotly';

interface VisualizationSpec {
  type: string;
  library: string;
  spec: any;
  title?: string;
  subtitle?: string;
  description?: string;
  data?: any;
  layout?: any;
  config?: any;
}

interface VisualizationContainerProps {
  spec: VisualizationSpec;
  height?: number;
  className?: string;
}

// Loading skeleton
function VisualizationSkeleton() {
  return (
    <div className="flex items-center justify-center h-full min-h-[300px] bg-gray-900/30 rounded-xl animate-pulse">
      <div className="flex flex-col items-center gap-3">
        <div className="w-10 h-10 border-2 border-ocean-500/30 border-t-ocean-500 rounded-full animate-spin" />
        <span className="text-sm text-gray-500">Loading visualization...</span>
      </div>
    </div>
  );
}

// Error display
function VisualizationError({ error, type }: { error: string; type: string }) {
  return (
    <motion.div 
      className="flex flex-col items-center justify-center h-full min-h-[300px] bg-red-900/10 rounded-xl border border-red-500/30"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <svg className="w-12 h-12 text-red-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <span className="text-red-400 font-medium">Visualization Error</span>
      <span className="text-sm text-gray-500 mt-1">{error}</span>
      <span className="text-xs text-gray-600 mt-2">Type: {type}</span>
    </motion.div>
  );
}

export function VisualizationContainer({ spec, height = 450, className = '' }: VisualizationContainerProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Memoize Plotly layout with dark theme
  const plotlyLayout = useMemo(() => ({
    ...spec.layout,
    ...spec.spec?.layout,
    autosize: true,
    paper_bgcolor: 'rgba(17, 24, 39, 0.5)',
    plot_bgcolor: 'rgba(17, 24, 39, 0.8)',
    font: { color: '#9ca3af', family: 'Inter, system-ui, sans-serif' },
    margin: { l: 60, r: 40, t: spec.title ? 50 : 30, b: 50 },
    title: spec.title ? {
      text: spec.title,
      font: { size: 16, color: '#f3f4f6' },
    } : undefined,
    xaxis: {
      ...spec.layout?.xaxis,
      ...spec.spec?.layout?.xaxis,
      gridcolor: '#374151',
      linecolor: '#4b5563',
      tickcolor: '#6b7280',
    },
    yaxis: {
      ...spec.layout?.yaxis,
      ...spec.spec?.layout?.yaxis,
      gridcolor: '#374151',
      linecolor: '#4b5563',
      tickcolor: '#6b7280',
    },
    legend: {
      font: { color: '#9ca3af' },
      bgcolor: 'rgba(31, 41, 55, 0.8)',
    },
  }), [spec.layout, spec.spec?.layout, spec.title]);

  const plotlyConfig = useMemo(() => ({
    ...spec.config,
    displayModeBar: true,
    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
    displaylogo: false,
    responsive: true,
    toImageButtonOptions: {
      format: 'png',
      filename: spec.title || 'floatchat_visualization',
      height: 800,
      width: 1200,
      scale: 2,
    },
  }), [spec.config, spec.title]);

  if (!mounted) {
    return <VisualizationSkeleton />;
  }

  const vizData = spec.data || spec.spec;
  const vizType = spec.type as VisualizationType;

  // Render based on visualization type or library
  const renderVisualization = () => {
    try {
      // Handle by type first
      switch (vizType) {
        case 'trajectory_map':
          return (
            <LeafletMap
              data={{
                trajectories: vizData?.trajectories,
                points: vizData?.points,
                center: vizData?.center,
                zoom: vizData?.zoom,
                colorBy: vizData?.colorBy,
              }}
              height={height}
            />
          );

        case 'time_series':
          return (
            <TimeSeriesChart
              data={vizData?.values || vizData}
              series={vizData?.series || [
                { key: 'value', name: 'Value', color: '#3b82f6' }
              ]}
              title={spec.title}
              subtitle={spec.subtitle || spec.description}
              height={height - 50}
              showBrush={vizData?.showBrush !== false}
              showArea={vizData?.showArea}
              referenceLines={vizData?.referenceLines}
            />
          );

        case 'vertical_profile':
          return (
            <VerticalProfile
              data={vizData?.measurements || vizData}
              title={spec.title}
              floatId={vizData?.float_id}
              cycleNumber={vizData?.cycle_number}
              timestamp={vizData?.timestamp}
              showMLD={vizData?.showMLD !== false}
              mldValue={vizData?.mld}
              height={height - 50}
            />
          );

        case 'ts_diagram':
          return (
            <TSDiagram
              data={vizData?.points || vizData}
              title={spec.title}
              showDensityContours={vizData?.showDensityContours !== false}
              showWaterMasses={vizData?.showWaterMasses !== false}
              colorByDepth={vizData?.colorByDepth !== false}
              height={height - 50}
            />
          );
      }

      // Fall back to library-based rendering
      if (spec.library === 'plotly' && vizData) {
        return (
          <div className="bg-gray-900/30 rounded-lg border border-gray-800 overflow-hidden">
            {spec.title && (
              <div className="px-4 py-2 border-b border-gray-800">
                <h3 className="font-medium text-white">{spec.title}</h3>
                {spec.description && (
                  <p className="text-sm text-gray-400">{spec.description}</p>
                )}
              </div>
            )}
            <Plot
              data={vizData.data || vizData.traces || []}
              layout={plotlyLayout}
              config={plotlyConfig}
              style={{ width: '100%', height: `${height}px` }}
              useResizeHandler
            />
          </div>
        );
      }

      if (spec.library === 'leaflet') {
        return (
          <div className="bg-gray-900/30 rounded-lg border border-gray-800 overflow-hidden">
            {spec.title && (
              <div className="px-4 py-2 border-b border-gray-800">
                <h3 className="font-medium text-white">{spec.title}</h3>
              </div>
            )}
            <LeafletMap
              data={vizData}
              height={height}
            />
          </div>
        );
      }

      if (spec.library === 'recharts') {
        return (
          <TimeSeriesChart
            data={vizData?.values || vizData}
            series={vizData?.series || [{ key: 'value', name: 'Value', color: '#3b82f6' }]}
            title={spec.title}
            height={height - 50}
          />
        );
      }

      // Default: try Plotly
      return (
        <div className="bg-gray-900/30 rounded-lg p-4">
          <p className="text-gray-400">
            Unknown visualization type: {spec.type || spec.library}
          </p>
        </div>
      );
    } catch (error) {
      return (
        <VisualizationError 
          error={error instanceof Error ? error.message : 'Unknown error'} 
          type={spec.type || spec.library}
        />
      );
    }
  };

  return (
    <motion.div
      className={`relative ${className}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Suspense fallback={<VisualizationSkeleton />}>
        {renderVisualization()}
      </Suspense>
    </motion.div>
  );
}
