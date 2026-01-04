"use client";

import React, { useState, useRef, useEffect } from 'react';
import ClaudeChatInput from '../components/ui/claude-style-chat-input';
import { FileText, Loader2, Code, Archive } from 'lucide-react';

const Icons = {
    FileText,
    Loader2,
    Code,
    Archive
};

interface UserProfile {
    allergies: string[];
    conditions: string[];
    goals: string[];
}

const ChatboxDemo = () => {
    const [messages, setMessages] = useState<Array<{
        id: string;
        message: string;
        timestamp: Date;
        role: 'user' | 'assistant';
    }>>([]);
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const messagesContainerRef = useRef<HTMLDivElement>(null);

    // User Profile State - You can load this from localStorage, API, or props
    // TODO: Replace with actual user profile from your auth system or API
    const [userProfile] = useState<UserProfile>({
        allergies: ['Peanuts', 'Dairy'],
        conditions: ['Diabetes Type 2', 'Hypertension'],
        goals: ['Weight loss', 'Better sleep', 'Lower blood sugar']
    });

    // Example: Load from localStorage
    // useEffect(() => {
    //     const savedProfile = localStorage.getItem('userProfile');
    //     if (savedProfile) {
    //         setUserProfile(JSON.parse(savedProfile));
    //     }
    // }, []);

    const handleSendMessage = async (data: {
        message: string;
        files: any[];
        pastedContent: any[];
        model: string;
        isThinkingEnabled: boolean;
    }) => {
        // Access the message and other data here
        const userMessage = data.message;
        const attachedFiles = data.files;
        const pastedContent = data.pastedContent;
        const selectedModel = data.model;
        const thinkingEnabled = data.isThinkingEnabled;

        // Console log to see the message
        console.log('=== USER MESSAGE ===');
        console.log('Message:', userMessage);
        console.log('Full data:', data);

        // Add user message to display
        const userMsgId = Date.now().toString();
        if (userMessage.trim() || attachedFiles.length > 0 || pastedContent.length > 0) {
            setMessages(prev => [...prev, {
                id: userMsgId,
                message: userMessage || (attachedFiles.length > 0 ? `Sent ${attachedFiles.length} file(s)` : 'Sent pasted content'),
                timestamp: new Date(),
                role: 'user'
            }]);
        }

        // Show loading state
        setIsLoading(true);

        // Convert files to base64 for sending
        const processFiles = async () => {
            const processedFiles = await Promise.all(
                attachedFiles.map(async (f) => {
                    // For images, use the preview (data URL) if available
                    if (f.type.startsWith("image/") && f.preview) {
                        return {
                            name: f.file.name,
                            type: f.file.type,
                            size: f.file.size,
                            content: f.preview, // Data URL (base64 encoded image)
                            isImage: true
                        };
                    }
                    // For other files, convert to base64
                    return new Promise<{
                        name: string;
                        type: string;
                        size: number;
                        content: string;
                        isImage: boolean;
                    }>((resolve, reject) => {
                        const reader = new FileReader();
                        reader.onload = () => {
                            resolve({
                                name: f.file.name,
                                type: f.file.type,
                                size: f.file.size,
                                content: reader.result as string, // Base64 string
                                isImage: false
                            });
                        };
                        reader.onerror = reject;
                        reader.readAsDataURL(f.file);
                    });
                })
            );
            return processedFiles;
        };

        // Prepare the request payload with message and user profile
        const processedFiles = await processFiles();
        const requestPayload = {
            // User's message/prompt
            message: userMessage,
            
            // User profile data - sent with every request
            userProfile: {
                allergies: userProfile.allergies,
                conditions: userProfile.conditions,
                goals: userProfile.goals
            },
            
            // Additional context
            model: selectedModel,
            thinkingEnabled: thinkingEnabled,
            
            // Files with actual content (base64 encoded)
            files: processedFiles,
            
            // Pasted content
            pastedContent: pastedContent.map(p => p.content),
        };

        // Log the complete payload being sent to server
        console.log('=== COMPLETE REQUEST PAYLOAD ===');
        console.log('Message:', userMessage);
        console.log('User Profile:', userProfile);
        console.log('Model:', selectedModel);
        console.log('Full Payload:', JSON.stringify(requestPayload, null, 2));

        // Send to your server/LLM API
        // TODO: Replace with your actual backend endpoint URL
        // Current endpoint: '/api/chat' (relative URL - sends to same domain)
        // Examples:
        //   - '/api/chat' (Next.js API route)
        //   - 'http://localhost:8000/api/chat' (local backend)
        //   - 'https://your-backend.com/api/chat' (production backend)
        const API_ENDPOINT = '/api/chat'; // 👈 CHANGE THIS TO YOUR BACKEND URL
        
        try {
            const response = await fetch(API_ENDPOINT, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    // Add authentication if needed
                    // 'Authorization': `Bearer ${yourAuthToken}`,
                },
                body: JSON.stringify(requestPayload),
            });

            if (response.ok) {
                const aiResponse = await response.json();
                // Handle AI response here
                console.log('AI Response:', aiResponse);
                
                // Add AI response to messages
                setMessages(prev => [...prev, {
                    id: (Date.now() + 1).toString(),
                    message: aiResponse.message || aiResponse.response || aiResponse.text || aiResponse.content || 'I received your message.',
                    timestamp: new Date(),
                    role: 'assistant'
                }]);
            } else {
                // If API fails, show error with details
                const errorText = await response.text();
                console.error('API Error:', response.status, errorText);
                
                setMessages(prev => [...prev, {
                    id: (Date.now() + 1).toString(),
                    message: `API Error (${response.status}): ${response.statusText}. Please check your backend endpoint at ${API_ENDPOINT}`,
                    timestamp: new Date(),
                    role: 'assistant'
                }]);
            }
        } catch (error) {
            console.error('Error sending message to LLM:', error);
            
            // Check if it's a network error (API endpoint not found)
            const errorMessage = error instanceof TypeError && error.message.includes('fetch')
                ? `Network error: Could not reach ${API_ENDPOINT}. Please ensure your backend server is running and the endpoint is correct.`
                : `Error: ${error instanceof Error ? error.message : 'Unknown error occurred'}`;
            
            setMessages(prev => [...prev, {
                id: (Date.now() + 1).toString(),
                message: errorMessage,
                timestamp: new Date(),
                role: 'assistant'
            }]);
        } finally {
            setIsLoading(false);
        }

        // For now, just log the data
        console.log('User message:', userMessage);
        console.log('Attached files:', attachedFiles);
        console.log('Pasted content:', pastedContent);
        console.log('Selected model:', selectedModel);
        console.log('Thinking enabled:', thinkingEnabled);
    };

    const currentHour = new Date().getHours();
    let greeting = 'Good morning';
    if (currentHour >= 12 && currentHour < 18) {
        greeting = 'Good afternoon';
    } else if (currentHour >= 18) {
        greeting = 'Good evening';
    }

    const userName = 'Saify';

    // Auto-scroll to bottom when new messages appear
    useEffect(() => {
        const scrollToBottom = () => {
            if (messagesEndRef.current) {
                messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
            }
        };
        
        // Small delay to ensure DOM is updated
        const timeoutId = setTimeout(scrollToBottom, 100);
        
        return () => clearTimeout(timeoutId);
    }, [messages, isLoading]);

    return (
        <div className="min-h-screen w-full bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/20 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 flex flex-col items-center justify-center p-4 font-sans text-text-100 transition-colors duration-200">

            {/* Greeting Section */}
            <div className="w-full max-w-3xl mb-8 sm:mb-12 text-center animate-fade-in">
                <div className="w-20 h-20 mx-auto mb-6 flex items-center justify-center bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl shadow-lg">
                    <span className="text-3xl font-bold text-white">AI</span>
                </div>
                <h1 className="text-4xl sm:text-5xl font-bold text-text-100 mb-3 tracking-tight bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-400 dark:to-purple-400 bg-clip-text text-transparent">
                    {greeting}, {userName}!
                </h1>
                <p className="text-lg text-text-300 dark:text-text-400">How can I assist you today?</p>
            </div>

            {/* Messages Display */}
            {messages.length > 0 && (
                <div 
                    ref={messagesContainerRef}
                    className="w-full max-w-2xl mx-auto mb-4 space-y-3 animate-fade-in"
                >
                    {messages.map((msg) => (
                        <div
                            key={msg.id}
                            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div className={`bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm border border-bg-300 dark:border-slate-700 rounded-xl p-4 shadow-md max-w-[80%] ${
                                msg.role === 'user' ? 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200 dark:border-indigo-800' : ''
                            }`}>
                                <div className={`flex items-start mb-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                    <span className="text-xs text-text-400 dark:text-text-500">
                                        {msg.role === 'assistant' && <span className="font-semibold text-indigo-600 dark:text-indigo-400 mr-2">AI:</span>}
                                        {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </span>
                                </div>
                                <p className={`text-slate-800 dark:text-slate-100 text-sm leading-relaxed whitespace-pre-wrap ${
                                    msg.role === 'user' ? 'text-right' : 'text-left'
                                }`}>
                                    {msg.message}
                                </p>
                            </div>
                        </div>
                    ))}
                    {isLoading && (
                        <div className="flex justify-start">
                            <div className="bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm border border-bg-300 dark:border-slate-700 rounded-xl p-4 shadow-md">
                                <div className="flex items-center gap-2">
                                    <div className="flex gap-1">
                                        <div className="w-2 h-2 bg-indigo-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                                        <div className="w-2 h-2 bg-indigo-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                                        <div className="w-2 h-2 bg-indigo-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                                    </div>
                                    <span className="text-xs text-text-400 dark:text-text-500">AI is thinking...</span>
                                </div>
                            </div>
                        </div>
                    )}
                    {/* Invisible element at the bottom to scroll to */}
                    <div ref={messagesEndRef} />
                </div>
            )}

            <ClaudeChatInput onSendMessage={handleSendMessage} />

            <div className="absolute bottom-4 text-xs text-text-400 font-sans opacity-60 hover:opacity-100 transition-opacity">
            </div>
        </div>
    );
};

export default ChatboxDemo;

