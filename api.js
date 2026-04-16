import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,
})

// ─── Chat ────────────────────────────────────────────────────
export const chatAPI = {
  sendMessage: (tenantId, message, sessionId, channel = 'widget') =>
    api.post('/chat/message', { tenant_id: tenantId, message, session_id: sessionId, channel }),

  getHistory: (tenantId, sessionId) =>
    api.get(`/chat/history/${sessionId}`, { params: { tenant_id: tenantId } }),

  clearSession: (tenantId, sessionId) =>
    api.delete(`/chat/session/${sessionId}`, { params: { tenant_id: tenantId } }),
}

// ─── Documents ───────────────────────────────────────────────
export const documentsAPI = {
  upload: (tenantId, file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/documents/upload', form, {
      params: { tenant_id: tenantId },
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  list: (tenantId) =>
    api.get('/documents/', { params: { tenant_id: tenantId } }),

  delete: (tenantId, documentId) =>
    api.delete(`/documents/${documentId}`, { params: { tenant_id: tenantId } }),

  testSearch: (tenantId, query, topK = 4) =>
    api.post('/documents/test-search', null, {
      params: { tenant_id: tenantId, query, top_k: topK }
    }),

  getChunks: (tenantId, documentId) =>
    api.get(`/documents/${documentId}/chunks`, { params: { tenant_id: tenantId } }),
}

// ─── Tenants ─────────────────────────────────────────────────
export const tenantsAPI = {
  getConfig: (tenantId) =>
    api.get(`/tenants/${tenantId}/config`),

  updateConfig: (tenantId, config) =>
    api.put(`/tenants/${tenantId}/config`, config),

  getStats: (tenantId) =>
    api.get(`/tenants/${tenantId}/stats`),

  getConversations: (tenantId, limit = 20) =>
    api.get(`/tenants/${tenantId}/conversations`, { params: { limit } }),

  getMessages: (tenantId, conversationId) =>
    api.get(`/tenants/${tenantId}/conversations/${conversationId}/messages`),
}

// ─── Super Admin ─────────────────────────────────────────────
export const adminAPI = {
  listTenants: (secret) =>
    api.get('/admin/tenants', { headers: { 'x-admin-secret': secret } }),

  createTenant: (secret, data) =>
    api.post('/admin/tenants', data, { headers: { 'x-admin-secret': secret } }),

  updateTenant: (secret, tenantId, data) =>
    api.put(`/admin/tenants/${tenantId}`, data, { headers: { 'x-admin-secret': secret } }),

  getTenantUsage: (secret, tenantId) =>
    api.get(`/admin/tenants/${tenantId}/usage`, { headers: { 'x-admin-secret': secret } }),

  systemHealth: (secret) =>
    api.get('/admin/system/health', { headers: { 'x-admin-secret': secret } }),

  debugVectors: (secret, tenantId, params) =>
    api.get(`/admin/tenants/${tenantId}/debug/vectors`, {
      headers: { 'x-admin-secret': secret },
      params
    }),

  reindexTenant: (secret, tenantId) =>
    api.post(`/admin/tenants/${tenantId}/reindex`, null, {
      headers: { 'x-admin-secret': secret }
    }),

  getTickets: (secret, status) =>
    api.get('/admin/support/tickets', {
      headers: { 'x-admin-secret': secret },
      params: status ? { status } : {}
    }),

  updateTicket: (secret, ticketId, status, notes) =>
    api.put(`/admin/support/tickets/${ticketId}`, null, {
      headers: { 'x-admin-secret': secret },
      params: { status, notes }
    }),
}

export default api
