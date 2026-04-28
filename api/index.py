import os
import asyncio
import hashlib
import logging
import sqlitecloud
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from jose import jwt, JWTError
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("expense-tracker")
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Config ---
SQL_URL = os.getenv("SQL_URL")
JWT_SECRET = os.getenv("JWT_SECRET", "expense-tracker-jwt-secret-2026")
AZURE_API_KEY = os.getenv("AZURE_API_KEY")
AZURE_API_BASE = os.getenv("AZURE_API_BASE")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2025-01-01-preview")
ADMIN_DEFAULT_PASSWORD = os.getenv("ADMIN_DEFAULT_PASSWORD", "Admin@2026")
KEEP_ALIVE_INTERVAL = 3600  # seconds (1 hour)

CATEGORIES = [
    "🍔 Food & Dining", "🚗 Transportation", "🏠 Housing & Utilities",
    "🛒 Groceries", "💊 Healthcare", "🎬 Entertainment", "👕 Clothing",
    "📚 Education", "🎁 Gifts", "💰 Savings & Investment", "🔧 Maintenance",
    "☎️ Communication", "✈️ Travel", "🏋️ Fitness", "📱 Technology", "📦 Other"
]

# --- Keep-alive background task ---
async def _keep_alive_loop():
    """Ping SQLite Cloud every hour to keep the free instance alive."""
    while True:
        try:
            conn = sqlitecloud.connect(SQL_URL)
            c = conn.cursor()
            c.execute("SELECT 1")
            _release(conn)
            logger.info("Keep-alive ping to SQLite Cloud succeeded")
        except Exception as e:
            logger.warning(f"Keep-alive ping failed: {e}")
        await asyncio.sleep(KEEP_ALIVE_INTERVAL)


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(_keep_alive_loop())
    logger.info("Keep-alive async task started")
    yield
    task.cancel()


# --- App ---
app = FastAPI(title="Expense Tracker API", docs_url="/api/docs", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Auth Helpers ---
security = HTTPBearer()


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _token(data: dict) -> str:
    return jwt.encode({**data, "exp": datetime.utcnow() + timedelta(days=30)}, JWT_SECRET, algorithm="HS256")


def _auth(cred: HTTPAuthorizationCredentials = Depends(security)):
    try:
        return jwt.decode(cred.credentials, JWT_SECRET, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")


# --- Connection pool with retry ---
import threading as _threading

_pool_lock = _threading.Lock()
_pool: list = []          # reusable connections
_POOL_MAX = 3
_RETRY_ATTEMPTS = 3
_RETRY_DELAY = 0.5        # seconds


def _new_conn():
    return sqlitecloud.connect(SQL_URL)


def _conn():
    """Get a connection — reuse from pool or create new, with retry on failure."""
    with _pool_lock:
        if _pool:
            conn = _pool.pop()
            try:
                conn.cursor().execute("SELECT 1")
                return conn
            except Exception:
                try:
                    _release(conn)
                except Exception:
                    pass

    last_err = None
    for attempt in range(_RETRY_ATTEMPTS):
        try:
            return _new_conn()
        except Exception as e:
            last_err = e
            logger.warning(f"DB connect attempt {attempt+1}/{_RETRY_ATTEMPTS} failed: {e}")
            if attempt < _RETRY_ATTEMPTS - 1:
                import time
                time.sleep(_RETRY_DELAY * (attempt + 1))

    raise HTTPException(503, f"Database temporarily unavailable. Please try again.")


def _release(conn):
    """Return a connection to the pool instead of closing it."""
    try:
        with _pool_lock:
            if len(_pool) < _POOL_MAX:
                _pool.append(conn)
                return
        conn.close()
    except Exception:
        pass


# --- DB Init ---
def _init_db():
    conn = _conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    # Migration: add is_admin column if missing (existing DBs)
    try:
        c.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
    except Exception:
        pass
    # Ensure 'admin' user has is_admin=1
    c.execute("UPDATE users SET is_admin=1 WHERE username='admin'")
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        purpose TEXT NOT NULL,
        category TEXT NOT NULL,
        date DATE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        month TEXT NOT NULL,
        amount REAL NOT NULL,
        UNIQUE(user_id, month),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    conn.commit()
    _release(conn)


def _seed_admin():
    """Create default admin user if no users exist."""
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    if count == 0:
        c.execute("INSERT INTO users (username, password_hash, full_name, is_admin) VALUES (?,?,?,1)",
                  ("admin", _hash(ADMIN_DEFAULT_PASSWORD), "Administrator"))
        conn.commit()
        logger.info("Default admin user created (username: admin)")
    _release(conn)


try:
    _init_db()
    _seed_admin()
except Exception:
    pass


# --- Models ---
class LoginReq(BaseModel):
    username: str
    password: str

class RegisterReq(BaseModel):
    username: str
    password: str
    full_name: str

class ExpenseIn(BaseModel):
    amount: float = Field(gt=0)
    purpose: str
    category: str
    date: str

class ExpenseUpdate(BaseModel):
    amount: Optional[float] = None
    purpose: Optional[str] = None
    category: Optional[str] = None
    date: Optional[str] = None

class BudgetIn(BaseModel):
    month: str
    amount: float = Field(gt=0)

class AIReq(BaseModel):
    type: str = "general"
    budget: Optional[float] = None


# --- Utility endpoint ---
@app.get("/api/categories")
def get_categories():
    return {"categories": CATEGORIES}


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


# ===================== AUTH =====================

@app.post("/api/auth/login")
def login(req: LoginReq):
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT id, username, full_name, is_admin FROM users WHERE username = ? AND password_hash = ?",
              (req.username, _hash(req.password)))
    u = c.fetchone()
    _release(conn)
    if not u:
        raise HTTPException(401, "Invalid credentials")
    user = {"id": u[0], "username": u[1], "full_name": u[2], "is_admin": bool(u[3])}
    return {"token": _token(user), "user": user}


@app.post("/api/auth/register")
def register(req: RegisterReq, user=Depends(_auth)):
    _require_admin(user)
    conn = _conn()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash, full_name) VALUES (?,?,?)",
                  (req.username, _hash(req.password), req.full_name))
        conn.commit()
        return {"message": "User created", "id": c.lastrowid}
    except Exception as e:
        raise HTTPException(400, str(e))
    finally:
        _release(conn)


