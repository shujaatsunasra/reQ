"use client";

import { memo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    Plus,
    MessageSquare,
    Trash2,
    PanelLeftClose,
    PanelLeft,
    Settings,
    Moon,
    Sun,
    Sparkles,
} from "lucide-react";
import { useAppStore } from "@/store/app-store";
import { useTheme } from "next-themes";
import { formatDistanceToNow } from "date-fns";

interface SidebarProps {
    isOpen: boolean;
    onToggle: () => void;
    onNewChat: () => void;
    onOpenSettings: () => void;
}

function SidebarComponent({ isOpen, onToggle, onNewChat, onOpenSettings }: SidebarProps) {
    const {
        conversations,
        activeConversationId,
        setActiveConversation,
        deleteConversation,
        createConversation
    } = useAppStore();
    const { theme, setTheme } = useTheme();

    const handleNewChat = useCallback(() => {
        createConversation();
        onNewChat();
    }, [createConversation, onNewChat]);

    const handleDeleteConversation = useCallback((e: React.MouseEvent, id: string) => {
        e.stopPropagation();
        deleteConversation(id);
    }, [deleteConversation]);

    const toggleTheme = useCallback(() => {
        setTheme(theme === "dark" ? "light" : "dark");
    }, [theme, setTheme]);

    return (
        <div className="h-full flex shrink-0">
            {/* Collapsed Icon Bar - Shows when sidebar is closed */}
            <AnimatePresence>
                {!isOpen && (
                    <motion.div
                        initial={{ width: 0, opacity: 0 }}
                        animate={{ width: 48, opacity: 1 }}
                        exit={{ width: 0, opacity: 0 }}
                        transition={{ duration: 0.15 }}
                        className="h-full flex flex-col items-center py-3 bg-card border-r overflow-hidden"
                    >
                        {/* Toggle Button */}
                        <button
                            onClick={onToggle}
                            className="p-2 mb-2 hover:bg-muted rounded-lg transition-colors"
                            title="Expand sidebar"
                        >
                            <PanelLeft className="w-5 h-5" />
                        </button>

                        {/* New Chat */}
                        <button
                            onClick={handleNewChat}
                            className="p-2 mb-1 hover:bg-muted rounded-lg transition-colors"
                            title="New chat"
                        >
                            <Plus className="w-5 h-5" />
                        </button>

                        {/* Chats */}
                        <button
                            onClick={onToggle}
                            className="p-2 mb-1 hover:bg-muted rounded-lg transition-colors"
                            title="View chats"
                        >
                            <MessageSquare className="w-5 h-5" />
                        </button>

                        {/* Spacer */}
                        <div className="flex-1" />

                        {/* Theme Toggle */}
                        <button
                            onClick={toggleTheme}
                            className="p-2 mb-1 hover:bg-muted rounded-lg transition-colors"
                            title={theme === "dark" ? "Light mode" : "Dark mode"}
                        >
                            {theme === "dark" ? (
                                <Sun className="w-5 h-5" />
                            ) : (
                                <Moon className="w-5 h-5" />
                            )}
                        </button>

                        {/* Settings */}
                        <button
                            onClick={onOpenSettings}
                            className="p-2 mb-2 hover:bg-muted rounded-lg transition-colors"
                            title="Settings"
                        >
                            <Settings className="w-5 h-5" />
                        </button>

                        {/* User Avatar */}
                        <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary font-medium text-sm">
                            S
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Expanded Sidebar */}
            <AnimatePresence mode="wait">
                {isOpen && (
                    <motion.aside
                        initial={{ width: 0, opacity: 0 }}
                        animate={{ width: 280, opacity: 1 }}
                        exit={{ width: 0, opacity: 0 }}
                        transition={{ type: "spring", stiffness: 300, damping: 30 }}
                        className="h-full bg-card border-r flex flex-col overflow-hidden"
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between p-4 border-b">
                            <div className="flex items-center gap-2">
                                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center shadow-sm">
                                    <Sparkles className="w-4 h-4 text-primary-foreground" />
                                </div>
                                <span className="font-semibold text-lg">Vortex</span>
                            </div>
                            <button
                                onClick={onToggle}
                                className="p-1.5 hover:bg-muted rounded-lg transition-colors"
                                title="Close sidebar"
                            >
                                <PanelLeftClose className="w-4 h-4" />
                            </button>
                        </div>

                        {/* New Chat Button */}
                        <div className="p-3">
                            <motion.button
                                onClick={handleNewChat}
                                whileHover={{ scale: 1.01 }}
                                whileTap={{ scale: 0.99 }}
                                className="w-full flex items-center gap-2 px-4 py-3 bg-primary text-primary-foreground rounded-xl font-medium hover:bg-primary/90 transition-all"
                            >
                                <Plus className="w-4 h-4" />
                                New Chat
                            </motion.button>
                        </div>

                        {/* Navigation Items */}
                        <div className="px-3 space-y-1">
                            <button className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted rounded-lg transition-colors bg-muted">
                                <MessageSquare className="w-4 h-4" />
                                <span>Chats</span>
                            </button>
                        </div>

                        {/* Conversations List */}
                        <div className="flex-1 overflow-y-auto px-3 pb-3 mt-2">
                            <p className="text-xs font-medium text-muted-foreground px-2 mb-2">
                                Recents
                            </p>

                            {conversations.length === 0 ? (
                                <div className="text-center py-8 text-muted-foreground">
                                    <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                    <p className="text-sm">No conversations yet</p>
                                    <p className="text-xs mt-1">Start a new chat to begin</p>
                                </div>
                            ) : (
                                <div className="space-y-1">
                                    {conversations.map((conv) => (
                                        <motion.div
                                            key={conv.id}
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            className={`group relative flex items-center gap-2 px-3 py-2.5 rounded-xl cursor-pointer transition-all ${activeConversationId === conv.id
                                                ? "bg-muted"
                                                : "hover:bg-muted/50"
                                                }`}
                                            onClick={() => setActiveConversation(conv.id)}
                                        >
                                            <MessageSquare className="w-4 h-4 shrink-0 text-muted-foreground" />
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-medium truncate">
                                                    {conv.title || "New Conversation"}
                                                </p>
                                                <p className="text-[10px] text-muted-foreground">
                                                    {formatDistanceToNow(new Date(conv.updatedAt), { addSuffix: true })}
                                                </p>
                                            </div>
                                            <button
                                                onClick={(e) => handleDeleteConversation(e, conv.id)}
                                                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-destructive/10 hover:text-destructive rounded transition-all"
                                                title="Delete conversation"
                                            >
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </button>
                                        </motion.div>
                                    ))}
                                </div>
                            )}
                        </div>

                    </motion.aside>
                )}
            </AnimatePresence>
        </div>
    );
}

export const Sidebar = memo(SidebarComponent);
