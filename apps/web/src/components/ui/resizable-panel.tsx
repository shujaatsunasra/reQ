"use client";

import { useState, useRef, useCallback, useEffect, ReactNode } from "react";
import { motion } from "framer-motion";
import { GripVertical } from "lucide-react";

interface ResizablePanelProps {
    children: ReactNode;
    defaultWidth?: number;
    minWidth?: number;
    maxWidth?: number;
    storageKey?: string;
    side?: "left" | "right";
    className?: string;
    onWidthChange?: (width: number) => void;
}

export function ResizablePanel({
    children,
    defaultWidth = 400,
    minWidth = 300,
    maxWidth = 800,
    storageKey,
    side = "right",
    className = "",
    onWidthChange,
}: ResizablePanelProps) {
    const [width, setWidth] = useState(() => {
        if (storageKey && typeof window !== "undefined") {
            const saved = localStorage.getItem(storageKey);
            if (saved) {
                const parsed = parseInt(saved, 10);
                if (!isNaN(parsed) && parsed >= minWidth && parsed <= maxWidth) {
                    return parsed;
                }
            }
        }
        return defaultWidth;
    });

    const [isResizing, setIsResizing] = useState(false);
    const panelRef = useRef<HTMLDivElement>(null);
    const startXRef = useRef(0);
    const startWidthRef = useRef(0);

    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        setIsResizing(true);
        startXRef.current = e.clientX;
        startWidthRef.current = width;
    }, [width]);

    const handleMouseMove = useCallback((e: MouseEvent) => {
        if (!isResizing) return;

        const delta = side === "right"
            ? startXRef.current - e.clientX
            : e.clientX - startXRef.current;

        const newWidth = Math.max(minWidth, Math.min(maxWidth, startWidthRef.current + delta));
        setWidth(newWidth);
        onWidthChange?.(newWidth);
    }, [isResizing, side, minWidth, maxWidth, onWidthChange]);

    const handleMouseUp = useCallback(() => {
        if (isResizing) {
            setIsResizing(false);
            if (storageKey) {
                localStorage.setItem(storageKey, width.toString());
            }
        }
    }, [isResizing, storageKey, width]);

    useEffect(() => {
        if (isResizing) {
            document.addEventListener("mousemove", handleMouseMove);
            document.addEventListener("mouseup", handleMouseUp);
            document.body.style.cursor = "col-resize";
            document.body.style.userSelect = "none";
        }

        return () => {
            document.removeEventListener("mousemove", handleMouseMove);
            document.removeEventListener("mouseup", handleMouseUp);
            document.body.style.cursor = "";
            document.body.style.userSelect = "";
        };
    }, [isResizing, handleMouseMove, handleMouseUp]);

    return (
        <motion.div
            ref={panelRef}
            animate={{ width }}
            transition={isResizing ? { duration: 0 } : { type: "spring", stiffness: 300, damping: 30 }}
            className={`relative flex shrink-0 ${className}`}
            style={{ width }}
        >
            {/* Resize Handle */}
            <div
                onMouseDown={handleMouseDown}
                className={`absolute top-0 bottom-0 w-1 cursor-col-resize group z-10 ${side === "right" ? "left-0 -ml-0.5" : "right-0 -mr-0.5"
                    }`}
            >
                <div className={`absolute inset-y-0 ${side === "right" ? "left-0" : "right-0"} w-1 transition-colors ${isResizing ? "bg-primary" : "bg-transparent group-hover:bg-primary/50"
                    }`} />
                <div className={`absolute top-1/2 -translate-y-1/2 ${side === "right" ? "-left-2" : "-right-2"} opacity-0 group-hover:opacity-100 transition-opacity`}>
                    <GripVertical className="w-4 h-4 text-muted-foreground" />
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-hidden">
                {children}
            </div>
        </motion.div>
    );
}