class ChangePasswordReq(BaseModel):
    old_password: str
    new_password: str

class AdminResetPasswordReq(BaseModel):
    user_id: int
    new_password: str


@app.post("/api/auth/change-password")
def change_password(req: ChangePasswordReq, user=Depends(_auth)):
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE id = ?", (user["id"],))
    row = c.fetchone()
    if not row or row[0] != _hash(req.old_password):
        _release(conn)
        raise HTTPException(400, "Current password is incorrect")
    c.execute("UPDATE users SET password_hash = ? WHERE id = ?", (_hash(req.new_password), user["id"]))
    conn.commit()
    _release(conn)
    return {"message": "Password changed"}


@app.get("/api/auth/me")
def get_me(user=Depends(_auth)):
    return {"user": user}


# ===================== EXPENSES =====================

def _where(uid, start=None, end=None, category=None, search=None):
    q = "WHERE user_id = ?"
    p = [uid]
    if start:
        q += " AND date >= ?"; p.append(start)
    if end:
        q += " AND date <= ?"; p.append(end)
    if category and category != "All":
        q += " AND category = ?"; p.append(category)
    if search:
        q += " AND purpose LIKE ?"; p.append(f"%{search}%")
    return q, p


@app.get("/api/expenses")
def list_expenses(
    start_date: Optional[str] = None, end_date: Optional[str] = None,
    category: Optional[str] = None, search: Optional[str] = None,
    limit: int = 200, offset: int = 0, user=Depends(_auth)
):
    conn = _conn(); c = conn.cursor()
    w, p = _where(user["id"], start_date, end_date, category, search)

    c.execute(f"SELECT COUNT(*) FROM expenses {w}", p)
    total = c.fetchone()[0]

    c.execute(f"SELECT id,amount,purpose,category,date,created_at FROM expenses {w} ORDER BY date DESC LIMIT ? OFFSET ?",
              p + [limit, offset])
    rows = c.fetchall()
    _release(conn)
    return {
        "expenses": [{"id": r[0],"amount": r[1],"purpose": r[2],"category": r[3],"date": r[4],"created_at": r[5]} for r in rows],
        "total": total
    }


@app.post("/api/expenses")
def add_expense(exp: ExpenseIn, user=Depends(_auth)):
    conn = _conn(); c = conn.cursor()
    c.execute("INSERT INTO expenses (user_id,amount,purpose,category,date) VALUES (?,?,?,?,?)",
              (user["id"], exp.amount, exp.purpose.strip(), exp.category, exp.date))
    conn.commit(); eid = c.lastrowid; _release(conn)
    return {"message": "Expense added", "id": eid}


