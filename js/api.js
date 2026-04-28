// API Client - handles all communication with the FastAPI backend
const API = {
    base: '/api',
    token: localStorage.getItem('token'),

    setToken(t) { this.token = t; localStorage.setItem('token', t); },
    clearToken() { this.token = null; localStorage.removeItem('token'); localStorage.removeItem('user'); },
    getUser() { try { return JSON.parse(localStorage.getItem('user')); } catch { return null; } },
    setUser(u) { localStorage.setItem('user', JSON.stringify(u)); },

    async request(method, path, body = null, params = null, _retries = 2) {
        let url = this.base + path;
        if (params) {
            const sp = new URLSearchParams();
            Object.entries(params).forEach(([k, v]) => { if (v != null && v !== '') sp.append(k, v); });
            const qs = sp.toString();
            if (qs) url += '?' + qs;
        }
        const opts = { method, headers: {} };
        if (this.token) opts.headers['Authorization'] = 'Bearer ' + this.token;
        if (body) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }

        const res = await fetch(url, opts);
        if (res.status === 401) { this.clearToken(); location.reload(); throw new Error('Unauthorized'); }
        // Retry on 503 (DB temporarily unavailable) or 500 (connection reset)
        if ((res.status === 503 || res.status === 500) && _retries > 0) {
            await new Promise(r => setTimeout(r, 800 * (3 - _retries)));
            return this.request(method, path, body, params, _retries - 1);
        }
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Request failed');
        return data;
    },

    // Auth
    login(username, password) { return this.request('POST', '/auth/login', { username, password }); },
    register(data) { return this.request('POST', '/auth/register', data); },

    // Expenses
    getExpenses(params) { return this.request('GET', '/expenses', null, params); },
    addExpense(data) { return this.request('POST', '/expenses', data); },
    updateExpense(id, data) { return this.request('PUT', `/expenses/${id}`, data); },
    deleteExpense(id) { return this.request('DELETE', `/expenses/${id}`); },

    // Analytics
    getOverview(params) { return this.request('GET', '/analytics/overview', null, params); },
    getCategorySummary(params) { return this.request('GET', '/analytics/category-summary', null, params); },
    getMonthly() { return this.request('GET', '/analytics/monthly'); },
    getDaily(params) { return this.request('GET', '/analytics/daily', null, params); },
    getWeekly() { return this.request('GET', '/analytics/weekly'); },
    getTop(params) { return this.request('GET', '/analytics/top', null, params); },
    getCategoryTrend() { return this.request('GET', '/analytics/category-trend'); },
    getHeatmap() { return this.request('GET', '/analytics/heatmap'); },

    // Budget
    getBudgets() { return this.request('GET', '/budgets'); },
    setBudget(month, amount) { return this.request('POST', '/budgets', { month, amount }); },

    // AI
    analyze(type, budget) { return this.request('POST', '/ai/analyze', { type, budget }); },

    // Categories
    getCategories() { return this.request('GET', '/categories'); },

    // Users (admin)
    getUsers() { return this.request('GET', '/users'); },
    deleteUser(id) { return this.request('DELETE', `/users/${id}`); },
    resetUserPassword(user_id, new_password) { return this.request('POST', '/users/reset-password', { user_id, new_password }); },
    changePassword(old_password, new_password) { return this.request('POST', '/auth/change-password', { old_password, new_password }); },

    // Keep-alive
    ping() { return this.request('GET', '/ping'); },

    isAdmin() { const u = this.getUser(); return u && u.is_admin === true; },
};
