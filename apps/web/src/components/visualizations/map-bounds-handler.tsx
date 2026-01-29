"use client";

import { useEffect, useMemo } from "react";
import { useMap } from "react-leaflet";

interface MapBoundsHandlerProps {
    data: { lat: number; lng: number }[];
    padding?: number;
}

/**
 * Auto-fits map to show all data points with smart bounds calculation
 */
export function MapBoundsHandler({ data, padding = 0.1 }: MapBoundsHandlerProps) {
    const map = useMap();

    const bounds = useMemo(() => {
        if (!data || data.length === 0) return null;

        const validData = data.filter(
            (d) =>
                typeof d.lat === "number" &&
                typeof d.lng === "number" &&
                !isNaN(d.lat) &&
                !isNaN(d.lng) &&
                d.lat >= -90 && d.lat <= 90 &&
                d.lng >= -180 && d.lng <= 180
        );

        if (validData.length === 0) return null;

        let minLat = Infinity;
        let maxLat = -Infinity;
        let minLng = Infinity;
        let maxLng = -Infinity;

        validData.forEach((d) => {
            if (d.lat < minLat) minLat = d.lat;
            if (d.lat > maxLat) maxLat = d.lat;
            if (d.lng < minLng) minLng = d.lng;
            if (d.lng > maxLng) maxLng = d.lng;
        });

        // Add padding
        const latPadding = (maxLat - minLat) * padding;
        const lngPadding = (maxLng - minLng) * padding;

        return {
            southWest: [minLat - latPadding, minLng - lngPadding] as [number, number],
            northEast: [maxLat + latPadding, maxLng + lngPadding] as [number, number],
        };
    }, [data, padding]);

    useEffect(() => {
        if (bounds && map) {
            try {
                map.fitBounds([bounds.southWest, bounds.northEast], {
                    animate: true,
                    duration: 0.5,
                    maxZoom: 8,
                });
            } catch (error) {
                console.warn("Could not fit map bounds:", error);
            }
        }
    }, [bounds, map]);

    return null;
}