@app.put("/api/expenses/{eid}")
def update_expense(eid: int, exp: ExpenseUpdate, user=Depends(_auth)):
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT user_id FROM expenses WHERE id = ?", (eid,))
    row = c.fetchone()
    if not row or row[0] != user["id"]:
        _release(conn); raise HTTPException(404, "Not found")

    sets, vals = [], []
    if exp.amount is not None: sets.append("amount=?"); vals.append(exp.amount)
    if exp.purpose is not None: sets.append("purpose=?"); vals.append(exp.purpose.strip())
    if exp.category is not None: sets.append("category=?"); vals.append(exp.category)
    if exp.date is not None: sets.append("date=?"); vals.append(exp.date)
    if sets:
        vals.append(eid)
        c.execute(f"UPDATE expenses SET {','.join(sets)} WHERE id=?", vals)
        conn.commit()
    _release(conn)
    return {"message": "Updated"}


@app.delete("/api/expenses/{eid}")
def delete_expense(eid: int, user=Depends(_auth)):
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT user_id FROM expenses WHERE id = ?", (eid,))
    row = c.fetchone()
    if not row or row[0] != user["id"]:
        _release(conn); raise HTTPException(404, "Not found")
    c.execute("DELETE FROM expenses WHERE id=?", (eid,))
    conn.commit(); _release(conn)
    return {"message": "Deleted"}


# ===================== BUDGETS =====================

@app.get("/api/budgets")
def get_budgets(user=Depends(_auth)):
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT id,month,amount FROM budgets WHERE user_id=? ORDER BY month DESC LIMIT 12", (user["id"],))
    rows = c.fetchall(); _release(conn)
    return {"budgets": [{"id": r[0], "month": r[1], "amount": r[2]} for r in rows]}


@app.post("/api/budgets")
def set_budget(b: BudgetIn, user=Depends(_auth)):
    conn = _conn(); c = conn.cursor()
    try:
        c.execute("INSERT INTO budgets (user_id,month,amount) VALUES (?,?,?) ON CONFLICT(user_id,month) DO UPDATE SET amount=?",
                  (user["id"], b.month, b.amount, b.amount))
        conn.commit()
    except Exception:
        # Fallback for SQLite versions without UPSERT
        c.execute("SELECT id FROM budgets WHERE user_id=? AND month=?", (user["id"], b.month))
        existing = c.fetchone()
        if existing:
            c.execute("UPDATE budgets SET amount=? WHERE id=?", (b.amount, existing[0]))
        else:
            c.execute("INSERT INTO budgets (user_id,month,amount) VALUES (?,?,?)", (user["id"], b.month, b.amount))
        conn.commit()
    _release(conn)
    return {"message": "Budget saved"}


# ===================== ANALYTICS =====================

@app.get("/api/analytics/overview")
def analytics_overview(start_date: Optional[str] = None, end_date: Optional[str] = None, user=Depends(_auth)):
    conn = _conn(); c = conn.cursor(); uid = user["id"]
    w, p = _where(uid, start_date, end_date)

    c.execute(f"SELECT COUNT(*),COALESCE(SUM(amount),0),COALESCE(AVG(amount),0),COALESCE(MAX(amount),0),COALESCE(MIN(amount),0) FROM expenses {w}", p)
    r = c.fetchone()

    today = datetime.now().strftime("%Y-%m-%d")
    ms = datetime.now().replace(day=1).strftime("%Y-%m-%d")
    c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE user_id=? AND date>=? AND date<=?", (uid, ms, today))
    this_m = c.fetchone()[0]

    lme = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d")
    lms = (datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d")
    c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE user_id=? AND date>=? AND date<=?", (uid, lms, lme))
    last_m = c.fetchone()[0]

    # Budget for this month
    cm = datetime.now().strftime("%Y-%m")
    c.execute("SELECT amount FROM budgets WHERE user_id=? AND month=?", (uid, cm))
    brow = c.fetchone()
    budget = brow[0] if brow else 0

    _release(conn)
    days = max((datetime.now().date() - datetime.now().replace(day=1).date()).days, 1)

    return {
        "total_transactions": r[0], "total_amount": round(r[1], 2),
        "avg_amount": round(r[2], 2), "max_amount": r[3], "min_amount": r[4] if r[0] > 0 else 0,
        "daily_avg": round(this_m / days, 2), "this_month": this_m, "last_month": last_m,
        "month_change_pct": round(((this_m - last_m) / last_m * 100), 1) if last_m > 0 else 0,
        "budget": budget, "budget_used_pct": round(this_m / budget * 100, 1) if budget > 0 else 0,
        "projected": round((this_m / days) * 30, 2),
        "days_passed": days, "days_remaining": 30 - days
    }


@app.get("/api/analytics/category-summary")
def category_summary(start_date: Optional[str] = None, end_date: Optional[str] = None, user=Depends(_auth)):
    conn = _conn(); c = conn.cursor()
    w, p = _where(user["id"], start_date, end_date)
    c.execute(f"SELECT category,SUM(amount),COUNT(*),AVG(amount) FROM expenses {w} GROUP BY category ORDER BY SUM(amount) DESC", p)
    rows = c.fetchall(); _release(conn)
    total = sum(r[1] for r in rows) or 1
    return {"categories": [
        {"category": r[0], "total": round(r[1], 2), "count": r[2], "avg": round(r[3], 2), "pct": round(r[1]/total*100, 1)}
        for r in rows
    ]}


@app.get("/api/analytics/monthly")
def monthly_summary(user=Depends(_auth)):
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT strftime('%Y-%m',date),SUM(amount) FROM expenses WHERE user_id=? GROUP BY strftime('%Y-%m',date) ORDER BY strftime('%Y-%m',date) DESC LIMIT 12",
              (user["id"],))
    rows = c.fetchall(); _release(conn)
    return {"months": [{"month": r[0], "amount": round(r[1], 2)} for r in rows]}


