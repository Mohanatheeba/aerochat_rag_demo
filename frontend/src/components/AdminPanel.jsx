import React, { useState, useEffect } from 'react';
import { 
  Plus, Users, Settings, Database, Shield, CheckCircle2, 
  Trash2, Upload, Search, Activity, Terminal, X
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { adminAPI, docAPI } from '../api/client';

const AdminPanel = () => {
  const [secret, setSecret] = useState('aerochat-dev-secret-123');
  const [tenants, setTenants] = useState([]);
  const [selectedTenant, setSelectedTenant] = useState(null);
  const [docs, setDocs] = useState([]);
  const [health, setHealth] = useState(null);
  const [view, setView] = useState('tenants'); // 'tenants', 'documents', 'health'
  const [loading, setLoading] = useState(false);
  
  // New Tenant Modal State
  const [showAddModal, setShowAddModal] = useState(false);
  const [newTenant, setNewTenant] = useState({ name: '', domain: '' });

  useEffect(() => {
    fetchTenants();
    fetchHealth();
  }, [secret]);

  useEffect(() => {
    if (selectedTenant) {
      fetchDocs();
    }
  }, [selectedTenant]);

  // AUTO-POLLING LOGIC: If any doc is 'processing', refresh the list every 3 seconds
  useEffect(() => {
    let interval;
    const hasProcessing = docs.some(d => d.status === 'processing');
    
    if (hasProcessing && selectedTenant) {
      interval = setInterval(() => {
        console.log("🔄 Polling for document status...");
        fetchDocs();
      }, 3000);
    }
    
    return () => clearInterval(interval);
  }, [docs, selectedTenant]);

  const fetchTenants = async () => {
    try {
      const res = await adminAPI.listTenants(secret);
      setTenants(res.data);
      if (res.data.length > 0 && !selectedTenant) setSelectedTenant(res.data[0]);
    } catch (err) {
      console.error(err);
    }
  };

  const handleAddTenant = async (e) => {
    e.preventDefault();
    try {
      await adminAPI.createTenant(secret, newTenant);
      setShowAddModal(false);
      setNewTenant({ name: '', domain: '' });
      fetchTenants();
    } catch (err) {
      const errorDetail = err.response?.data?.detail || err.message;
      alert('Failed to create tenant: ' + errorDetail);
    }
  };

  const handleDeleteTenant = async (e, id) => {
    e.stopPropagation(); // Don't select the tenant when clicking delete
    if (!window.confirm('WARNING: This will permanently delete the tenant and ALL its uploaded documents. Continue?')) return;
    
    try {
      await adminAPI.deleteTenant(secret, id);
      fetchTenants();
      if (selectedTenant?.id === id) setSelectedTenant(null);
    } catch (err) {
      alert('Failed to delete tenant: ' + err.message);
    }
  };

  const fetchDocs = async () => {
    if (!selectedTenant) return;
    try {
      const res = await docAPI.list(selectedTenant.id);
      setDocs(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchHealth = async () => {
    try {
      const res = await adminAPI.getHealth(secret);
      setHealth(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file || !selectedTenant) return;
    setLoading(true);
    try {
      await docAPI.upload(selectedTenant.id, file);
      fetchDocs();
    } catch (err) {
      alert('Upload failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const deleteDoc = async (docId) => {
    if (!window.confirm('Delete this document?')) return;
    try {
      await docAPI.delete(selectedTenant.id, docId);
      fetchDocs();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="grid grid-cols-12 gap-6 h-[700px] relative font-sans">
      {/* Sidebar */}
      <div className="col-span-3 glass-card rounded-3xl p-4 space-y-2 border-slate-800">
        <h2 className="text-xs font-black text-slate-500 uppercase tracking-[0.2em] px-3 mb-6">Super Admin</h2>
        <NavItem active={view === 'tenants'} onClick={() => setView('tenants')} icon={Users} label="Clients & Tenants" ghostColor="text-brand-400" />
        <NavItem active={view === 'documents'} onClick={() => setView('documents')} icon={Database} label="Grounding Data" ghostColor="text-purple-400" />
        <NavItem active={view === 'health'} onClick={() => setView('health')} icon={Activity} label="System Health" ghostColor="text-green-400" />
        
        <div className="pt-8 px-2">
          <label className="text-[10px] font-bold text-slate-500 uppercase block mb-2 px-1">Admin Secret</label>
          <div className="relative group">
            <Shield className="absolute left-3 top-3 w-4 h-4 text-slate-500 group-focus-within:text-brand-500 transition-colors" />
            <input 
              type="password" 
              value={secret} 
              onChange={(e) => setSecret(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl py-2.5 pl-10 pr-4 text-xs text-slate-300 focus:outline-none focus:border-brand-500/50 transition-all font-mono"
            />
          </div>
        </div>
      </div>

      {/* Main Area */}
      <div className="col-span-9 glass-card rounded-3xl p-8 overflow-y-auto relative border-slate-800 shadow-2xl">
        {view === 'tenants' && (
          <div className="space-y-8">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-3xl font-black flex items-center gap-3 text-white">
                  <Users className="text-brand-500" size={32} /> Tenants
                </h2>
                <p className="text-slate-500 text-sm mt-1">Manage active RAG instances and client environments.</p>
              </div>
              <button 
                onClick={() => setShowAddModal(true)}
                className="flex items-center gap-2 bg-brand-600 hover:bg-brand-500 px-6 py-3 rounded-2xl text-sm font-bold transition-all shadow-lg shadow-brand-600/20 active:scale-95"
              >
                <Plus size={20} /> Add Tenant
              </button>
            </div>
            
            <div className="grid gap-4">
              {tenants.map(t => (
                <div 
                  key={t.id} 
                  onClick={() => setSelectedTenant(t)}
                  className={`group p-6 rounded-2xl border transition-all cursor-pointer relative overflow-hidden ${
                    selectedTenant?.id === t.id ? 'bg-brand-500/10 border-brand-500/50 ring-1 ring-brand-500/50' : 'bg-slate-900/40 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex justify-between items-center relative z-10">
                    <div className="space-y-1">
                      <div className="flex items-center gap-3">
                        <h3 className="text-lg font-bold text-white">{t.name}</h3>
                        <span className="text-[10px] bg-slate-800 px-2 py-0.5 rounded-full border border-slate-700 text-slate-400 font-mono tracking-tighter">{t.domain || 'no-domain'}</span>
                      </div>
                      <p className="text-[10px] font-mono text-brand-400 uppercase tracking-tighter opacity-70">ID: {t.id}</p>
                    </div>
                    
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <span className="block text-xs font-bold text-white">{t.message_count}</span>
                        <span className="text-[10px] text-slate-500 uppercase font-black tracking-widest">Requests</span>
                      </div>
                      
                      <button 
                        onClick={(e) => handleDeleteTenant(e, t.id)}
                        className="p-3 bg-slate-950/50 hover:bg-red-500/20 text-slate-600 hover:text-red-500 rounded-xl transition-all border border-transparent hover:border-red-500/30 active:scale-90"
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </div>
                  {/* Subtle hover effect background */}
                  <div className="absolute inset-0 bg-gradient-to-r from-brand-500/0 to-brand-500/0 group-hover:from-brand-500/5 transition-all pointer-events-none" />
                </div>
              ))}
            </div>

            {/* Inline Add Modal Overlay */}
            <AnimatePresence>
              {showAddModal && (
                <motion.div 
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="absolute inset-0 z-50 bg-slate-950/90 backdrop-blur-xl p-8 flex items-center justify-center rounded-3xl"
                >
                  <div className="glass-card p-10 rounded-[2.5rem] w-full max-w-md border-brand-500/30 shadow-2xl relative">
                    <button onClick={() => setShowAddModal(false)} className="absolute top-6 right-6 text-slate-500 hover:text-white p-2 hover:bg-slate-800 rounded-full transition-all"><X size={20} /></button>
                    
                    <div className="text-center mb-8">
                      <div className="w-16 h-16 bg-brand-500/10 rounded-3xl flex items-center justify-center mx-auto mb-4 border border-brand-500/20">
                        <Users className="text-brand-500" size={32} />
                      </div>
                      <h3 className="text-2xl font-black text-white">Create Instance</h3>
                      <p className="text-slate-500 text-sm mt-1">Spin up a new dedicated RAG environment.</p>
                    </div>

                    <form onSubmit={handleAddTenant} className="space-y-6">
                      <div className="space-y-2">
                        <label className="text-[10px] text-slate-500 uppercase font-black tracking-widest px-1">Business Name</label>
                        <input 
                          autoFocus
                          required
                          className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-white focus:outline-none focus:border-brand-500 transition-all shadow-inner"
                          placeholder="e.g. Acme Corp"
                          value={newTenant.name}
                          onChange={e => setNewTenant({...newTenant, name: e.target.value})}
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-[10px] text-slate-500 uppercase font-black tracking-widest px-1">Domain</label>
                        <input 
                          required
                          className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-white focus:outline-none focus:border-brand-500 transition-all shadow-inner"
                          placeholder="acme.com"
                          value={newTenant.domain}
                          onChange={e => setNewTenant({...newTenant, domain: e.target.value})}
                        />
                      </div>
                      <button type="submit" className="w-full bg-brand-600 hover:bg-brand-500 py-4 rounded-2xl font-black text-sm uppercase tracking-widest transition-all shadow-xl shadow-brand-600/30 active:scale-95">
                        Initialize
                      </button>
                    </form>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* ... (Documents and Health views stay mostly same but with rounded-3xl and polished spacing) */}
        {view === 'documents' && (
          <div className="space-y-8">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-3xl font-black flex items-center gap-3 text-white">
                  <Database className="text-purple-400" size={32} /> Grounding Data
                </h2>
                <p className="text-slate-500 text-sm mt-1">Teaching the AI for: <span className="text-brand-400 font-bold">{selectedTenant?.name || 'No Tenant Selected'}</span></p>
              </div>
              <label className="flex items-center gap-2 bg-purple-600 hover:bg-purple-500 px-6 py-3 rounded-2xl text-sm font-bold cursor-pointer transition-all shadow-lg shadow-purple-600/20 active:scale-95">
                <Upload size={20} /> {loading ? 'Processing...' : 'Upload PDF'}
                <input type="file" className="hidden" onChange={handleFileUpload} disabled={loading} />
              </label>
            </div>

            <div className="grid gap-3 mt-8">
              {!selectedTenant ? (
                <div className="text-center py-20 bg-slate-900/30 rounded-[2rem] border border-dashed border-slate-800">
                   <Users className="w-12 h-12 mx-auto text-slate-700 mb-4" />
                   <p className="text-slate-500 italic">Please select a tenant from the sidebar to manage files.</p>
                </div>
              ) : docs.length === 0 ? (
                <div className="text-center py-20 bg-slate-900/30 rounded-[2rem] border border-dashed border-slate-800">
                  <Terminal className="w-12 h-12 mx-auto text-slate-700 mb-4" />
                  <p className="text-slate-500">No documents found for this tenant.</p>
                </div>
              ) : (
                docs.map(doc => (
                  <div key={doc.id} className="flex items-center justify-between p-5 bg-slate-900/40 rounded-[1.5rem] border border-slate-800 hover:border-slate-700 transition-all group">
                    <div className="flex items-center gap-4">
                      <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                        <Database className="w-5 h-5 text-brand-400" />
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-slate-200">{doc.file_name}</h4>
                        <div className="flex items-center gap-4 mt-1.5">
                          <span className="text-[10px] text-slate-600 font-black uppercase tracking-tighter">{(doc.file_size / 1024).toFixed(1)} KB</span>
                          <span className={`text-[9px] px-2 py-0.5 rounded-full uppercase font-black tracking-widest ${
                            doc.status === 'indexed' ? 'bg-green-500/10 text-green-500 border border-green-500/20' : 'bg-brand-500/10 text-brand-500 border border-brand-500/20 animate-pulse'
                          }`}>
                            {doc.status}
                          </span>
                        </div>
                      </div>
                    </div>
                    <button 
                      onClick={() => deleteDoc(doc.id)}
                      className="p-3 hover:bg-red-500/20 text-slate-600 hover:text-red-500 rounded-xl transition-all border border-transparent hover:border-red-500/30 active:scale-90"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {view === 'health' && (
          <div className="space-y-12">
            <h2 className="text-3xl font-black flex items-center gap-3 text-white">
              <Activity className="text-green-400" size={32} /> Infrastructure
            </h2>
            
            <div className="grid grid-cols-2 gap-6">
              {health && Object.entries(health.services).map(([name, status]) => (
                <div key={name} className="p-6 bg-slate-900/40 rounded-[2rem] border border-slate-800 flex items-center justify-between shadow-lg">
                  <div className="space-y-1">
                    <div className="text-[10px] text-slate-500 uppercase font-black tracking-widest">Service</div>
                    <div className="capitalize text-lg font-bold text-white">{name}</div>
                  </div>
                  <div className="flex items-center gap-3 bg-green-500/10 text-green-500 px-4 py-2 rounded-2xl border border-green-500/20">
                    <CheckCircle2 size={18} />
                    <span className="text-xs font-black uppercase tracking-widest">{status}</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="p-10 bg-gradient-to-br from-brand-600/10 to-purple-600/5 border border-brand-500/20 rounded-[2.5rem] relative overflow-hidden group">
              <div className="relative z-10 space-y-4">
                <h3 className="text-2xl font-black text-brand-400">Next-Gen Hybrid Intelligence</h3>
                <p className="text-slate-400 leading-relaxed max-w-2xl text-sm">
                  Leveraging **Llama 3.3 70B** for logical synthesis and **MiniLM-L6** for semantic vectorization. 
                  Real-time session state is managed by a high-availability Redis cache. 
                  Current end-to-end response delay: <span className="text-brand-400 font-bold px-2 py-0.5 bg-brand-500/10 rounded-lg">~1.2s</span>
                </p>
                <div className="flex gap-4 pt-4">
                   <div className="flex items-center gap-2 text-[10px] text-slate-500 uppercase font-black tracking-widest"><div className="w-1.5 h-1.5 bg-blue-500 rounded-full"/> Semantic Engine</div>
                   <div className="flex items-center gap-2 text-[10px] text-slate-500 uppercase font-black tracking-widest"><div className="w-1.5 h-1.5 bg-purple-500 rounded-full"/> Inference API</div>
                   <div className="flex items-center gap-2 text-[10px] text-slate-500 uppercase font-black tracking-widest"><div className="w-1.5 h-1.5 bg-green-500 rounded-full"/> Vector Node</div>
                </div>
              </div>
              <Activity className="absolute -right-12 -bottom-12 w-64 h-64 text-brand-500/5 group-hover:text-brand-500/10 transition-colors duration-1000" />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const NavItem = ({ active, onClick, icon: Icon, label, ghostColor }) => (
  <button 
    onClick={onClick}
    className={`w-full flex items-center gap-4 px-5 py-4 rounded-[1.25rem] transition-all relative overflow-hidden group active:scale-95 ${
      active ? 'bg-slate-800 text-white shadow-xl ring-1 ring-slate-700' : 'text-slate-500 hover:bg-slate-900/50 hover:text-slate-300'
    }`}
  >
    <Icon className={`w-5 h-5 transition-transform group-hover:scale-110 ${active ? ghostColor : ''}`} />
    <span className="text-sm font-bold">{label}</span>
    {active && <div className={`absolute right-2 w-1.5 h-5 rounded-full ${ghostColor.replace('text-', 'bg-')}`} />}
  </button>
);

export default AdminPanel;
