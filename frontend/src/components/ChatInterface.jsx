import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, ListTree, RefreshCw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { chatAPI } from '../api/client';

const ChatInterface = ({ tenantId, messages, setMessages }) => {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID()); // Unique session for this browser visit
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await chatAPI.sendMessage({
        tenant_id: tenantId,
        message: input,
        session_id: sessionId
      });
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: res.data.response,
        sources: res.data.sources 
      }]);
    } catch (err) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error connecting to the brain.' 
      }]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    if (window.confirm('Clear this chat history?')) {
      setMessages([]);
    }
  };

  return (
    <div className="flex flex-col h-[600px] glass-card rounded-3xl overflow-hidden border-brand-500/20">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 bg-slate-900/50 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">AeroChat AI • Live Support</span>
        </div>
        <button 
          onClick={clearChat}
          className="p-2 hover:bg-slate-800 rounded-lg text-slate-500 hover:text-brand-400 transition-all group"
          title="Refresh Chat"
        >
          <RefreshCw className="w-4 h-4 group-hover:rotate-180 transition-transform duration-500" />
        </button>
      </div>

      {/* Messages area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-50">
            <Bot className="w-12 h-12 text-brand-500" />
            <p className="text-sm">Hello! I am your AeroChat assistant.<br/>How can I help you today?</p>
          </div>
        )}
        
        {messages.map((msg, i) => (
          <motion.div 
            key={i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`flex gap-3 max-w-[85%] ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                msg.role === 'user' ? 'bg-brand-600' : 'bg-slate-800 border border-slate-700'
              }`}>
                {msg.role === 'user' ? <User size={16} /> : <Bot size={16} className="text-brand-400" />}
              </div>
              <div className={`space-y-2 ${msg.role === 'user' ? 'text-right' : ''}`}>
                <div className={`p-4 rounded-2xl text-sm leading-relaxed ${
                  msg.role === 'user' 
                    ? 'bg-brand-600 text-white rounded-tr-none shadow-lg' 
                    : 'bg-slate-800/50 text-slate-200 rounded-tl-none border border-slate-700/50'
                }`}>
                  {msg.content}
                </div>
                
                {msg.sources && msg.sources.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {msg.sources.map((s, idx) => (
                      <div key={idx} className="flex items-center gap-1.5 px-2 py-1 bg-slate-900/50 border border-slate-800 rounded text-[10px] text-slate-500">
                        <ListTree size={10} className="text-brand-500" /> Grounded Source
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-800/50 p-4 rounded-2xl rounded-tl-none border border-slate-700/50 flex items-center gap-3">
              <Loader2 className="w-4 h-4 text-brand-500 animate-spin" />
              <span className="text-xs text-slate-400 animate-pulse">Thinking...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input area */}
      <form onSubmit={handleSend} className="p-4 bg-slate-900/50 border-t border-slate-800">
        <div className="relative flex items-center">
          <input 
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything about your business data..."
            className="w-full bg-slate-950 border border-slate-800 rounded-2xl py-4 pl-6 pr-14 text-sm focus:outline-none focus:border-brand-500 transition-all shadow-inner"
          />
          <button 
            type="submit"
            disabled={!input.trim() || loading}
            className="absolute right-2 p-3 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 disabled:hover:bg-brand-600 text-white rounded-xl transition-all shadow-lg"
          >
            <Send size={18} />
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatInterface;