@app.get("/api/analytics/daily")
def daily_trend(start_date: Optional[str] = None, end_date: Optional[str] = None, user=Depends(_auth)):
    conn = _conn(); c = conn.cursor()
    w, p = _where(user["id"], start_date, end_date)
    c.execute(f"SELECT date,SUM(amount),COUNT(*) FROM expenses {w} GROUP BY date ORDER BY date", p)
    rows = c.fetchall(); _release(conn)
    return {"days": [{"date": r[0], "amount": round(r[1], 2), "count": r[2]} for r in rows]}


@app.get("/api/analytics/weekly")
def weekly_pattern(user=Depends(_auth)):
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT strftime('%w',date),SUM(amount),COUNT(*),AVG(amount) FROM expenses WHERE user_id=? GROUP BY strftime('%w',date)",
              (user["id"],))
    rows = c.fetchall(); _release(conn)
    names = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']
    return {"days": [{"day": names[int(r[0])], "dow": int(r[0]), "total": round(r[1], 2), "count": r[2], "avg": round(r[3], 2)} for r in rows]}


@app.get("/api/analytics/top")
def top_expenses(limit: int = 10, start_date: Optional[str] = None, end_date: Optional[str] = None, user=Depends(_auth)):
    conn = _conn(); c = conn.cursor()
    w, p = _where(user["id"], start_date, end_date)
    c.execute(f"SELECT id,amount,purpose,category,date FROM expenses {w} ORDER BY amount DESC LIMIT ?", p + [limit])
    rows = c.fetchall(); _release(conn)
    return {"expenses": [{"id": r[0],"amount": r[1],"purpose": r[2],"category": r[3],"date": r[4]} for r in rows]}


@app.get("/api/analytics/category-trend")
def category_trend(user=Depends(_auth)):
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT strftime('%Y-%m',date),category,SUM(amount) FROM expenses WHERE user_id=? GROUP BY strftime('%Y-%m',date),category ORDER BY strftime('%Y-%m',date)",
              (user["id"],))
    rows = c.fetchall(); _release(conn)
    return {"data": [{"month": r[0], "category": r[1], "amount": round(r[2], 2)} for r in rows]}


@app.get("/api/analytics/heatmap")
def heatmap(user=Depends(_auth)):
    conn = _conn(); c = conn.cursor()
    start = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    c.execute("SELECT date,SUM(amount) FROM expenses WHERE user_id=? AND date>=? GROUP BY date ORDER BY date",
              (user["id"], start))
    rows = c.fetchall(); _release(conn)
    return {"data": [{"date": r[0], "amount": round(r[1], 2)} for r in rows]}


# ===================== AI =====================

