import React, { useState } from 'react';
import { Bot, Shield, MessageSquare, Zap, Terminal } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ChatInterface from './components/ChatInterface';
import AdminPanel from './components/AdminPanel';

function App() {
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' or 'admin'
  const [currentTenantId, setCurrentTenantId] = useState('');
  const [tenantChats, setTenantChats] = useState({}); // { [tenantId]: [messages...] }

  const setMessagesForTenant = (newMessages) => {
    setTenantChats(prev => ({
      ...prev,
      [currentTenantId]: typeof newMessages === 'function' 
        ? newMessages(prev[currentTenantId] || []) 
        : newMessages
    }));
  };

  const currentMessages = tenantChats[currentTenantId] || [];

  return (
    <div className="min-h-screen">
      {/* Navigation Header */}
      <nav className="p-6 border-b border-slate-800 bg-slate-950/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-brand-600 p-2 rounded-xl">
              <Zap className="text-white w-6 h-6 fill-white" />
            </div>
            <span className="text-2xl font-black tracking-tighter text-white">
              AERO<span className="text-brand-500">CHAT</span>
            </span>
            <span className="bg-slate-800 text-brand-400 text-[10px] font-bold px-2 py-0.5 rounded-full border border-brand-500/20">
              STAGING
            </span>
          </div>

          <div className="flex p-1 bg-slate-900 rounded-xl border border-slate-800">
            <button 
              onClick={() => setActiveTab('chat')}
              className={`flex items-center gap-2 px-6 py-2 rounded-lg text-sm font-bold transition-all ${
                activeTab === 'chat' ? 'bg-brand-600 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              <MessageSquare className="w-4 h-4" /> Demo Chat
            </button>
            <button 
              onClick={() => setActiveTab('admin')}
              className={`flex items-center gap-2 px-6 py-2 rounded-lg text-sm font-bold transition-all ${
                activeTab === 'admin' ? 'bg-purple-600 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              <Shield className="w-4 h-4" /> Super Admin
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto p-6 md:p-12">
        <AnimatePresence mode="wait">
          {activeTab === 'chat' ? (
            <motion.div 
              key="chat"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
              className="max-w-3xl mx-auto space-y-8"
            >
              {/* Marketing Banner */}
              <div className="text-center space-y-4 mb-8">
                <h1 className="text-4xl md:text-6xl font-black text-white leading-tight">
                  Intelligent <span className="text-gradient">RAG Support</span> <br /> 
                  for Enterprise Scale.
                </h1>
                <p className="text-slate-400 max-w-xl mx-auto">
                  Powered by Llama 3 and PGVector. Providing accurate, 
                  product-aware responses with 100% data grounding.
                </p>
              </div>

              {!currentTenantId ? (
                <div className="glass-card p-12 rounded-3xl text-center space-y-6">
                  <div className="w-16 h-16 bg-slate-900 rounded-2xl flex items-center justify-center mx-auto border border-slate-800">
                    <Bot className="w-8 h-8 text-brand-500" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold">Select a Staging Tenant</h2>
                    <p className="text-slate-500 mt-2">Enter a Tenant ID from the Admin Panel to begin testing the RAG flow.</p>
                  </div>
                  <div className="flex max-w-sm mx-auto gap-2">
                    <input 
                      type="text" 
                      placeholder="Enter Tenant ID..." 
                      className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/50"
                      onChange={(e) => setCurrentTenantId(e.target.value)}
                    />
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex justify-between items-center px-2">
                    <span className="text-xs text-slate-500">Testing active for tenant: <span className="text-brand-400 font-mono">{currentTenantId}</span></span>
                    <button onClick={() => setCurrentTenantId('')} className="text-[10px] text-slate-600 hover:text-slate-400 uppercase font-bold tracking-widest">Change</button>
                  </div>
                  <ChatInterface 
                    key={currentTenantId}
                    tenantId={currentTenantId} 
                    messages={currentMessages} 
                    setMessages={setMessagesForTenant} 
                  />
                </div>
              )}
            </motion.div>
          ) : (
            <motion.div 
              key="admin"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
            >
              <AdminPanel />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Footer */}
      <footer className="mt-20 border-t border-slate-900 p-8 text-center bg-slate-950/80">
        <div className="flex justify-center gap-6 mb-4">
          <Bot className="w-5 h-5 text-slate-700 hover:text-brand-500 cursor-pointer" />
          <Terminal className="w-5 h-5 text-slate-700 hover:text-white cursor-pointer" />
        </div>
        <p className="text-slate-700 text-[10px] font-bold uppercase tracking-[0.2em]">
          AeroChat RAG Architecture • Production-Ready Staging Environment
        </p>
      </footer>
    </div>
  );
}

export default App;
