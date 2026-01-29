'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ThumbsUp, ThumbsDown, MessageSquare, X, Send } from 'lucide-react';

interface FeedbackWidgetProps {
    onFeedback?: (type: 'positive' | 'negative', comment?: string) => void;
    visualizationType?: string;
    className?: string;
    compact?: boolean;
}

/**
 * Feedback Widget
 * 
 * Inline feedback component for visualizations:
 * - 👍/👎 quick feedback
 * - Optional comment input on negative feedback
 * - Tracks feedback for AI improvement
 */
export function FeedbackWidget({
    onFeedback,
    visualizationType,
    className = '',
    compact = false,
}: FeedbackWidgetProps) {
    const [feedbackGiven, setFeedbackGiven] = useState<'positive' | 'negative' | null>(null);
    const [showCommentInput, setShowCommentInput] = useState(false);
    const [comment, setComment] = useState('');

    const handleFeedback = (type: 'positive' | 'negative') => {
        setFeedbackGiven(type);

        if (type === 'negative') {
            setShowCommentInput(true);
        } else {
            onFeedback?.(type);
        }
    };

    const handleSubmitComment = () => {
        onFeedback?.('negative', comment);
        setShowCommentInput(false);
        setComment('');
    };

    const handleSkipComment = () => {
        onFeedback?.('negative');
        setShowCommentInput(false);
    };

    if (feedbackGiven && !showCommentInput) {
        return (
            <motion.div
                className={`flex items-center gap-2 text-sm ${className}`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
            >
                <span className={feedbackGiven === 'positive' ? 'text-emerald-400' : 'text-amber-400'}>
                    {feedbackGiven === 'positive' ? '✓ Thanks for the feedback!' : 'Thanks, we\'ll improve this'}
                </span>
            </motion.div>
        );
    }

    return (
        <div className={`relative ${className}`}>
            <AnimatePresence mode="wait">
                {showCommentInput ? (
                    <motion.div
                        key="comment"
                        className="flex flex-col gap-2 bg-gray-800/90 backdrop-blur-sm rounded-lg p-3 border border-gray-700"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                    >
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-300">What could be better?</span>
                            <button
                                onClick={() => setShowCommentInput(false)}
                                className="text-gray-500 hover:text-gray-300"
                            >
                                <X size={16} />
                            </button>
                        </div>

                        <div className="flex flex-wrap gap-2 text-xs">
                            {[
                                'Wrong visualization type',
                                'Missing data',
                                'Too much detail',
                                'Different analysis needed'
                            ].map(option => (
                                <button
                                    key={option}
                                    onClick={() => setComment(option)}
                                    className={`px-2 py-1 rounded-md transition-colors ${comment === option
                                            ? 'bg-ocean-500 text-white'
                                            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                                        }`}
                                >
                                    {option}
                                </button>
                            ))}
                        </div>

                        <div className="flex items-center gap-2">
                            <input
                                type="text"
                                value={comment}
                                onChange={(e) => setComment(e.target.value)}
                                placeholder="Or type your feedback..."
                                className="flex-1 bg-gray-700 text-white text-sm px-3 py-2 rounded-lg border border-gray-600 focus:border-ocean-500 focus:outline-none"
                            />
                            <button
                                onClick={handleSubmitComment}
                                disabled={!comment.trim()}
                                className="p-2 bg-ocean-500 hover:bg-ocean-600 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg transition-colors text-white"
                            >
                                <Send size={16} />
                            </button>
                        </div>

                        <button
                            onClick={handleSkipComment}
                            className="text-xs text-gray-500 hover:text-gray-400 self-end"
                        >
                            Skip
                        </button>
                    </motion.div>
                ) : (
                    <motion.div
                        key="buttons"
                        className={`flex items-center gap-2 ${compact ? '' : 'bg-gray-800/50 backdrop-blur-sm rounded-lg px-3 py-2'}`}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                    >
                        <span className="text-xs text-gray-500">
                            {compact ? '' : 'Was this helpful?'}
                        </span>

                        <button
                            onClick={() => handleFeedback('positive')}
                            className="p-1.5 hover:bg-emerald-500/20 rounded-lg transition-colors group"
                            title="Helpful"
                        >
                            <ThumbsUp
                                size={compact ? 16 : 18}
                                className="text-gray-400 group-hover:text-emerald-400 transition-colors"
                            />
                        </button>

                        <button
                            onClick={() => handleFeedback('negative')}
                            className="p-1.5 hover:bg-amber-500/20 rounded-lg transition-colors group"
                            title="Not helpful"
                        >
                            <ThumbsDown
                                size={compact ? 16 : 18}
                                className="text-gray-400 group-hover:text-amber-400 transition-colors"
                            />
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

export default FeedbackWidget;