@app.post("/api/ai/analyze")
def ai_analyze(req: AIReq, user=Depends(_auth)):
    conn = _conn(); c = conn.cursor(); uid = user["id"]
    start = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    c.execute("SELECT amount,purpose,category,date FROM expenses WHERE user_id=? AND date>=? ORDER BY date DESC",
              (uid, start))
    rows = c.fetchall()
    if not rows:
        _release(conn)
        return {"analysis": "Not enough data. Add some expenses first!"}

    total = sum(r[0] for r in rows)
    count = len(rows)
    cats = {}
    months = {}
    for r in rows:
        cats[r[2]] = cats.get(r[2], 0) + r[0]
        m = r[3][:7] if r[3] else "?"
        months[m] = months.get(m, 0) + r[0]

    cat_text = "\n".join(f"- {c}: ₹{a:,.0f} ({a/total*100:.0f}%)" for c, a in sorted(cats.items(), key=lambda x: -x[1]))
    month_text = "\n".join(f"- {m}: ₹{a:,.0f}" for m, a in sorted(months.items()))
    top5 = "\n".join(f"- {r[1]} ({r[2]}): ₹{r[0]:,.0f} on {r[3]}" for r in sorted(rows, key=lambda x: -x[0])[:5])

    summary = f"EXPENSES (90 days): Total ₹{total:,.0f} | {count} txns | Avg ₹{total/count:,.0f}\n\nCATEGORIES:\n{cat_text}\n\nMONTHLY:\n{month_text}\n\nTOP 5:\n{top5}"
    _release(conn)

    prompts = {
        "general": f"Analyze and give: 1) Overview 2) Category insights 3) Trends 4) Concerns 5) Tips.\n\n{summary}",
        "budget": f"Monthly budget: ₹{req.budget or 50000:,.0f}. Give: 1) Status 2) Projected spend 3) Allocation 4) Savings potential 5) Action plan.\n\n{summary}",
        "savings": f"Find savings: 1) Quick wins 2) Category cuts 3) Bad patterns 4) Goal 5) 30-day challenge.\n\n{summary}",
        "anomaly": f"Audit for: 1) Unusual txns 2) Outliers 3) Timing spikes 4) Trend breaks 5) Actions.\n\n{summary}",
    }

    try:
        client = AzureOpenAI(api_key=AZURE_API_KEY, azure_endpoint=AZURE_API_BASE, api_version=AZURE_API_VERSION)
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are a concise personal finance assistant. Use markdown. Be specific with numbers."},
                {"role": "user", "content": prompts.get(req.type, prompts["general"])}
            ],
            temperature=0.7, max_tokens=1500
        )
        return {"analysis": resp.choices[0].message.content}
    except Exception as e:
        return {"analysis": f"AI unavailable: {str(e)}"}


# ===================== USERS (admin) =====================

def _require_admin(user):
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin only")


@app.get("/api/users")
def list_users(user=Depends(_auth)):
    _require_admin(user)
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT u.id, u.username, u.full_name, u.created_at, u.is_admin, COUNT(e.id) as expense_count, COALESCE(SUM(e.amount),0) as total_spent FROM users u LEFT JOIN expenses e ON u.id = e.user_id GROUP BY u.id ORDER BY u.username")
    rows = c.fetchall(); _release(conn)
    return {"users": [{"id": r[0], "username": r[1], "full_name": r[2], "created_at": r[3], "is_admin": bool(r[4]), "expense_count": r[5], "total_spent": round(r[6], 2)} for r in rows]}


@app.delete("/api/users/{uid}")
def delete_user(uid: int, user=Depends(_auth)):
    _require_admin(user)
    if uid == user["id"]:
        raise HTTPException(400, "Cannot delete yourself")
    conn = _conn(); c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE user_id=?", (uid,))
    c.execute("DELETE FROM budgets WHERE user_id=?", (uid,))
    c.execute("DELETE FROM users WHERE id=?", (uid,))
    conn.commit(); _release(conn)
    return {"message": "User and their data deleted"}


@app.post("/api/users/reset-password")
def admin_reset_password(req: AdminResetPasswordReq, user=Depends(_auth)):
    _require_admin(user)
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT id FROM users WHERE id=?", (req.user_id,))
    if not c.fetchone():
        _release(conn); raise HTTPException(404, "User not found")
    c.execute("UPDATE users SET password_hash=? WHERE id=?", (_hash(req.new_password), req.user_id))
    conn.commit(); _release(conn)
    return {"message": "Password reset"}


# ===================== KEEP-ALIVE =====================

@app.get("/api/ping")
def ping_db():
    """Manual ping endpoint — can be called by external cron (e.g. cron-job.org) every hour."""
    try:
        conn = _conn(); c = conn.cursor()
        c.execute("SELECT 1")
        _release(conn)
        return {"status": "alive", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(500, f"DB ping failed: {str(e)}")


# ===================== STATIC FILES (local dev) =====================

# Mount static directories for local uvicorn serving
# On Vercel, these are served directly by the CDN
if (BASE_DIR / "css").exists():
    app.mount("/css", StaticFiles(directory=str(BASE_DIR / "css")), name="css")
if (BASE_DIR / "js").exists():
    app.mount("/js", StaticFiles(directory=str(BASE_DIR / "js")), name="js")


@app.get("/manifest.json")
def manifest():
    return FileResponse(str(BASE_DIR / "manifest.json"))


# SPA fallback — serve index.html for all non-API routes
@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    index = BASE_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    raise HTTPException(404, "Not found")
