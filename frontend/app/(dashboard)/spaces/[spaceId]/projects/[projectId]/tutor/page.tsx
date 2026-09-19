'use client';

import { useState, useEffect, useRef, use } from 'react';
import { fetchApi } from '@/lib/api-client';
import { ProjectNav } from '@/components/ProjectNav';

interface Citation {
  text: string;
  page_number: number;
  filename: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations: Citation[] | null;
  created_at: string;
}

interface Conversation {
  id: string;
  messages: Message[];
}

export default function TutorPage({ params }: { params: Promise<{ spaceId: string, projectId: string }> }) {
  const { spaceId, projectId } = use(params);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Basic setup: Create a new conversation on mount if none exists
    // In a real app we'd load an existing one or list them.
    const initConv = async () => {
      try {
        const conv = await fetchApi(`/projects/${projectId}/tutor/conversations`, {
          method: 'POST'
        });
        setConversation(conv);
      } catch (e) {
        console.error("Failed to create conversation", e);
      }
    };
    initConv();
  }, [projectId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation?.messages]);

  const sendMessage = async () => {
    if (!input.trim() || !conversation) return;
    
    const userMsg = input.trim();
    setInput('');
    
    // Optimistic update
    const tempId = Date.now().toString();
    setConversation(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        messages: [
          ...prev.messages,
          { id: tempId, role: 'user', content: userMsg, citations: null, created_at: new Date().toISOString() }
        ]
      };
    });

    setLoading(true);
    try {
      const responseMsg = await fetchApi(`/projects/${projectId}/tutor/conversations/${conversation.id}/messages`, {
        method: 'POST',
        body: JSON.stringify({ content: userMsg })
      });
      
      setConversation(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          messages: [...prev.messages, responseMsg]
        };
      });
    } catch (e) {
      console.error(e);
      // Rollback logic could go here
    } finally {
      setLoading(false);
    }
  };

  if (!conversation) return <div className="p-8">Starting tutor session...</div>;

  return (
    <div className="flex flex-col h-[calc(100vh-80px)] p-6 bg-slate-50">
      <ProjectNav spaceId={spaceId} projectId={projectId} />
      <h1 className="text-2xl font-semibold mb-4 text-slate-800">AI Tutor</h1>
      
      <div className="flex-1 overflow-y-auto mb-4 bg-white rounded-lg shadow p-4 flex flex-col space-y-4">
        {conversation.messages.length === 0 && (
          <div className="text-slate-500 text-center mt-10">Ask me a question about your materials!</div>
        )}
        {conversation.messages.map(msg => {
          const isInsufficient = msg.role === 'assistant' && msg.content === "I don't have enough evidence in your materials to answer that.";
          
          return (
            <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div className={`
                max-w-[80%] rounded-2xl px-4 py-2 
                ${msg.role === 'user' 
                  ? 'bg-blue-600 text-white' 
                  : isInsufficient 
                    ? 'bg-amber-100 text-amber-900 border border-amber-300' 
                    : 'bg-slate-100 text-slate-800'}
              `}>
                <div className="whitespace-pre-wrap">{msg.content}</div>
                
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-300 text-xs flex flex-col gap-1">
                    <span className="font-semibold text-slate-600 mb-1">Sources:</span>
                    {msg.citations.map((c, i) => (
                      <div key={i} className="text-slate-500 italic">
                        "{c.text}" — <span className="font-medium">{c.filename}</span>, p.{c.page_number}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
        {loading && (
          <div className="flex items-start">
            <div className="bg-slate-100 text-slate-800 rounded-2xl px-4 py-2 flex items-center space-x-2">
              <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce delay-75"></div>
              <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce delay-150"></div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="flex space-x-2">
        <input 
          type="text" 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Ask a question..."
          disabled={loading}
          className="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        />
        <button 
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
