import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000,
});

export const chatAPI = {
  sendMessage: (payload) => api.post('/chat/message', payload),
};

export const adminAPI = {
  listTenants: (secret) => api.get('/admin/tenants', { headers: { 'x-admin-secret': secret } }),
  createTenant: (secret, data) => api.post('/admin/tenants', data, { headers: { 'x-admin-secret': secret } }),
  deleteTenant: (secret, id) => api.delete(`/admin/tenants/${id}`, { headers: { 'x-admin-secret': secret } }),
  getHealth: (secret) => api.get('/admin/system/health', { headers: { 'x-admin-secret': secret } }),
};

export const docAPI = {
  upload: (tenantId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/documents/upload?tenant_id=${tenantId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  list: (tenantId) => api.get(`/documents/?tenant_id=${tenantId}`),
  delete: (tenantId, docId) => api.delete(`/documents/${docId}?tenant_id=${tenantId}`),
};

export const tenantAPI = {
  getConfig: (tenantId) => api.get(`/tenants/${tenantId}/config`),
  updateConfig: (tenantId, config) => api.put(`/tenants/${tenantId}/config`, config),
};

export default api;
