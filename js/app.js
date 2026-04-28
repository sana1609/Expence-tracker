// ===== App Core =====
const App = {
    currentPage: 'dashboard',
    categories: [],
    charts: {},

    async init() {
        if (API.token && API.getUser()) { this.showApp(); }
        else { this.showLogin(); }
    },

    // ===== Auth =====
    showLogin() {
        document.getElementById('login-screen').classList.remove('hidden');
        document.getElementById('app-screen').classList.add('hidden');
        document.getElementById('login-form').onsubmit = async (e) => {
            e.preventDefault();
            const errEl = document.getElementById('login-error');
            errEl.classList.add('hidden');
            const u = document.getElementById('login-user').value.trim();
            const p = document.getElementById('login-pass').value;
            try {
                const res = await API.login(u, p);
                API.setToken(res.token);
                API.setUser(res.user);
                this.showApp();
            } catch (err) {
                errEl.textContent = err.message;
                errEl.classList.remove('hidden');
            }
        };
    },

    async showApp() {
        document.getElementById('login-screen').classList.add('hidden');
        document.getElementById('app-screen').classList.remove('hidden');
        const user = API.getUser();
        document.getElementById('sidebar-user').textContent = user.full_name;

        // Load categories
        try { const res = await API.getCategories(); this.categories = res.categories; } catch { this.categories = ['📦 Other']; }

        // Show admin nav if admin user
        if (API.isAdmin()) {
            document.querySelectorAll('.admin-only').forEach(el => el.classList.remove('hidden'));
        }

        // Setup navigation
        document.querySelectorAll('.sidebar-nav li').forEach(li => {
            li.onclick = () => this.navigateTo(li.dataset.page);
        });

        // Theme toggle
        const theme = localStorage.getItem('theme') || 'light';
        if (theme === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
        document.getElementById('theme-btn').onclick = () => {
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            document.documentElement.setAttribute('data-theme', isDark ? '' : 'dark');
            localStorage.setItem('theme', isDark ? 'light' : 'dark');
            const icon = document.querySelector('#theme-btn i');
            icon.className = isDark ? 'ri-moon-line' : 'ri-sun-line';
        };

        // Logout
        document.getElementById('logout-btn').onclick = () => { API.clearToken(); location.reload(); };

        // Mobile menu
        document.getElementById('menu-btn').onclick = () => {
            document.getElementById('sidebar').classList.toggle('open');
            let ov = document.querySelector('.sidebar-overlay');
            if (!ov) { ov = document.createElement('div'); ov.className = 'sidebar-overlay'; document.getElementById('app-screen').appendChild(ov); }
            ov.classList.toggle('active');
            ov.onclick = () => { document.getElementById('sidebar').classList.remove('open'); ov.classList.remove('active'); };
        };

        // Bottom nav (mobile)
        document.querySelectorAll('.bottom-nav-item').forEach(btn => {
            btn.onclick = () => this.navigateTo(btn.dataset.page);
        });

        // Keep-alive: ping SQLite Cloud every hour from client side too
        this._startKeepAlive();

        this.navigateTo('dashboard');
    },

    _keepAliveTimer: null,
    _startKeepAlive() {
        if (this._keepAliveTimer) clearInterval(this._keepAliveTimer);
        // Ping immediately, then every hour
        API.ping().catch(() => {});
        this._keepAliveTimer = setInterval(() => { API.ping().catch(() => {}); }, 3600000);
    },

    navigateTo(page) {
        this.currentPage = page;
        document.querySelectorAll('.sidebar-nav li').forEach(li => li.classList.toggle('active', li.dataset.page === page));
        document.querySelectorAll('.bottom-nav-item').forEach(b => b.classList.toggle('active', b.dataset.page === page));
        const titles = { dashboard: 'Dashboard', add: 'Add Expense', expenses: 'Expenses', analytics: 'Analytics', budget: 'Budget', ai: 'AI Insights', admin: 'Admin Panel' };
        document.getElementById('page-title').textContent = titles[page] || page;
        // Close mobile sidebar
        document.getElementById('sidebar').classList.remove('open');
        const ov = document.querySelector('.sidebar-overlay'); if (ov) ov.classList.remove('active');
        // Destroy old charts
        Object.values(this.charts).forEach(c => { try { c.destroy(); } catch {} });
        this.charts = {};
        // Render
        const content = document.getElementById('content');
        content.innerHTML = '<div class="loading-overlay"><div class="spinner"></div><span>Loading...</span></div>';
        this['render_' + page]?.();
    },

    // ===== Helpers =====
    $(sel, parent) { return (parent || document).querySelector(sel); },
    fmt(n) { return '₹' + Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 }); },
    fmtD(n) { return '₹' + Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); },
    toast(msg, type = 'success') {
        const c = document.getElementById('toast-container');
        const t = document.createElement('div');
        t.className = 'toast ' + type;
        t.innerHTML = `<i class="ri-${type === 'success' ? 'check' : type === 'error' ? 'close-circle' : 'information'}-line"></i> ${msg}`;
        c.appendChild(t);
        setTimeout(() => { t.style.animation = 'slideOut .3s ease forwards'; setTimeout(() => t.remove(), 300); }, 3000);
    },
    chartColors() {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        return { fg: isDark ? '#E2E8F0' : '#1E293B', grid: isDark ? '#334155' : '#E2E8F0', bg: isDark ? '#1E293B' : '#FFFFFF' };
    },
    chartOpts(overrides = {}) {
        const c = this.chartColors();
        return {
            chart: { background: 'transparent', foreColor: c.fg, toolbar: { show: false }, fontFamily: 'Inter, sans-serif', ...overrides.chart },
            grid: { borderColor: c.grid, strokeDashArray: 3, ...overrides.grid },
            theme: { mode: document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light' },
            tooltip: { theme: document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light', ...overrides.tooltip },
            ...overrides
        };
    },

    // ===== DASHBOARD =====
    async render_dashboard() {
        const content = document.getElementById('content');
        try {
            const [overview, catData, dailyData, monthlyData] = await Promise.all([
                API.getOverview(), API.getCategorySummary(), API.getDaily(), API.getMonthly()
            ]);

            const mchg = overview.month_change_pct;
            const mchgClass = mchg > 0 ? 'up' : mchg < 0 ? 'down' : '';
            const mchgIcon = mchg > 0 ? '↑' : mchg < 0 ? '↓' : '→';

            content.innerHTML = `
                <div class="metrics-grid">
                    <div class="metric-card accent-blue"><div class="metric-label">This Month</div><div class="metric-value">${this.fmt(overview.this_month)}</div><div class="metric-sub ${mchgClass}">${mchgIcon} ${Math.abs(mchg).toFixed(1)}% vs last month</div></div>
                    <div class="metric-card accent-green"><div class="metric-label">Daily Average</div><div class="metric-value">${this.fmt(overview.daily_avg)}</div><div class="metric-sub">${overview.days_passed} days in</div></div>
                    <div class="metric-card accent-amber"><div class="metric-label">Projected</div><div class="metric-value">${this.fmt(overview.projected)}</div><div class="metric-sub">${overview.days_remaining} days left</div></div>
                    <div class="metric-card accent-red"><div class="metric-label">Largest Expense</div><div class="metric-value">${this.fmt(overview.max_amount)}</div><div class="metric-sub">${overview.total_transactions} total txns</div></div>
                    ${overview.budget > 0 ? `<div class="metric-card accent-blue"><div class="metric-label">Budget Used</div><div class="metric-value">${overview.budget_used_pct}%</div><div class="progress-bar"><div class="fill" style="width:${Math.min(overview.budget_used_pct,100)}%;background:${overview.budget_used_pct>90?'var(--danger)':overview.budget_used_pct>70?'var(--warning)':'var(--success)'}"></div></div><div class="metric-sub">of ${this.fmt(overview.budget)}</div></div>` : ''}
                </div>
                <div class="charts-grid">
                    <div class="card"><div class="card-header"><h3>📊 Category Distribution</h3></div><div id="chart-cat-pie"></div></div>
                    <div class="card"><div class="card-header"><h3>📈 Daily Spending</h3></div><div id="chart-daily"></div></div>
                    <div class="card"><div class="card-header"><h3>📅 Monthly Comparison</h3></div><div id="chart-monthly"></div></div>
                    <div class="card"><div class="card-header"><h3>🏆 Top Categories</h3></div><div id="chart-cat-bar"></div></div>
                </div>
            `;

            // Category donut
            if (catData.categories.length) {
                this.charts.catPie = new ApexCharts(document.getElementById('chart-cat-pie'), this.chartOpts({
                    chart: { type: 'donut', height: 280 },
                    series: catData.categories.map(c => c.total),
                    labels: catData.categories.map(c => c.category),
                    plotOptions: { pie: { donut: { size: '55%', labels: { show: true, total: { show: true, label: 'Total', formatter: () => this.fmt(catData.categories.reduce((s, c) => s + c.total, 0)) } } } } },
                    legend: { position: 'bottom', fontSize: '12px' },
                    dataLabels: { enabled: false }
                }));
                this.charts.catPie.render();
            }

            // Daily line
            if (dailyData.days.length) {
                this.charts.daily = new ApexCharts(document.getElementById('chart-daily'), this.chartOpts({
                    chart: { type: 'area', height: 280, sparkline: { enabled: false } },
                    series: [{ name: 'Spending', data: dailyData.days.map(d => ({ x: d.date, y: d.amount })) }],
                    xaxis: { type: 'datetime' },
                    yaxis: { labels: { formatter: v => this.fmt(v) } },
                    stroke: { curve: 'smooth', width: 2 },
                    fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.3, opacityTo: 0.05 } },
                    colors: ['#3B82F6'],
                    dataLabels: { enabled: false }
                }));
                this.charts.daily.render();
            }

            // Monthly bar
            const months = monthlyData.months.slice().reverse();
            if (months.length) {
                const colors = months.map((m, i) => i === 0 ? '#3B82F6' : (i > 0 && m.amount <= months[i - 1].amount ? '#10B981' : '#EF4444'));
                this.charts.monthly = new ApexCharts(document.getElementById('chart-monthly'), this.chartOpts({
                    chart: { type: 'bar', height: 280 },
                    series: [{ name: 'Amount', data: months.map(m => m.amount) }],
                    xaxis: { categories: months.map(m => m.month) },
                    yaxis: { labels: { formatter: v => this.fmt(v) } },
                    plotOptions: { bar: { borderRadius: 6, distributed: true, columnWidth: '60%' } },
                    colors: colors,
                    legend: { show: false },
                    dataLabels: { enabled: false }
                }));
                this.charts.monthly.render();
            }

            // Category horizontal bar
            if (catData.categories.length) {
                this.charts.catBar = new ApexCharts(document.getElementById('chart-cat-bar'), this.chartOpts({
                    chart: { type: 'bar', height: 280 },
                    series: [{ name: 'Amount', data: catData.categories.map(c => c.total) }],
                    xaxis: { categories: catData.categories.map(c => c.category) },
                    yaxis: { labels: { formatter: v => this.fmt(v) } },
                    plotOptions: { bar: { horizontal: true, borderRadius: 4, barHeight: '65%' } },
                    colors: ['#3B82F6'],
                    dataLabels: { enabled: true, formatter: v => this.fmt(v), style: { fontSize: '11px' } }
                }));
                this.charts.catBar.render();
            }
        } catch (err) {
            content.innerHTML = `<div class="empty-state"><i class="ri-error-warning-line"></i><p>Error loading dashboard: ${err.message}</p></div>`;
        }
    },

    // ===== ADD EXPENSE =====
    async render_add() {
        const content = document.getElementById('content');
        const today = new Date().toISOString().split('T')[0];
        content.innerHTML = `
            <div class="card" style="max-width:600px;">
                <h3 style="margin-bottom:1.5rem;">Add New Expense</h3>
                <form id="add-form">
                    <div class="form-row">
                        <div class="form-group"><label>Amount (₹)</label><input type="number" id="add-amount" min="1" step="any" placeholder="Enter amount" required></div>
                        <div class="form-group"><label>Date</label><input type="date" id="add-date" value="${today}" max="${today}" required></div>
                    </div>
                    <div class="form-group"><label>Purpose</label><input type="text" id="add-purpose" placeholder="e.g., Lunch at restaurant" required></div>
                    <div class="form-group"><label>Category</label><select id="add-category">${this.categories.map(c => `<option value="${c}">${c}</option>`).join('')}</select></div>
                    <button type="submit" class="btn btn-primary btn-full mt-1"><i class="ri-add-line"></i> Add Expense</button>
                </form>
            </div>
        `;
        document.getElementById('add-form').onsubmit = async (e) => {
            e.preventDefault();
            const btn = e.target.querySelector('button[type="submit"]');
            btn.disabled = true; btn.textContent = 'Adding...';
            try {
                await API.addExpense({
                    amount: parseFloat(document.getElementById('add-amount').value),
                    purpose: document.getElementById('add-purpose').value.trim(),
                    category: document.getElementById('add-category').value,
                    date: document.getElementById('add-date').value
                });
                this.toast('Expense added!');
                e.target.reset();
                document.getElementById('add-date').value = today;
            } catch (err) { this.toast(err.message, 'error'); }
            btn.disabled = false; btn.innerHTML = '<i class="ri-add-line"></i> Add Expense';
        };
    },

    // ===== EXPENSES LIST =====
    async render_expenses() {
        const content = document.getElementById('content');
        const today = new Date().toISOString().split('T')[0];
        const monthStart = today.slice(0, 8) + '01';

        content.innerHTML = `
            <div class="filters-bar">
                <div class="form-group"><label>From</label><input type="date" id="f-start" value="${monthStart}"></div>
                <div class="form-group"><label>To</label><input type="date" id="f-end" value="${today}"></div>
                <div class="form-group"><label>Category</label><select id="f-cat"><option value="">All</option>${this.categories.map(c => `<option>${c}</option>`).join('')}</select></div>
                <div class="form-group"><label>Search</label><input type="text" id="f-search" placeholder="Search purpose..."></div>
                <div class="filter-actions">
                    <button class="btn btn-primary" id="f-apply"><i class="ri-search-line"></i> Filter</button>
                    <button class="btn btn-outline" id="f-export"><i class="ri-download-2-line"></i> CSV</button>
                </div>
            </div>
            <div class="card"><div id="expenses-table"></div></div>
        `;

        const loadExpenses = async () => {
            const params = {
                start_date: document.getElementById('f-start').value,
                end_date: document.getElementById('f-end').value,
                category: document.getElementById('f-cat').value,
                search: document.getElementById('f-search').value
            };
            const tbl = document.getElementById('expenses-table');
            tbl.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
            try {
                const res = await API.getExpenses(params);
                if (!res.expenses.length) {
                    tbl.innerHTML = '<div class="empty-state"><i class="ri-inbox-line"></i><p>No expenses found</p></div>';
                    return;
                }
                const total = res.expenses.reduce((s, e) => s + e.amount, 0);
                tbl.innerHTML = `
                    <div class="flex-between mb-1"><span class="text-muted text-sm">${res.total} expenses · Total: <strong>${this.fmt(total)}</strong></span></div>
                    <!-- Desktop table -->
                    <div class="table-wrap desktop-table"><table>
                        <thead><tr><th>Date</th><th>Purpose</th><th>Category</th><th>Amount</th><th>Actions</th></tr></thead>
                        <tbody>${res.expenses.map(e => `
                            <tr data-id="${e.id}">
                                <td class="date-cell">${e.date}</td>
                                <td>${this._esc(e.purpose)}</td>
                                <td><span class="category-badge">${this._esc(e.category)}</span></td>
                                <td class="amount-cell">${this.fmtD(e.amount)}</td>
                                <td class="actions-cell">
                                    <button class="btn-icon edit-btn" title="Edit"><i class="ri-edit-line"></i></button>
                                    <button class="btn-icon del-btn" title="Delete" style="color:var(--danger)"><i class="ri-delete-bin-line"></i></button>
                                </td>
                            </tr>
                        `).join('')}</tbody>
                    </table></div>
                    <!-- Mobile cards -->
                    <div class="expense-cards">
                        ${res.expenses.map(e => `
                        <div class="expense-card" data-id="${e.id}">
                            <div class="expense-card-top">
                                <span class="expense-card-purpose">${this._esc(e.purpose)}</span>
                                <span class="expense-card-amount">${this.fmtD(e.amount)}</span>
                            </div>
                            <div class="expense-card-bottom">
                                <div class="expense-card-meta">
                                    <span>${e.date}</span>
                                    <span class="category-badge">${this._esc(e.category)}</span>
                                </div>
                                <div class="expense-card-actions">
                                    <button class="btn-icon edit-btn" title="Edit"><i class="ri-edit-line"></i></button>
                                    <button class="btn-icon del-btn" title="Delete" style="color:var(--danger)"><i class="ri-delete-bin-line"></i></button>
                                </div>
                            </div>
                        </div>
                        `).join('')}
                    </div>
                `;

                // Edit buttons (works on both table rows and mobile cards)
                tbl.querySelectorAll('.edit-btn').forEach(btn => {
                    btn.onclick = () => {
                        const el = btn.closest('[data-id]');
                        const id = el.dataset.id;
                        const e = res.expenses.find(x => x.id == id);
                        if (e) this._showEditModal(e, loadExpenses);
                    };
                });

                // Delete buttons
                tbl.querySelectorAll('.del-btn').forEach(btn => {
                    btn.onclick = async () => {
                        const id = btn.closest('[data-id]').dataset.id;
                        if (!confirm('Delete this expense?')) return;
                        try { await API.deleteExpense(id); this.toast('Deleted'); loadExpenses(); } catch (err) { this.toast(err.message, 'error'); }
                    };
                });
            } catch (err) { tbl.innerHTML = `<div class="empty-state"><p>Error: ${err.message}</p></div>`; }
        };

        document.getElementById('f-apply').onclick = loadExpenses;
        document.getElementById('f-export').onclick = async () => {
            const params = { start_date: document.getElementById('f-start').value, end_date: document.getElementById('f-end').value, category: document.getElementById('f-cat').value, search: document.getElementById('f-search').value, limit: 10000 };
            try {
                const res = await API.getExpenses(params);
                const csv = 'Date,Purpose,Category,Amount\n' + res.expenses.map(e => `${e.date},"${e.purpose}","${e.category}",${e.amount}`).join('\n');
                const blob = new Blob([csv], { type: 'text/csv' });
                const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `expenses_${params.start_date}_${params.end_date}.csv`; a.click();
                this.toast('CSV exported!');
            } catch (err) { this.toast(err.message, 'error'); }
        };
        loadExpenses();
    },

    _showEditModal(expense, onSave) {
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.innerHTML = `
            <div class="modal">
                <h3>Edit Expense</h3>
                <form id="edit-form">
                    <div class="form-row">
                        <div class="form-group"><label>Amount</label><input type="number" id="ed-amt" value="${expense.amount}" min="1" step="any" required></div>
                        <div class="form-group"><label>Date</label><input type="date" id="ed-date" value="${expense.date}" required></div>
                    </div>
                    <div class="form-group"><label>Purpose</label><input type="text" id="ed-purpose" value="${this._esc(expense.purpose)}" required></div>
                    <div class="form-group"><label>Category</label><select id="ed-cat">${this.categories.map(c => `<option ${c === expense.category ? 'selected' : ''}>${c}</option>`).join('')}</select></div>
                    <div class="modal-actions">
                        <button type="button" class="btn btn-outline" id="ed-cancel">Cancel</button>
                        <button type="submit" class="btn btn-primary">Save</button>
                    </div>
                </form>
            </div>
        `;
        document.body.appendChild(overlay);
        overlay.querySelector('#ed-cancel').onclick = () => overlay.remove();
        overlay.querySelector('#edit-form').onsubmit = async (e) => {
            e.preventDefault();
            try {
                await API.updateExpense(expense.id, {
                    amount: parseFloat(document.getElementById('ed-amt').value),
                    purpose: document.getElementById('ed-purpose').value.trim(),
                    category: document.getElementById('ed-cat').value,
                    date: document.getElementById('ed-date').value
                });
                this.toast('Updated!');
                overlay.remove();
                onSave();
            } catch (err) { this.toast(err.message, 'error'); }
        };
    },

    _esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; },

    // ===== ANALYTICS =====
    async render_analytics() {
        const content = document.getElementById('content');
        content.innerHTML = `
            <div class="tabs">
                <button class="tab-btn active" data-tab="overview">Overview</button>
                <button class="tab-btn" data-tab="trends">Trends</button>
                <button class="tab-btn" data-tab="patterns">Patterns</button>
            </div>
            <div id="analytics-content"></div>
        `;
        const tabBtns = content.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.onclick = () => {
                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this['_analytics_' + btn.dataset.tab]();
            };
        });
        this._analytics_overview();
    },

    async _analytics_overview() {
        const el = document.getElementById('analytics-content');
        el.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
        try {
            const [overview, catData, topData] = await Promise.all([API.getOverview(), API.getCategorySummary(), API.getTop({ limit: 10 })]);
            el.innerHTML = `
                <div class="metrics-grid">
                    <div class="metric-card accent-blue"><div class="metric-label">Total Spent</div><div class="metric-value">${this.fmt(overview.total_amount)}</div></div>
                    <div class="metric-card accent-green"><div class="metric-label">Avg Transaction</div><div class="metric-value">${this.fmt(overview.avg_amount)}</div></div>
                    <div class="metric-card accent-amber"><div class="metric-label">Transactions</div><div class="metric-value">${overview.total_transactions}</div></div>
                    <div class="metric-card accent-red"><div class="metric-label">Max / Min</div><div class="metric-value">${this.fmt(overview.max_amount)}</div><div class="metric-sub">Min: ${this.fmt(overview.min_amount)}</div></div>
                </div>
                <div class="charts-grid">
                    <div class="card"><div class="card-header"><h3>Category Breakdown</h3></div><div id="a-cat-tree"></div></div>
                    <div class="card"><div class="card-header"><h3>Top 10 Expenses</h3></div>
                        <div class="table-wrap desktop-table"><table><thead><tr><th>Date</th><th>Purpose</th><th>Category</th><th>Amount</th></tr></thead>
                        <tbody>${topData.expenses.map(e => `<tr><td class="date-cell">${e.date}</td><td>${this._esc(e.purpose)}</td><td><span class="category-badge">${this._esc(e.category)}</span></td><td class="amount-cell">${this.fmtD(e.amount)}</td></tr>`).join('')}</tbody></table></div>
                        <div class="expense-cards">${topData.expenses.map(e => `
                            <div class="expense-card">
                                <div class="expense-card-top"><span class="expense-card-purpose">${this._esc(e.purpose)}</span><span class="expense-card-amount">${this.fmtD(e.amount)}</span></div>
                                <div class="expense-card-meta"><span>${e.date}</span><span class="category-badge">${this._esc(e.category)}</span></div>
                            </div>`).join('')}</div>
                    </div>
                </div>
            `;
            if (catData.categories.length) {
                this.charts.aCatTree = new ApexCharts(document.getElementById('a-cat-tree'), this.chartOpts({
                    chart: { type: 'treemap', height: 300 },
                    series: [{ data: catData.categories.map(c => ({ x: c.category, y: c.total })) }],
                    plotOptions: { treemap: { distributed: true, enableShades: false } },
                    dataLabels: { enabled: true, formatter: (text, op) => [text, this.fmt(op.value)], style: { fontSize: '12px' } }
                }));
                this.charts.aCatTree.render();
            }
        } catch (err) { el.innerHTML = `<div class="empty-state"><p>Error: ${err.message}</p></div>`; }
    },

    async _analytics_trends() {
        const el = document.getElementById('analytics-content');
        el.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
        try {
            const [monthlyData, catTrend] = await Promise.all([API.getMonthly(), API.getCategoryTrend()]);
            const months = monthlyData.months.slice().reverse();

            el.innerHTML = `
                <div class="charts-grid">
                    <div class="card chart-full"><div class="card-header"><h3>Monthly Trend</h3></div><div id="a-monthly-trend"></div></div>
                    <div class="card chart-full"><div class="card-header"><h3>Category Trends Over Time</h3></div><div id="a-cat-trend"></div></div>
                </div>
            `;

            // Monthly trend with MoM change
            if (months.length) {
                const changes = months.map((m, i) => i === 0 ? 0 : ((m.amount - months[i - 1].amount) / months[i - 1].amount * 100));
                this.charts.aMonthly = new ApexCharts(document.getElementById('a-monthly-trend'), this.chartOpts({
                    chart: { type: 'line', height: 320 },
                    series: [
                        { name: 'Amount', type: 'column', data: months.map(m => m.amount) },
                        { name: 'MoM Change %', type: 'line', data: changes }
                    ],
                    xaxis: { categories: months.map(m => m.month) },
                    yaxis: [
                        { title: { text: 'Amount (₹)' }, labels: { formatter: v => this.fmt(v) } },
                        { opposite: true, title: { text: 'Change (%)' }, labels: { formatter: v => v.toFixed(1) + '%' } }
                    ],
                    stroke: { width: [0, 3] },
                    colors: ['#3B82F6', '#F59E0B'],
                    dataLabels: { enabled: false }
                }));
                this.charts.aMonthly.render();
            }

            // Category trend
            if (catTrend.data.length) {
                const allMonths = [...new Set(catTrend.data.map(d => d.month))].sort();
                const allCats = [...new Set(catTrend.data.map(d => d.category))];
                const series = allCats.map(cat => ({
                    name: cat,
                    data: allMonths.map(m => { const found = catTrend.data.find(d => d.month === m && d.category === cat); return found ? found.amount : 0; })
                }));
                this.charts.aCatTrend = new ApexCharts(document.getElementById('a-cat-trend'), this.chartOpts({
                    chart: { type: 'area', height: 350, stacked: true },
                    series: series,
                    xaxis: { categories: allMonths },
                    yaxis: { labels: { formatter: v => this.fmt(v) } },
                    stroke: { curve: 'smooth', width: 2 },
                    fill: { type: 'gradient', gradient: { opacityFrom: 0.5, opacityTo: 0.1 } },
                    legend: { position: 'bottom' },
                    dataLabels: { enabled: false }
                }));
                this.charts.aCatTrend.render();
            }
        } catch (err) { el.innerHTML = `<div class="empty-state"><p>Error: ${err.message}</p></div>`; }
    },

    async _analytics_patterns() {
        const el = document.getElementById('analytics-content');
        el.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
        try {
            const [weeklyData, heatmapData] = await Promise.all([API.getWeekly(), API.getHeatmap()]);
            el.innerHTML = `
                <div class="charts-grid">
                    <div class="card"><div class="card-header"><h3>Day of Week</h3></div><div id="a-weekly"></div></div>
                    <div class="card"><div class="card-header"><h3>Spending Heatmap (6 months)</h3></div><div id="a-heatmap"></div></div>
                </div>
            `;

            // Weekly pattern
            if (weeklyData.days.length) {
                const ordered = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
                const sortedDays = ordered.map(d => weeklyData.days.find(w => w.day === d) || { day: d, total: 0, count: 0, avg: 0 });
                this.charts.aWeekly = new ApexCharts(document.getElementById('a-weekly'), this.chartOpts({
                    chart: { type: 'radar', height: 300 },
                    series: [
                        { name: 'Total', data: sortedDays.map(d => d.total) },
                        { name: 'Avg', data: sortedDays.map(d => d.avg) }
                    ],
                    xaxis: { categories: sortedDays.map(d => d.day.slice(0, 3)) },
                    colors: ['#3B82F6', '#10B981'],
                    stroke: { width: 2 },
                    fill: { opacity: 0.15 },
                    yaxis: { show: false }
                }));
                this.charts.aWeekly.render();
            }

            // Heatmap
            if (heatmapData.data.length) {
                const byWeekDay = {};
                heatmapData.data.forEach(d => {
                    const dt = new Date(d.date);
                    const week = this._getWeek(dt);
                    const day = dt.getDay();
                    const key = `${week}-${day}`;
                    byWeekDay[key] = (byWeekDay[key] || 0) + d.amount;
                });

                const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
                const weeks = [...new Set(heatmapData.data.map(d => this._getWeek(new Date(d.date))))].sort();
                const series = dayNames.map((name, dayIdx) => ({
                    name: name,
                    data: weeks.map(w => ({ x: 'W' + w, y: Math.round(byWeekDay[`${w}-${dayIdx}`] || 0) }))
                }));

                this.charts.aHeatmap = new ApexCharts(document.getElementById('a-heatmap'), this.chartOpts({
                    chart: { type: 'heatmap', height: 300 },
                    series: series,
                    colors: ['#3B82F6'],
                    plotOptions: { heatmap: { shadeIntensity: 0.5, radius: 4, colorScale: { ranges: [
                        { from: 0, to: 0, color: '#E2E8F0', name: 'None' },
                        { from: 1, to: 500, color: '#93C5FD', name: 'Low' },
                        { from: 501, to: 2000, color: '#3B82F6', name: 'Medium' },
                        { from: 2001, to: 100000, color: '#1E3A8A', name: 'High' }
                    ] } } },
                    dataLabels: { enabled: false },
                    xaxis: { labels: { show: false } }
                }));
                this.charts.aHeatmap.render();
            }
        } catch (err) { el.innerHTML = `<div class="empty-state"><p>Error: ${err.message}</p></div>`; }
    },

    _getWeek(d) {
        const oneJan = new Date(d.getFullYear(), 0, 1);
        return Math.ceil(((d - oneJan) / 86400000 + oneJan.getDay() + 1) / 7);
    },

    // ===== BUDGET =====
    async render_budget() {
        const content = document.getElementById('content');
        const cm = new Date().toISOString().slice(0, 7);
        content.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
        try {
            const [overview, budgets] = await Promise.all([API.getOverview(), API.getBudgets()]);
            const currentBudget = budgets.budgets.find(b => b.month === cm);
            const budgetAmt = currentBudget ? currentBudget.amount : 0;
            const spent = overview.this_month;
            const pct = budgetAmt > 0 ? Math.min((spent / budgetAmt) * 100, 150) : 0;
            const remaining = budgetAmt - spent;
            const safeDaily = remaining > 0 ? remaining / Math.max(overview.days_remaining, 1) : 0;
            const gaugeColor = pct > 90 ? '#EF4444' : pct > 70 ? '#F59E0B' : '#10B981';

            content.innerHTML = `
                <div class="grid-2 mb-2">
                    <div class="card">
                        <h3 style="margin-bottom:1rem;">Set Monthly Budget</h3>
                        <form id="budget-form">
                            <div class="form-row">
                                <div class="form-group"><label>Month</label><input type="month" id="budget-month" value="${cm}" required></div>
                                <div class="form-group"><label>Amount (₹)</label><input type="number" id="budget-amt" value="${budgetAmt || ''}" min="1000" step="500" placeholder="50000" required></div>
                            </div>
                            <button type="submit" class="btn btn-primary btn-full mt-1">Save Budget</button>
                        </form>
                    </div>
                    <div class="card budget-gauge">
                        <div id="gauge-chart"></div>
                        <div class="text-muted">${budgetAmt > 0 ? `${this.fmt(spent)} of ${this.fmt(budgetAmt)}` : 'No budget set'}</div>
                    </div>
                </div>
                ${budgetAmt > 0 ? `
                <div class="metrics-grid">
                    <div class="metric-card accent-blue"><div class="metric-label">Budget</div><div class="metric-value">${this.fmt(budgetAmt)}</div></div>
                    <div class="metric-card accent-green"><div class="metric-label">Remaining</div><div class="metric-value">${this.fmt(Math.max(remaining, 0))}</div><div class="metric-sub ${remaining < 0 ? 'up' : ''}">${remaining < 0 ? 'Over by ' + this.fmt(Math.abs(remaining)) : ''}</div></div>
                    <div class="metric-card accent-amber"><div class="metric-label">Safe Daily Spend</div><div class="metric-value">${this.fmt(safeDaily)}</div><div class="metric-sub">${overview.days_remaining} days left</div></div>
                    <div class="metric-card accent-red"><div class="metric-label">Burn Rate</div><div class="metric-value">${this.fmt(overview.daily_avg)}/day</div><div class="metric-sub">Projected: ${this.fmt(overview.projected)}</div></div>
                </div>` : ''}
            `;

            // Gauge chart
            if (budgetAmt > 0) {
                this.charts.gauge = new ApexCharts(document.getElementById('gauge-chart'), {
                    chart: { type: 'radialBar', height: 200, fontFamily: 'Inter' },
                    series: [Math.min(pct, 100).toFixed(0)],
                    plotOptions: { radialBar: {
                        hollow: { size: '60%' },
                        track: { background: document.documentElement.getAttribute('data-theme') === 'dark' ? '#334155' : '#E2E8F0' },
                        dataLabels: { name: { show: true, color: gaugeColor, fontSize: '14px' }, value: { fontSize: '28px', fontWeight: 700, formatter: () => pct.toFixed(0) + '%' } }
                    } },
                    colors: [gaugeColor],
                    labels: [pct > 90 ? 'Over Budget!' : pct > 70 ? 'Warning' : 'On Track']
                });
                this.charts.gauge.render();
            }

            document.getElementById('budget-form').onsubmit = async (e) => {
                e.preventDefault();
                try {
                    await API.setBudget(document.getElementById('budget-month').value, parseFloat(document.getElementById('budget-amt').value));
                    this.toast('Budget saved!');
                    this.render_budget();
                } catch (err) { this.toast(err.message, 'error'); }
            };
        } catch (err) { content.innerHTML = `<div class="empty-state"><p>Error: ${err.message}</p></div>`; }
    },

    // ===== AI INSIGHTS =====
    async render_ai() {
        const content = document.getElementById('content');
        content.innerHTML = `
            <div class="card mb-2" style="max-width:700px;">
                <h3 style="margin-bottom:1rem;">🤖 AI Financial Assistant</h3>
                <p class="text-muted mb-1">Get personalized insights powered by AI analysis of your spending data.</p>
                <div class="form-group"><label>Analysis Type</label>
                    <select id="ai-type">
                        <option value="general">💡 General Spending Analysis</option>
                        <option value="budget">💰 Budget Planning</option>
                        <option value="savings">💸 Savings Opportunities</option>
                        <option value="anomaly">🔍 Anomaly Detection</option>
                    </select>
                </div>
                <div class="form-group hidden" id="ai-budget-group"><label>Monthly Budget (₹)</label><input type="number" id="ai-budget" value="50000" min="1000" step="1000"></div>
                <button class="btn btn-primary btn-full" id="ai-btn"><i class="ri-magic-line"></i> Analyze My Spending</button>
            </div>
            <div id="ai-result"></div>
        `;

        document.getElementById('ai-type').onchange = (e) => {
            document.getElementById('ai-budget-group').classList.toggle('hidden', e.target.value !== 'budget');
        };

        document.getElementById('ai-btn').onclick = async () => {
            const type = document.getElementById('ai-type').value;
            const budget = type === 'budget' ? parseFloat(document.getElementById('ai-budget').value) : null;
            const resultEl = document.getElementById('ai-result');
            const btn = document.getElementById('ai-btn');
            btn.disabled = true; btn.innerHTML = '<div class="spinner" style="width:20px;height:20px;margin:0;border-width:2px;display:inline-block;vertical-align:middle;"></div> Analyzing...';
            resultEl.innerHTML = '';
            try {
                const res = await API.analyze(type, budget);
                resultEl.innerHTML = `<div class="card ai-result">${marked.parse(res.analysis)}</div>`;
            } catch (err) { resultEl.innerHTML = `<div class="alert alert-error">${err.message}</div>`; }
            btn.disabled = false; btn.innerHTML = '<i class="ri-magic-line"></i> Analyze My Spending';
        };
    },

    // ===== ADMIN PANEL =====
    async render_admin() {
        const content = document.getElementById('content');
        if (!API.isAdmin()) {
            content.innerHTML = '<div class="empty-state"><i class="ri-lock-line"></i><p>Admin access required</p></div>';
            return;
        }

        content.innerHTML = `
            <div class="tabs">
                <button class="tab-btn active" data-tab="users">Users</button>
                <button class="tab-btn" data-tab="adduser">Add User</button>
                <button class="tab-btn" data-tab="settings">Settings</button>
            </div>
            <div id="admin-content"></div>
        `;
        const tabBtns = content.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.onclick = () => {
                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this['_admin_' + btn.dataset.tab]();
            };
        });
        this._admin_users();
    },

    async _admin_users() {
        const el = document.getElementById('admin-content');
        el.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
        try {
            const res = await API.getUsers();
            const currentUser = API.getUser();
            el.innerHTML = `
                <div class="card mt-1">
                    <div class="card-header"><h3>All Users (${res.users.length})</h3></div>
                    <!-- Desktop table -->
                    <div class="table-wrap desktop-table"><table>
                        <thead><tr><th>ID</th><th>Username</th><th>Full Name</th><th>Role</th><th>Expenses</th><th>Total Spent</th><th>Created</th><th>Actions</th></tr></thead>
                        <tbody>${res.users.map(u => `
                            <tr data-uid="${u.id}">
                                <td>${u.id}</td>
                                <td><strong>${this._esc(u.username)}</strong></td>
                                <td>${this._esc(u.full_name)}</td>
                                <td>${u.is_admin ? '<span class="category-badge" style="background:var(--danger-light);color:var(--danger)">Admin</span>' : '<span class="category-badge">User</span>'}</td>
                                <td>${u.expense_count}</td>
                                <td class="amount-cell">${this.fmt(u.total_spent)}</td>
                                <td class="date-cell">${u.created_at ? u.created_at.slice(0, 10) : 'N/A'}</td>
                                <td class="actions-cell">
                                    <button class="btn btn-sm btn-outline reset-pwd-btn" data-uid="${u.id}" data-name="${this._esc(u.username)}" title="Reset password"><i class="ri-lock-password-line"></i></button>
                                    ${u.id !== currentUser.id ? `<button class="btn btn-sm btn-danger del-user-btn" data-uid="${u.id}" data-name="${this._esc(u.username)}" title="Delete user"><i class="ri-delete-bin-line"></i></button>` : '<span class="text-muted text-sm">(you)</span>'}
                                </td>
                            </tr>
                        `).join('')}</tbody>
                    </table></div>
                    <!-- Mobile cards -->
                    <div class="expense-cards">
                        ${res.users.map(u => `
                        <div class="expense-card" data-uid="${u.id}">
                            <div class="expense-card-top">
                                <span class="expense-card-purpose">${this._esc(u.full_name)} <small style="color:var(--text-muted)">@${this._esc(u.username)}</small></span>
                                ${u.is_admin ? '<span class="category-badge" style="background:var(--danger-light);color:var(--danger);font-size:.7rem">Admin</span>' : '<span class="category-badge" style="font-size:.7rem">User</span>'}
                            </div>
                            <div style="display:flex;gap:1rem;font-size:.8rem;color:var(--text-secondary);margin:.35rem 0;">
                                <span>${u.expense_count} expenses</span>
                                <span>${this.fmt(u.total_spent)}</span>
                                <span>${u.created_at ? u.created_at.slice(0, 10) : ''}</span>
                            </div>
                            <div class="expense-card-actions" style="margin-top:.35rem;">
                                <button class="btn btn-sm btn-outline reset-pwd-btn" data-uid="${u.id}" data-name="${this._esc(u.username)}"><i class="ri-lock-password-line"></i> Reset Pwd</button>
                                ${u.id !== currentUser.id ? `<button class="btn btn-sm btn-danger del-user-btn" data-uid="${u.id}" data-name="${this._esc(u.username)}"><i class="ri-delete-bin-line"></i> Delete</button>` : '<span class="text-muted text-sm">(you)</span>'}
                            </div>
                        </div>
                        `).join('')}
                    </div>
                </div>
            `;

            // Reset password buttons
            el.querySelectorAll('.reset-pwd-btn').forEach(btn => {
                btn.onclick = () => {
                    const uid = parseInt(btn.dataset.uid);
                    const uname = btn.dataset.name;
                    this._showResetPasswordModal(uid, uname);
                };
            });

            // Delete buttons
            el.querySelectorAll('.del-user-btn').forEach(btn => {
                btn.onclick = async () => {
                    const uid = parseInt(btn.dataset.uid);
                    const uname = btn.dataset.name;
                    if (!confirm(`Delete user "${uname}" and ALL their data? This cannot be undone.`)) return;
                    try { await API.deleteUser(uid); this.toast('User deleted'); this._admin_users(); } catch (err) { this.toast(err.message, 'error'); }
                };
            });
        } catch (err) { el.innerHTML = `<div class="empty-state"><p>Error: ${err.message}</p></div>`; }
    },

    _showResetPasswordModal(userId, username) {
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.innerHTML = `
            <div class="modal">
                <h3>Reset Password for "${username}"</h3>
                <form id="reset-pwd-form">
                    <div class="form-group"><label>New Password</label>
                        <div style="display:flex;gap:.5rem;">
                            <input type="password" id="rp-new" placeholder="Min 8 characters" required minlength="8" style="flex:1">
                            <button type="button" class="btn btn-outline btn-sm" id="rp-toggle" title="Show/hide"><i class="ri-eye-line"></i></button>
                        </div>
                    </div>
                    <div class="form-group"><label>Confirm Password</label><input type="password" id="rp-confirm" placeholder="Re-enter password" required></div>
                    <div id="rp-result" class="hidden"></div>
                    <div class="modal-actions">
                        <button type="button" class="btn btn-outline" id="rp-cancel">Cancel</button>
                        <button type="submit" class="btn btn-primary">Reset Password</button>
                    </div>
                </form>
            </div>
        `;
        document.body.appendChild(overlay);
        overlay.querySelector('#rp-toggle').onclick = () => {
            const inp = document.getElementById('rp-new');
            inp.type = inp.type === 'password' ? 'text' : 'password';
            overlay.querySelector('#rp-toggle i').className = inp.type === 'password' ? 'ri-eye-line' : 'ri-eye-off-line';
        };
        overlay.querySelector('#rp-cancel').onclick = () => overlay.remove();
        overlay.querySelector('#reset-pwd-form').onsubmit = async (e) => {
            e.preventDefault();
            const pwd = document.getElementById('rp-new').value;
            const confirm = document.getElementById('rp-confirm').value;
            if (pwd !== confirm) { this.toast('Passwords do not match', 'error'); return; }
            if (pwd.length < 8) { this.toast('Password must be at least 8 characters', 'error'); return; }
            try {
                await API.resetUserPassword(userId, pwd);
                this.toast('Password reset!');
                const resEl = document.getElementById('rp-result');
                resEl.classList.remove('hidden');
                resEl.innerHTML = `<div class="alert alert-success" style="margin-top:.75rem;">Password set to: <strong style="user-select:all;cursor:pointer;">${this._esc(pwd)}</strong> <br><small>Copy it now — it won't be shown again.</small></div>`;
            } catch (err) { this.toast(err.message, 'error'); }
        };
    },

    _admin_adduser() {
        const el = document.getElementById('admin-content');
        el.innerHTML = `
            <div class="card mt-1" style="max-width:500px;">
                <h3 style="margin-bottom:1rem;">Add New User</h3>
                <form id="add-user-form">
                    <div class="form-group"><label>Username</label><input type="text" id="nu-user" placeholder="e.g., john" required pattern="[a-zA-Z0-9_]{3,20}" title="3-20 chars, letters/numbers/underscore"></div>
                    <div class="form-group"><label>Full Name</label><input type="text" id="nu-name" placeholder="e.g., John Doe" required></div>
                    <div class="form-group"><label>Password</label>
                        <div style="display:flex;gap:.5rem;">
                            <input type="password" id="nu-pass" placeholder="Min 8 characters" required minlength="8" style="flex:1">
                            <button type="button" class="btn btn-outline btn-sm" id="nu-toggle" title="Show/hide"><i class="ri-eye-line"></i></button>
                        </div>
                    </div>
                    <div id="nu-result" class="hidden"></div>
                    <button type="submit" class="btn btn-primary btn-full mt-1"><i class="ri-user-add-line"></i> Create User</button>
                </form>
            </div>
        `;
        document.getElementById('nu-toggle').onclick = () => {
            const inp = document.getElementById('nu-pass');
            inp.type = inp.type === 'password' ? 'text' : 'password';
            document.querySelector('#nu-toggle i').className = inp.type === 'password' ? 'ri-eye-line' : 'ri-eye-off-line';
        };
        document.getElementById('add-user-form').onsubmit = async (e) => {
            e.preventDefault();
            const btn = e.target.querySelector('button[type="submit"]');
            btn.disabled = true; btn.textContent = 'Creating...';
            const username = document.getElementById('nu-user').value.trim();
            const password = document.getElementById('nu-pass').value;
            try {
                await API.register({
                    username: username,
                    full_name: document.getElementById('nu-name').value.trim(),
                    password: password
                });
                this.toast('User created!');
                const resEl = document.getElementById('nu-result');
                resEl.classList.remove('hidden');
                resEl.innerHTML = `<div class="alert alert-success" style="margin-top:.75rem;">User <strong>${this._esc(username)}</strong> created.<br>Password: <strong style="user-select:all;cursor:pointer;">${this._esc(password)}</strong><br><small>Save these credentials — password won't be shown again.</small></div>`;
            } catch (err) { this.toast(err.message, 'error'); }
            btn.disabled = false; btn.innerHTML = '<i class="ri-user-add-line"></i> Create User';
        };
    },

    _admin_settings() {
        const el = document.getElementById('admin-content');
        el.innerHTML = `
            <div class="card mt-1" style="max-width:500px;">
                <h3 style="margin-bottom:1rem;">Change Your Password</h3>
                <form id="chg-pwd-form">
                    <div class="form-group"><label>Current Password</label><input type="password" id="cp-old" required></div>
                    <div class="form-group"><label>New Password</label><input type="password" id="cp-new" required minlength="8"></div>
                    <div class="form-group"><label>Confirm New Password</label><input type="password" id="cp-confirm" required></div>
                    <button type="submit" class="btn btn-primary btn-full mt-1"><i class="ri-lock-line"></i> Update Password</button>
                </form>
            </div>
            <div class="card mt-1" style="max-width:500px;">
                <h3 style="margin-bottom:1rem;">Database Health</h3>
                <p class="text-muted mb-1">SQLite Cloud is pinged every hour to keep the free instance alive.</p>
                <button class="btn btn-outline" id="manual-ping"><i class="ri-signal-wifi-line"></i> Ping Now</button>
                <div id="ping-result" class="mt-1"></div>
            </div>
        `;
        document.getElementById('chg-pwd-form').onsubmit = async (e) => {
            e.preventDefault();
            const newP = document.getElementById('cp-new').value;
            const confirm = document.getElementById('cp-confirm').value;
            if (newP !== confirm) { this.toast('Passwords do not match', 'error'); return; }
            try {
                await API.changePassword(document.getElementById('cp-old').value, newP);
                this.toast('Password updated!');
                e.target.reset();
            } catch (err) { this.toast(err.message, 'error'); }
        };
        document.getElementById('manual-ping').onclick = async () => {
            const res_el = document.getElementById('ping-result');
            try {
                const res = await API.ping();
                res_el.innerHTML = `<div class="alert alert-success">✅ DB alive at ${res.timestamp}</div>`;
            } catch (err) { res_el.innerHTML = `<div class="alert alert-error">❌ Ping failed: ${err.message}</div>`; }
        };
    },
};

// Boot
document.addEventListener('DOMContentLoaded', () => App.init());
