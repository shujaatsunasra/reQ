'use client';

import React, { useState } from 'react';
import { Download, FileSpreadsheet, Image, FileJson, ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { exportToCSV, exportToPNG, exportToSVG, exportToGeoJSON, exportToJSON } from '@/lib/export-utils';

export interface ExportDropdownProps {
    /** Element ID to capture for PNG/SVG export */
    elementId?: string;
    /** Data array for CSV/JSON/GeoJSON export */
    data?: any[];
    /** Filename prefix for exports */
    filename: string;
    /** Type of content being exported */
    type: 'map' | 'chart' | 'table' | 'data';
    /** Additional class name */
    className?: string;
}

export function ExportDropdown({ elementId, data, filename, type, className = '' }: ExportDropdownProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [isExporting, setIsExporting] = useState(false);

    const handleExport = async (format: string) => {
        setIsExporting(true);
        setIsOpen(false);

        try {
            switch (format) {
                case 'csv':
                    if (data) exportToCSV(data, filename);
                    break;
                case 'png':
                    if (elementId) await exportToPNG(elementId, filename);
                    break;
                case 'svg':
                    if (elementId) exportToSVG(elementId, filename);
                    break;
                case 'geojson':
                    if (data) exportToGeoJSON(data, filename);
                    break;
                case 'json':
                    if (data) exportToJSON(data, filename);
                    break;
            }
        } catch (error) {
            console.error('Export failed:', error);
        } finally {
            setTimeout(() => setIsExporting(false), 500);
        }
    };

    // Define export options based on content type
    const getExportOptions = () => {
        switch (type) {
            case 'map':
                return [
                    { format: 'png', label: 'PNG Image', icon: Image, available: !!elementId },
                    { format: 'geojson', label: 'GeoJSON', icon: FileJson, available: !!data },
                    { format: 'csv', label: 'CSV Data', icon: FileSpreadsheet, available: !!data },
                ];
            case 'chart':
                return [
                    { format: 'png', label: 'PNG Image', icon: Image, available: !!elementId },
                    { format: 'svg', label: 'SVG Vector', icon: FileJson, available: !!elementId },
                    { format: 'csv', label: 'CSV Data', icon: FileSpreadsheet, available: !!data },
                ];
            case 'table':
                return [
                    { format: 'csv', label: 'CSV', icon: FileSpreadsheet, available: !!data },
                    { format: 'json', label: 'JSON', icon: FileJson, available: !!data },
                ];
            case 'data':
            default:
                return [
                    { format: 'csv', label: 'CSV', icon: FileSpreadsheet, available: !!data },
                    { format: 'json', label: 'JSON', icon: FileJson, available: !!data },
                    { format: 'geojson', label: 'GeoJSON', icon: FileJson, available: !!data },
                ];
        }
    };

    const options = getExportOptions().filter(opt => opt.available);

    if (options.length === 0) return null;

    return (
        <div className={`relative ${className}`}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                disabled={isExporting}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors disabled:opacity-50"
            >
                {isExporting ? (
                    <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    >
                        <Download className="w-3.5 h-3.5" />
                    </motion.div>
                ) : (
                    <Download className="w-3.5 h-3.5" />
                )}
                <span>Export</span>
                <ChevronDown className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            <AnimatePresence>
                {isOpen && (
                    <>
                        {/* Backdrop */}
                        <div
                            className="fixed inset-0 z-40"
                            onClick={() => setIsOpen(false)}
                        />

                        {/* Dropdown */}
                        <motion.div
                            initial={{ opacity: 0, y: -8, scale: 0.95 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, y: -8, scale: 0.95 }}
                            transition={{ duration: 0.15 }}
                            className="absolute right-0 top-full mt-1 z-50 min-w-[140px] bg-card border border-border rounded-lg shadow-lg overflow-hidden"
                        >
                            {options.map((option) => (
                                <button
                                    key={option.format}
                                    onClick={() => handleExport(option.format)}
                                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-muted transition-colors"
                                >
                                    <option.icon className="w-4 h-4 text-muted-foreground" />
                                    <span>{option.label}</span>
                                </button>
                            ))}
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
}
