import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os, json, uuid, re
from datetime import datetime

# ─── PAGE CONFIG ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Social Growth Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── THEME CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

/* ── Root variables ── */
:root {
  --bg:         #f0f2f5;
  --bg2:        #e8eaee;
  --surface:    rgba(255,255,255,0.82);
  --surface2:   rgba(255,255,255,0.55);
  --border:     rgba(255,255,255,0.95);
  --border2:    rgba(180,185,200,0.35);
  --text:       #1a1d2e;
  --text2:      #5a6070;
  --cyan:       #00c8d4;
  --violet:     #7c5cfc;
  --lime:       #74e27a;
  --pink:       #f06090;
  --amber:      #f5a623;
  --grid:       rgba(160,170,190,0.18);
}

/* ── Reset & base ── */
html, body, [data-testid="stApp"] {
  font-family: 'DM Sans', sans-serif;
  background: var(--bg) !important;
  color: var(--text) !important;
}

/* ── Subtle grid background ── */
[data-testid="stApp"]::before {
  content: '';
  position: fixed; inset: 0; z-index: 0;
  background-image:
    linear-gradient(var(--grid) 1px, transparent 1px),
    linear-gradient(90deg, var(--grid) 1px, transparent 1px);
  background-size: 36px 36px;
  pointer-events: none;
}

/* ── Main content area ── */
.main .block-container {
  padding: 2rem 2.5rem 3rem;
  max-width: 1440px;
  position: relative; z-index: 1;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: rgba(255,255,255,0.92) !important;
  backdrop-filter: blur(20px);
  border-right: 1px solid var(--border2) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }
[data-testid="stSidebar"] .stRadio label {
  font-size: 0.88rem;
  font-weight: 500;
  padding: 6px 10px;
  border-radius: 8px;
  transition: background 0.15s;
}
[data-testid="stSidebar"] .stRadio label:hover { background: rgba(0,200,212,0.08); }

/* ── Typography ── */
h1 { font-family: 'Space Grotesk', sans-serif; font-size: 1.8rem !important; font-weight: 700 !important; letter-spacing: -0.03em; color: var(--text) !important; margin-bottom: 0.25rem !important; }
h2 { font-family: 'Space Grotesk', sans-serif; font-size: 1.15rem !important; font-weight: 600 !important; letter-spacing: -0.02em; }
h3 { font-family: 'Space Grotesk', sans-serif; font-size: 0.95rem !important; font-weight: 600 !important; }
p, li { font-size: 0.9rem; line-height: 1.6; }

/* ── KPI Cards ── */
.kpi-card {
  background: var(--surface);
  backdrop-filter: blur(24px);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 20px 22px;
  box-shadow: 0 2px 12px rgba(100,110,140,0.10), 0 1px 3px rgba(100,110,140,0.06);
  position: relative;
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
}
.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 28px rgba(100,110,140,0.16);
}
.kpi-card::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: var(--accent-color, linear-gradient(90deg, var(--cyan), var(--violet)));
  border-radius: 20px 20px 0 0;
}
.kpi-icon { font-size: 1.5rem; margin-bottom: 8px; }
.kpi-value {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 2rem; font-weight: 700; letter-spacing: -0.04em;
  color: var(--text); line-height: 1;
}
.kpi-label { font-size: 0.78rem; font-weight: 500; color: var(--text2); text-transform: uppercase; letter-spacing: 0.08em; margin-top: 4px; }
.kpi-delta { font-size: 0.82rem; font-weight: 500; margin-top: 6px; }
.kpi-delta.up { color: #22c55e; }
.kpi-delta.down { color: #ef4444; }
.kpi-delta.neutral { color: var(--text2); }

/* ── Glass panels ── */
.glass-panel {
  background: var(--surface);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(100,110,140,0.08);
  margin-bottom: 1rem;
}

/* ── Section header ── */
.section-header {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 16px;
}
.section-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--cyan);
  box-shadow: 0 0 8px var(--cyan);
}

/* ── Action insight box ── */
.insight-box {
  background: linear-gradient(135deg, rgba(0,200,212,0.08), rgba(124,92,252,0.08));
  border: 1px solid rgba(0,200,212,0.25);
  border-radius: 16px;
  padding: 16px 20px;
  margin-top: 8px;
}
.insight-box p { margin: 4px 0; font-size: 0.88rem; color: var(--text2); }
.insight-box .insight-item::before { content: '→ '; color: var(--cyan); font-weight: 700; }

/* ── Pill badges ── */
.badge {
  display: inline-block;
  padding: 3px 10px; border-radius: 999px;
  font-size: 0.75rem; font-weight: 600;
  letter-spacing: 0.04em;
}
.badge-cyan  { background: rgba(0,200,212,0.12); color: #0099a8; }
.badge-violet{ background: rgba(124,92,252,0.12); color: #5a3fd4; }
.badge-lime  { background: rgba(116,226,122,0.15); color: #3a9940; }

/* ── Top header bar ── */
.top-bar {
  background: var(--surface);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 16px 24px;
  margin-bottom: 24px;
  display: flex; align-items: center; justify-content: space-between;
  box-shadow: 0 2px 12px rgba(100,110,140,0.08);
}
.top-bar-title { font-family: 'Space Grotesk', sans-serif; font-size: 1.1rem; font-weight: 700; }
.top-bar-sub { font-size: 0.8rem; color: var(--text2); margin-top: 2px; }

/* ── Streamlit widget cleanup ── */
[data-testid="metric-container"] { display: none; }
.stExpander { border-radius: 16px !important; border: 1px solid var(--border2) !important; }
.stSelectbox > div, .stNumberInput > div input, .stTextArea textarea {
  background: var(--surface2) !important;
  border-color: var(--border2) !important;
  border-radius: 10px !important;
  color: var(--text) !important;
}
div[data-testid="stFileUploader"] {
  background: var(--surface2);
  border: 1.5px dashed var(--border2);
  border-radius: 14px;
  padding: 12px;
}
.stButton > button {
  background: linear-gradient(135deg, var(--cyan), var(--violet)) !important;
  color: white !important; border: none !important;
  border-radius: 10px !important; font-weight: 600 !important;
  transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }
.stDataFrame { border-radius: 12px; overflow: hidden; }
.stAlert { border-radius: 12px !important; }
hr { border-color: var(--border2) !important; }
</style>
""", unsafe_allow_html=True)

# ─── STORAGE SETUP ───────────────────────────────────────────────────────────
BASE_DIR   = "storage"
EXPORT_DIR = os.path.join(BASE_DIR, "exports")
VIDEO_DIR  = os.path.join(BASE_DIR, "videos")
SS_DIR     = os.path.join(BASE_DIR, "screenshots")
for d in [BASE_DIR, EXPORT_DIR, VIDEO_DIR, SS_DIR]:
    os.makedirs(d, exist_ok=True)

PERIODS = ["7", "28", "60", "365"]
EXPORT_TYPES = [
    ("overview",                 "Overview"),
    ("content",                  "Content"),
    ("viewers",                  "Viewers"),
    ("follower_history",         "Follower History"),
    ("follower_activity",        "Follower Activity"),
    ("follower_gender",          "Follower Gender"),
    ("follower_top_territories", "Follower Top Territories"),
]
EXPORT_TYPE_LABEL = dict(EXPORT_TYPES)

# ─── PLOTLY THEME ────────────────────────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    font_family="DM Sans",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#1a1d2e",
    margin=dict(l=16, r=16, t=40, b=16),
    colorway=["#00c8d4","#7c5cfc","#74e27a","#f06090","#f5a623","#38bdf8"],
)

def apply_theme(fig):
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_xaxes(gridcolor="rgba(160,170,190,0.18)", linecolor="rgba(160,170,190,0.3)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(160,170,190,0.18)", linecolor="rgba(160,170,190,0.3)", zeroline=False)
    return fig

# ─── DATA HELPERS ────────────────────────────────────────────────────────────
def export_path(period: str, export_type: str) -> str:
    pdir = os.path.join(EXPORT_DIR, period)
    os.makedirs(pdir, exist_ok=True)
    return os.path.join(pdir, f"{export_type}.csv")

def read_csv_safe(path: str):
    if not os.path.exists(path): return None
    try:
        return pd.read_csv(path)
    except Exception as e:
        st.error(f"CSV okunamadı: {path} — {e}")
        return None

def make_unique_columns(df: pd.DataFrame) -> pd.DataFrame:
    seen = {}; new_cols = []
    for c in df.columns:
        base = str(c)
        if base not in seen:
            seen[base] = 0; new_cols.append(base)
        else:
            seen[base] += 1; new_cols.append(f"{base}__{seen[base]}")
    df.columns = new_cols
    return df

def norm_cols(df: pd.DataFrame) -> dict:
    return {c.lower().strip(): c for c in df.columns}

def find_col(df: pd.DataFrame, candidates: list) -> str | None:
    cols = norm_cols(df)
    for c in candidates:
        if c.lower().strip() in cols: return cols[c.lower().strip()]
    return None

def clean_numeric(series: pd.Series) -> pd.Series:
    """Convert strings like '12%', '1,234', '0,12' to float."""
    def _clean(v):
        if pd.isna(v): return None
        s = str(v).strip().replace("%","").replace(" ","")
        s = s.replace(",",".")
        try: return float(s)
        except: return None
    return pd.to_numeric(series.apply(_clean), errors="coerce")

def sum_num(df: pd.DataFrame, colname: str | None) -> float:
    if not colname or colname not in df.columns: return 0.0
    s = clean_numeric(df[colname]).fillna(0)
    s[s < 0] = 0
    return float(s.sum())

def safe_float(x, default=0.0) -> float:
    try:
        return float(pd.to_numeric(pd.Series([x]), errors="coerce").fillna(default).iloc[0])
    except:
        return float(default)

def fmt_int(x) -> str:
    try: return f"{int(float(x)):,}".replace(",", ".")
    except: return "0"

def fmt_pct(x, decimals=2) -> str:
    try: return f"{float(x)*100:.{decimals}f}%"
    except: return "—"

# ─── EXPORT TYPE GUESSER ─────────────────────────────────────────────────────
def guess_export_type(df: pd.DataFrame, filename: str) -> str | None:
    name = filename.lower()
    cols = {c.lower().strip() for c in df.columns}
    if "overview"  in name: return "overview"
    if "content"   in name: return "content"
    if "viewer"    in name: return "viewers"
    if "gender"    in name: return "follower_gender"
    if "territor"  in name: return "follower_top_territories"
    if "activity"  in name: return "follower_activity"
    if "history"   in name: return "follower_history"
    if {"video views","profile views"} & cols: return "overview"
    if {"title","video views"} & cols:         return "content"
    if ("viewers" in cols) or ("total viewers" in cols): return "viewers"
    if ({"female","male"} & cols) or ("gender" in cols): return "follower_gender"
    if ("territory" in cols) or ("country" in cols):     return "follower_top_territories"
    if "hour" in cols or "day" in cols:                  return "follower_activity"
    if "followers" in cols and ("date" in cols or "day" in cols): return "follower_history"
    return None

# ─── CONTENT PARSING ─────────────────────────────────────────────────────────
def list_videos_from_content(period: str) -> pd.DataFrame:
    df = read_csv_safe(export_path(period, "content"))
    if df is None or df.empty: return pd.DataFrame()
    cols = norm_cols(df)

    def gc(*keys):
        for k in keys:
            if k in cols: return cols[k]
        return None

    title_col   = gc("title","video title","content") or list(df.columns)[0]
    date_col    = gc("date","publish date","create time")
    views_col   = gc("video views","views")
    likes_col   = gc("likes")
    comments_col= gc("comments")
    shares_col  = gc("shares")

    out = pd.DataFrame()
    out["title"]    = df[title_col].astype(str)
    out["date"]     = df[date_col].astype(str) if date_col else ""
    out["views"]    = clean_numeric(df[views_col])   if views_col    else pd.NA
    out["likes"]    = clean_numeric(df[likes_col])   if likes_col    else pd.NA
    out["comments"] = clean_numeric(df[comments_col]).fillna(0).clip(lower=0) if comments_col else 0
    out["shares"]   = clean_numeric(df[shares_col])  if shares_col   else pd.NA

    denom = out["views"].replace({0: pd.NA})
    eng   = out[["likes","comments","shares"]].fillna(0).sum(axis=1)
    out["er"]            = (eng / denom).fillna(0)
    out["shares_per_1k"] = ((out["shares"].fillna(0) / denom) * 1000).fillna(0)
    out["video_id"] = out.apply(
        lambda r: str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{r['title']}|{r['date']}")), axis=1
    )
    return out

# ─── VIDEO STATE ─────────────────────────────────────────────────────────────
def video_json_path(vid): return os.path.join(VIDEO_DIR, f"{vid}.json")

def load_video_state(vid: str) -> dict:
    p = video_json_path(vid)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f: return json.load(f)
    return {"video_id":vid,"notes":"","duration_sec":None,"avg_watch_sec":None,
            "completion_pct":None,"followers_gained":None,"last_updated":None}

def save_video_state(vid: str, state: dict):
    state["last_updated"] = datetime.utcnow().isoformat()
    with open(video_json_path(vid), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def save_screenshots(vid: str, files):
    vdir = os.path.join(SS_DIR, vid); os.makedirs(vdir, exist_ok=True)
    saved = []
    for f in files:
        fname = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{f.name}"
        path = os.path.join(vdir, fname)
        with open(path, "wb") as out: out.write(f.getbuffer())
        saved.append(path)
    return saved

def list_screenshots(vid: str):
    vdir = os.path.join(SS_DIR, vid)
    if not os.path.exists(vdir): return []
    return sorted([os.path.join(vdir, x) for x in os.listdir(vdir)])

# ─── SCORING ─────────────────────────────────────────────────────────────────
def compute_growth_score(row, vstate: dict) -> dict:
    views         = safe_float(row.get("views"), 0)
    shares_per_1k = safe_float(row.get("shares_per_1k"), 0)
    duration      = vstate.get("duration_sec")
    avg_watch     = vstate.get("avg_watch_sec")
    completion    = vstate.get("completion_pct")
    followers_gained = vstate.get("followers_gained")

    retention = None
    if duration and avg_watch and float(duration) > 0:
        retention = max(0.0, min(1.0, float(avg_watch) / float(duration)))

    follow_per_1k = None
    if followers_gained is not None and views > 0:
        follow_per_1k = (float(followers_gained) / views) * 1000.0

    score = (
        (retention or 0.0) * 50 +
        ((float(completion)/100.0) if completion else 0.0) * 25 +
        (shares_per_1k / 10.0) * 15 +
        ((follow_per_1k or 0.0) / 10.0) * 10
    )
    return {"retention": retention, "follow_per_1k": follow_per_1k, "score": score}

# ─── KPI CARD BUILDER ────────────────────────────────────────────────────────
def kpi_card(icon, value, label, accent="#00c8d4", delta=None, delta_type="neutral"):
    delta_html = ""
    if delta is not None:
        arrow = "↑" if delta_type == "up" else ("↓" if delta_type == "down" else "·")
        delta_html = f'<div class="kpi-delta {delta_type}">{arrow} {delta}</div>'
    st.markdown(f"""
    <div class="kpi-card" style="--accent-color: linear-gradient(90deg, {accent}, {accent}88);">
      <div class="kpi-icon">{icon}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-label">{label}</div>
      {delta_html}
    </div>""", unsafe_allow_html=True)

def section_header(title, dot_color="#00c8d4"):
    st.markdown(f"""
    <div class="section-header">
      <div class="section-dot" style="background:{dot_color};box-shadow:0 0 8px {dot_color};"></div>
      <h2 style="margin:0;">{title}</h2>
    </div>""", unsafe_allow_html=True)

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:12px 0 20px;">
      <div style="font-family:'Space Grotesk',sans-serif;font-size:1.1rem;font-weight:700;color:#1a1d2e;">
        ◎ Social Growth
      </div>
      <div style="font-size:0.75rem;color:#5a6070;margin-top:2px;">Analytics Dashboard</div>
    </div>""", unsafe_allow_html=True)

    period = st.radio("Dönem (gün)", PERIODS, horizontal=True)
    st.markdown("<hr style='margin:12px 0;'>", unsafe_allow_html=True)
    page = st.radio(
        "Sayfa",
        ["Genel Bakış", "Growth Cockpit", "İçerik", "İzleyiciler", "Takipçiler", "Ayarlar"],
    )
    st.markdown("<hr style='margin:12px 0;'>", unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.75rem;color:#5a6070;">Spor · Eğlence · Bilgi</div>', unsafe_allow_html=True)

# ─── TOP BAR ─────────────────────────────────────────────────────────────────
now_str = datetime.now().strftime("%d %b %Y, %H:%M")
st.markdown(f"""
<div class="top-bar">
  <div>
    <div class="top-bar-title">{page}</div>
    <div class="top-bar-sub">Son {period} gün · {now_str}</div>
  </div>
  <div style="display:flex;gap:8px;align-items:center;">
    <span class="badge badge-cyan">TikTok</span>
    <span class="badge badge-violet">Dönem: {period}g</span>
  </div>
</div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGES
# ═══════════════════════════════════════════════════════════════════════════════

# ── SETTINGS ──────────────────────────────────────────────────────────────────
def page_settings():
    st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
    section_header("Veri Yükleme")
    st.markdown("CSV export dosyalarını **toplu** yükle — sistem dosya türünü otomatik algılar.", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    period_sel = st.radio("Yükleme dönemi", PERIODS, horizontal=True,
                          index=PERIODS.index(period) if period in PERIODS else 0)
    mode = st.radio("Mod", ["Toplu (önerilen)", "Tekli"], horizontal=True)
    st.markdown("---")

    if mode == "Toplu (önerilen)":
        ups = st.file_uploader("CSV dosyaları seç", type=["csv"], accept_multiple_files=True)
        if ups:
            results = []
            for up in ups:
                try: df = pd.read_csv(up)
                except Exception as e:
                    results.append({"dosya": up.name, "durum": f"OKUNAMADI: {e}", "tür": None}); continue
                guessed = guess_export_type(df, up.name)
                etype = guessed
                if etype is None:
                    etype = st.selectbox(f"Tür: {up.name}", [x[0] for x in EXPORT_TYPES],
                                         format_func=lambda t: EXPORT_TYPE_LABEL.get(t, t),
                                         key=f"type_{up.name}")
                path = export_path(period_sel, etype)
                try:
                    up.seek(0)
                    with open(path, "wb") as f: f.write(up.getbuffer())
                    results.append({"dosya": up.name, "durum": "✓ Yüklendi", "tür": etype})
                except Exception as e:
                    results.append({"dosya": up.name, "durum": f"HATA: {e}", "tür": etype})
            st.success("İşlem tamamlandı.")
            st.dataframe(make_unique_columns(pd.DataFrame(results)), use_container_width=True, hide_index=True)
    else:
        c1, c2 = st.columns([1,2])
        with c1:
            etype = st.selectbox("Export türü", [x[0] for x in EXPORT_TYPES],
                                  format_func=lambda t: EXPORT_TYPE_LABEL.get(t,t))
            up = st.file_uploader("CSV yükle", type=["csv"], key="single_upload")
            if up:
                path = export_path(period_sel, etype)
                with open(path,"wb") as f: f.write(up.getbuffer())
                st.success(f"Yüklendi → {path}")
        with c2:
            section_header("Yüklü Dosyalar", "#7c5cfc")
            rows = [{"Dönem":p,"Tür":et,"Var mı":"✓" if os.path.exists(export_path(p,et)) else "—","Yol":export_path(p,et)}
                    for p in PERIODS for et,_ in EXPORT_TYPES]
            st.dataframe(make_unique_columns(pd.DataFrame(rows)), use_container_width=True, hide_index=True)


# ── OVERVIEW ──────────────────────────────────────────────────────────────────
def page_overview():
    df = read_csv_safe(export_path(period, "overview"))
    if df is None or df.empty:
        st.info("Bu dönem için Overview verisi yok. → Ayarlar'dan yükle.")
        return

    views_col    = find_col(df, ["video views","views","total video views"])
    profile_col  = find_col(df, ["profile views","profile visits","profile view"])
    likes_col    = find_col(df, ["likes","total likes"])
    comments_col = find_col(df, ["comments","total comments"])
    shares_col   = find_col(df, ["shares","total shares"])
    date_col     = find_col(df, ["date","day","tarih","created_at"])

    total_views    = sum_num(df, views_col)
    total_profile  = sum_num(df, profile_col)
    total_likes    = sum_num(df, likes_col)
    total_comments = sum_num(df, comments_col)
    total_shares   = sum_num(df, shares_col)

    profile_ctr = (total_profile / total_views) if total_views else 0
    er = ((total_likes + total_comments + total_shares) / total_views) if total_views else 0
    shares_1k = (total_shares / total_views * 1000) if total_views else 0

    # KPI Cards
    section_header("Temel Metrikler")
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: kpi_card("👁️", fmt_int(total_views), "Toplam İzlenme", "#00c8d4")
    with c2: kpi_card("👤", fmt_int(total_profile), "Profil Ziyareti", "#7c5cfc")
    with c3: kpi_card("🔗", f"{profile_ctr*100:.2f}%", "Profil CTR", "#f06090")
    with c4: kpi_card("⚡", f"{er*100:.2f}%", "Etkileşim Oranı", "#74e27a")
    with c5: kpi_card("🔁", f"{shares_1k:.2f}", "Paylaşım / 1K", "#f5a623")

    st.markdown("<br>", unsafe_allow_html=True)

    # Time-series chart
    if date_col:
        try:
            ts = df.copy()
            ts["_date"] = pd.to_datetime(ts[date_col], errors="coerce")
            ts = ts.dropna(subset=["_date"]).sort_values("_date")

            numeric_cols = []
            for col_candidates, label in [
                ([views_col], "İzlenme"),
                ([likes_col], "Beğeni"),
                ([shares_col], "Paylaşım"),
            ]:
                cc = col_candidates[0]
                if cc:
                    ts[label] = clean_numeric(ts[cc]).fillna(0)
                    numeric_cols.append(label)

            if numeric_cols:
                section_header("Zaman Serisi", "#7c5cfc")
                col_l, col_r = st.columns([3,1])
                with col_l:
                    fig = go.Figure()
                    colors = ["#00c8d4","#7c5cfc","#74e27a","#f06090"]
                    for i, nc in enumerate(numeric_cols):
                        fig.add_trace(go.Scatter(
                            x=ts["_date"], y=ts[nc], name=nc, mode="lines+markers",
                            line=dict(color=colors[i%len(colors)], width=2.5),
                            marker=dict(size=5),
                            fill="tozeroy" if i==0 else "none",
                            fillcolor=f"rgba({','.join(str(int(colors[i%len(colors)].lstrip('#')[j*2:(j+1)*2],16)) for j in range(3))},0.07)" if i==0 else None,
                            hovertemplate=f"<b>{nc}</b>: %{{y:,.0f}}<extra></extra>"
                        ))
                    apply_theme(fig)
                    fig.update_layout(height=300, legend=dict(orientation="h",y=1.12))
                    st.plotly_chart(fig, use_container_width=True)
                with col_r:
                    st.markdown("""
                    <div class="insight-box">
                      <div style="font-size:0.78rem;font-weight:700;color:#1a1d2e;margin-bottom:8px;">📊 Dönem Özeti</div>
                    """, unsafe_allow_html=True)
                    st.markdown(f'<p class="insight-item">İzlenme: <strong>{fmt_int(total_views)}</strong></p>', unsafe_allow_html=True)
                    st.markdown(f'<p class="insight-item">ER: <strong>{er*100:.2f}%</strong></p>', unsafe_allow_html=True)
                    st.markdown(f'<p class="insight-item">CTR: <strong>{profile_ctr*100:.2f}%</strong></p>', unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"Zaman serisi oluşturulamadı: {e}")

    st.markdown("<br>", unsafe_allow_html=True)

    # Engagement breakdown donut
    if any([total_likes, total_comments, total_shares]):
        section_header("Etkileşim Dağılımı", "#74e27a")
        c1, c2 = st.columns(2)
        with c1:
            fig = go.Figure(go.Pie(
                labels=["Beğeni","Yorum","Paylaşım"],
                values=[total_likes, total_comments, total_shares],
                hole=0.62,
                marker=dict(colors=["#00c8d4","#7c5cfc","#74e27a"],
                            line=dict(color="white", width=3)),
                textfont_size=13,
                hovertemplate="<b>%{label}</b>: %{value:,.0f}<extra></extra>",
            ))
            fig.update_layout(
                **PLOTLY_LAYOUT, height=280,
                annotations=[dict(text=f"<b>{fmt_int(total_likes+total_comments+total_shares)}</b><br><span style='font-size:11px'>toplam</span>",
                                  showarrow=False, font_size=16)],
                showlegend=True,
                legend=dict(orientation="h", y=-0.05),
            )
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown("""
            <div class="glass-panel" style="height:280px;display:flex;flex-direction:column;justify-content:center;">
            """, unsafe_allow_html=True)
            for icon, label, val in [
                ("👍","Beğeni", fmt_int(total_likes)),
                ("💬","Yorum",  fmt_int(total_comments)),
                ("🔁","Paylaşım", fmt_int(total_shares)),
            ]:
                st.markdown(f"""
                <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid rgba(180,185,200,0.2);">
                  <span style="font-size:0.88rem;color:#5a6070;">{icon} {label}</span>
                  <span style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:1.1rem;">{val}</span>
                </div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Ham Veri (Opsiyonel)", expanded=False):
        st.dataframe(make_unique_columns(df.copy()), use_container_width=True, hide_index=True)


# ── GROWTH COCKPIT ────────────────────────────────────────────────────────────
def page_growth_cockpit():
    st.markdown('<p style="color:#5a6070;font-size:0.88rem;margin-top:-12px;margin-bottom:20px;">Sadece büyüten metrikler. Diğer her şey gürültü.</p>', unsafe_allow_html=True)

    o = read_csv_safe(export_path(period, "overview"))
    c = list_videos_from_content(period)
    if o is None or o.empty:
        st.info("Overview verisi yok. → Ayarlar'dan yükle.")
        return

    views_col    = find_col(o, ["video views","views","total video views"])
    profile_col  = find_col(o, ["profile views","profile visits","profile view"])
    likes_col    = find_col(o, ["likes","total likes"])
    comments_col = find_col(o, ["comments","total comments"])
    shares_col   = find_col(o, ["shares","total shares"])

    total_views    = sum_num(o, views_col)
    total_profile  = sum_num(o, profile_col)
    total_likes    = sum_num(o, likes_col)
    total_comments = sum_num(o, comments_col)
    total_shares   = sum_num(o, shares_col)

    profile_ctr  = (total_profile / total_views) if total_views else 0
    er_total     = ((total_likes + total_comments + total_shares) / total_views) if total_views else 0
    shares_per_1k= (total_shares / total_views * 1000) if total_views else 0

    follow_per_1k_list = []; completion_list = []
    if not c.empty:
        for _, row in c.iterrows():
            vs = load_video_state(row["video_id"])
            views_v = safe_float(row.get("views"), 0)
            if vs.get("followers_gained") and views_v > 0:
                follow_per_1k_list.append((float(vs["followers_gained"]) / views_v) * 1000)
            if vs.get("completion_pct") is not None:
                completion_list.append(float(vs["completion_pct"]))

    avg_fol_1k  = sum(follow_per_1k_list)/len(follow_per_1k_list) if follow_per_1k_list else None
    avg_comp    = sum(completion_list)/len(completion_list)        if completion_list    else None

    section_header("Growth Sinyalleri")
    cols = st.columns(6)
    with cols[0]: kpi_card("👁️", fmt_int(total_views), "İzlenme", "#00c8d4")
    with cols[1]: kpi_card("🔗", f"{profile_ctr*100:.2f}%", "Profil CTR", "#7c5cfc")
    with cols[2]: kpi_card("⚡", f"{er_total*100:.2f}%", "Etkileşim", "#74e27a")
    with cols[3]: kpi_card("🔁", f"{shares_per_1k:.2f}", "Paylaşım / 1K", "#f06090")
    with cols[4]: kpi_card("👥", "—" if avg_fol_1k is None else f"{avg_fol_1k:.2f}", "Takip / 1K", "#f5a623")
    with cols[5]: kpi_card("⏱️", "—" if avg_comp is None else f"{avg_comp:.1f}%", "Completion", "#38bdf8")

    st.markdown("<br>", unsafe_allow_html=True)

    # Score gauge chart
    if not c.empty:
        section_header("İçerik Skoru Dağılımı", "#f06090")
        scores_list = []
        for _, row in c.iterrows():
            vs  = load_video_state(row["video_id"])
            res = compute_growth_score(row, vs)
            scores_list.append({
                "title": str(row["title"])[:40],
                "score": safe_float(res.get("score"), 0),
                "views": safe_float(row.get("views"), 0),
            })
        sc_df = pd.DataFrame(scores_list).sort_values("score", ascending=False).head(15)

        fig = go.Figure(go.Bar(
            x=sc_df["score"], y=sc_df["title"],
            orientation="h",
            marker=dict(
                color=sc_df["score"],
                colorscale=[[0,"#e8eaee"],[0.5,"#00c8d4"],[1,"#7c5cfc"]],
                showscale=False,
                line=dict(width=0),
            ),
            hovertemplate="<b>%{y}</b><br>Skor: %{x:.1f}<extra></extra>",
        ))
        apply_theme(fig)
        fig.update_layout(height=400, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    section_header("Aksiyon Önerileri", "#f5a623")
    actions = []
    if profile_ctr < 0.007:
        actions.append("Profile CTR düşük → bio + sabitlenmiş video + net CTA gerekli.")
    if shares_per_1k < 3:
        actions.append("Paylaşım zayıf → içeriği 'kaydet/paylaş' formatına çevir, daha kısa + net yap.")
    if avg_comp is not None and avg_comp < 25:
        actions.append("Completion düşük → ilk 2 saniye hook'u sertleştir, video süresini kısalt.")
    if not actions:
        actions.append("Sinyaller iyi → en iyi 3 videonun formatını çoğalt, 3 hook varyasyonu test et.")

    st.markdown('<div class="insight-box">', unsafe_allow_html=True)
    for a in actions:
        st.markdown(f'<p class="insight-item">{a}</p>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ── CONTENT ───────────────────────────────────────────────────────────────────
def page_video_detail(vid: str, parent_df: pd.DataFrame):
    state = load_video_state(vid)
    shots = list_screenshots(vid)
    if shots:
        with st.expander("Ekran Görüntüleri", expanded=False):
            for p in shots[-8:]: st.image(p, use_container_width=True)

    st.markdown("---")
    section_header("Retention / Conversion Metrikleri", "#f5a623")
    c1,c2,c3,c4 = st.columns(4)
    with c1: state["duration_sec"]      = st.number_input("Video süresi (sn)", value=state["duration_sec"] or 0, min_value=0, step=1, key=f"dur_{vid}")
    with c2: state["avg_watch_sec"]     = st.number_input("Avg watch (sn)",    value=state["avg_watch_sec"] or 0.0, min_value=0.0, step=0.1, key=f"avg_{vid}")
    with c3: state["completion_pct"]    = st.number_input("Completion %",      value=state["completion_pct"] or 0.0, min_value=0.0, max_value=100.0, step=0.1, key=f"comp_{vid}")
    with c4: state["followers_gained"]  = st.number_input("Followers gained",  value=state["followers_gained"] or 0, min_value=0, step=1, key=f"fol_{vid}")
    state["notes"] = st.text_area("Notlar", value=state.get("notes",""), height=100, key=f"notes_{vid}")
    if st.button("💾 Kaydet", key=f"save_{vid}"):
        for k in ["duration_sec","avg_watch_sec","completion_pct","followers_gained"]:
            if state[k] == 0 or state[k] == 0.0: state[k] = None
        save_video_state(vid, state)
        st.success("Kaydedildi.")

    row_df = parent_df[parent_df["video_id"]==vid]
    if row_df.empty: return
    row = row_df.iloc[0].to_dict()
    res = compute_growth_score(row, state)

    st.markdown("---")
    section_header("Otomatik Teşhis", "#f06090")
    a,b,c_ = st.columns(3)
    with a: kpi_card("🏆", f"{safe_float(res.get('score')):.1f}", "Score", "#7c5cfc")
    with b: kpi_card("📼", "—" if res.get("retention") is None else f"{safe_float(res.get('retention'))*100:.1f}%", "Retention", "#00c8d4")
    with c_: kpi_card("👥", "—" if res.get("follow_per_1k") is None else f"{safe_float(res.get('follow_per_1k')):.2f}", "Follow / 1K", "#74e27a")

    verdicts = []
    if res.get("retention") is not None and safe_float(res.get("retention")) < 0.35:
        verdicts.append("Hook/tempo tırt: izleyici videoda kalmıyor. İlk 2 saniyeyi sertleştir.")
    if state.get("completion_pct") and safe_float(state.get("completion_pct")) < 20:
        verdicts.append("Completion düşük: video gereksiz uzuyor veya payoff geç geliyor.")
    if safe_float(row.get("shares_per_1k",0)) < 3:
        verdicts.append("Paylaşım zayıf: 'kopyala-yapıştır değer' şeklinde paketle.")
    if not verdicts:
        verdicts.append("Sinyaller iyi: aynı formatı 3 hook varyasyonuyla tekrar dene.")

    st.markdown('<div class="insight-box">', unsafe_allow_html=True)
    for v in verdicts:
        st.markdown(f'<p class="insight-item">{v}</p>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def page_content():
    df = list_videos_from_content(period)
    if df.empty:
        st.info("Bu dönem için Content verisi yok. → Ayarlar'dan yükle.")
        return

    scores = [compute_growth_score(row, load_video_state(row["video_id"])) for _, row in df.iterrows()]
    s  = make_unique_columns(pd.DataFrame(scores))
    df2 = make_unique_columns(pd.concat([df.reset_index(drop=True), s.reset_index(drop=True)], axis=1))

    with st.expander("Filtreler", expanded=False):
        c1,c2,c3 = st.columns(3)
        with c1: min_views = st.number_input("Min İzlenme", value=0)
        with c2: sort_by   = st.selectbox("Sırala", ["score","views","er","shares_per_1k"])
        with c3: top_n     = st.slider("Grafik video sayısı", 5, 50, 15)

    for col in ["views","er","shares_per_1k","score"]:
        df2[col] = clean_numeric(df2[col]).fillna(0)

    df2 = df2[df2["views"] >= min_views].sort_values(sort_by, ascending=False)

    # KPI Cards
    section_header("İçerik Metrikleri")
    k1,k2,k3,k4 = st.columns(4)
    with k1: kpi_card("🎬", str(len(df2)), "Video Sayısı", "#00c8d4")
    with k2: kpi_card("👁️", fmt_int(df2["views"].sum()), "Toplam İzlenme", "#7c5cfc")
    with k3: kpi_card("⚡", f"{df2['er'].mean()*100:.2f}%", "Ort. ER", "#74e27a")
    with k4: kpi_card("🔁", f"{df2['shares_per_1k'].mean():.2f}", "Ort. Paylaşım/1K", "#f06090")

    st.markdown("<br>", unsafe_allow_html=True)
    top = df2.head(top_n).copy()
    top["title_short"] = top["title"].astype(str).str.slice(0, 40)

    # Charts row 1
    section_header("En İyi İçerikler", "#7c5cfc")
    cA, cB = st.columns(2)
    with cA:
        fig = go.Figure(go.Bar(
            x=top["views"], y=top["title_short"], orientation="h",
            marker=dict(color="#00c8d4", line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>İzlenme: %{x:,.0f}<extra></extra>",
        ))
        apply_theme(fig); fig.update_layout(height=380, title="En Çok İzlenenler", yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)
    with cB:
        fig = go.Figure(go.Bar(
            x=top["shares_per_1k"], y=top["title_short"], orientation="h",
            marker=dict(color="#7c5cfc", line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>Paylaşım/1K: %{x:.2f}<extra></extra>",
        ))
        apply_theme(fig); fig.update_layout(height=380, title="En Çok Paylaşılanlar (1K başına)", yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    # Charts row 2
    section_header("Performans Analizi", "#74e27a")
    cC, cD = st.columns(2)
    with cC:
        bins = pd.cut(df2["er"].clip(upper=0.2), bins=8)
        hist_df = bins.value_counts().sort_index().reset_index()
        hist_df.columns = ["ER Bandı","Sayı"]
        hist_df["ER Bandı"] = hist_df["ER Bandı"].astype(str)
        fig = go.Figure(go.Bar(
            x=hist_df["ER Bandı"], y=hist_df["Sayı"],
            marker=dict(color="#74e27a", line=dict(width=0)),
        ))
        apply_theme(fig); fig.update_layout(height=300, title="ER Dağılımı")
        st.plotly_chart(fig, use_container_width=True)
    with cD:
        fig = go.Figure(go.Scatter(
            x=df2["views"], y=df2["score"],
            mode="markers",
            marker=dict(color=df2["er"], colorscale="Teal", size=9, opacity=0.75,
                        line=dict(color="white",width=1),
                        colorbar=dict(title="ER", thickness=10)),
            text=df2["title"].str.slice(0,35),
            hovertemplate="<b>%{text}</b><br>İzlenme: %{x:,.0f}<br>Skor: %{y:.1f}<extra></extra>",
        ))
        apply_theme(fig); fig.update_layout(height=300, title="Score vs İzlenme")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    section_header("Video Detay", "#f5a623")
    pick = st.selectbox(
        "Video seç",
        df2["video_id"].tolist(),
        format_func=lambda vid: df2.loc[df2["video_id"]==vid,"title"].iloc[0] if vid in df2["video_id"].values else vid,
    )
    if pick:
        row = df2[df2["video_id"]==pick].iloc[0]
        st.markdown(f"""
        <div class="glass-panel">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap;">
            <div>
              <div style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:1rem;">{row['title']}</div>
              <div style="font-size:0.78rem;color:#5a6070;margin-top:4px;">Tarih: {row.get('date','')} · ID: <code>{pick[:16]}…</code></div>
            </div>
            <div style="display:flex;gap:16px;">
              <div style="text-align:right;"><div style="font-size:0.72rem;color:#5a6070;text-transform:uppercase;">İzlenme</div><div style="font-weight:700;">{fmt_int(row.get('views',0))}</div></div>
              <div style="text-align:right;"><div style="font-size:0.72rem;color:#5a6070;text-transform:uppercase;">ER</div><div style="font-weight:700;">{safe_float(row.get('er',0))*100:.2f}%</div></div>
              <div style="text-align:right;"><div style="font-size:0.72rem;color:#5a6070;text-transform:uppercase;">Shares/1K</div><div style="font-weight:700;">{safe_float(row.get('shares_per_1k',0)):.2f}</div></div>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

        with st.expander("📎 Ekran Görüntüsü Yükle", expanded=False):
            ss_files = st.file_uploader("SS seç", type=["png","jpg","jpeg","webp"],
                                         accept_multiple_files=True, key=f"ss_up_{pick}")
            if ss_files:
                saved = save_screenshots(pick, ss_files)
                st.success(f"{len(saved)} görüntü kaydedildi.")
            shots = list_screenshots(pick)
            if shots:
                for p in shots[-4:]: st.image(p, use_container_width=True)

        page_video_detail(pick, df2)

    show_raw = st.toggle("Ham tabloyu göster", value=False)
    if show_raw:
        cols_show = [c for c in ["title","date","views","er","shares_per_1k","score","video_id"] if c in df2.columns]
        st.dataframe(make_unique_columns(df2[cols_show].copy()), use_container_width=True, hide_index=True)


# ── VIEWERS ───────────────────────────────────────────────────────────────────
def page_viewers():
    df = read_csv_safe(export_path(period, "viewers"))
    if df is None or df.empty:
        st.info("Bu dönem için İzleyici verisi yok. → Ayarlar'dan yükle.")
        return

    section_header("İzleyici Analizi")
    # Try to render something meaningful
    numeric_cols = [c for c in df.columns if clean_numeric(df[c]).notna().sum() > len(df)*0.4]

    if len(numeric_cols) >= 1:
        cat_col = [c for c in df.columns if c not in numeric_cols]
        x_col   = cat_col[0] if cat_col else df.columns[0]
        y_col   = numeric_cols[0]

        fig = go.Figure(go.Bar(
            x=clean_numeric(df[y_col]), y=df[x_col].astype(str),
            orientation="h",
            marker=dict(color="#00c8d4", line=dict(width=0)),
        ))
        apply_theme(fig); fig.update_layout(height=400, title=y_col, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Ham Veri", expanded=False):
        st.dataframe(make_unique_columns(df.copy()), use_container_width=True, hide_index=True)


# ── FOLLOWERS ─────────────────────────────────────────────────────────────────
def page_followers():
    section_header("Takipçi Analizi")

    # History line chart
    df_hist = read_csv_safe(export_path(period, "follower_history"))
    if df_hist is not None and not df_hist.empty:
        date_col = find_col(df_hist, ["date","day","tarih"])
        fol_col  = find_col(df_hist, ["followers","net followers","new followers"])
        if date_col and fol_col:
            df_hist["_date"] = pd.to_datetime(df_hist[date_col], errors="coerce")
            df_hist["_fol"]  = clean_numeric(df_hist[fol_col]).fillna(0)
            df_hist = df_hist.dropna(subset=["_date"]).sort_values("_date")
            fig = go.Figure(go.Scatter(
                x=df_hist["_date"], y=df_hist["_fol"], mode="lines+markers",
                fill="tozeroy", fillcolor="rgba(0,200,212,0.07)",
                line=dict(color="#00c8d4", width=2.5),
                hovertemplate="<b>%{x|%d %b}</b>: %{y:,.0f}<extra></extra>",
            ))
            apply_theme(fig); fig.update_layout(height=280, title="Takipçi Geçmişi")
            st.plotly_chart(fig, use_container_width=True)
        else:
            with st.expander("Follower History Ham Veri", expanded=False):
                st.dataframe(make_unique_columns(df_hist.copy()), use_container_width=True, hide_index=True)
    else:
        st.info("Follower History yok.")

    c1, c2 = st.columns(2)

    # Gender donut
    with c1:
        df_g = read_csv_safe(export_path(period, "follower_gender"))
        if df_g is not None and not df_g.empty:
            gender_col = find_col(df_g, ["gender","cinsiyet"])
            pct_col    = find_col(df_g, ["percentage","percent","oran","%"])
            if gender_col and pct_col:
                vals = clean_numeric(df_g[pct_col]).fillna(0)
                fig  = go.Figure(go.Pie(
                    labels=df_g[gender_col].astype(str), values=vals,
                    hole=0.55,
                    marker=dict(colors=["#00c8d4","#7c5cfc","#74e27a"], line=dict(color="white",width=3)),
                ))
                apply_theme(fig); fig.update_layout(height=280, title="Cinsiyet Dağılımı")
                st.plotly_chart(fig, use_container_width=True)
            else:
                with st.expander("Gender Verisi", expanded=False):
                    st.dataframe(make_unique_columns(df_g.copy()), use_container_width=True, hide_index=True)
        else:
            st.info("Gender verisi yok.")

    # Top territories bar
    with c2:
        df_t = read_csv_safe(export_path(period, "follower_top_territories"))
        if df_t is not None and not df_t.empty:
            ter_col = find_col(df_t, ["territory","country","ülke","bölge"])
            pct_col = find_col(df_t, ["percentage","percent","followers","takipçi"])
            if ter_col and pct_col:
                df_t["_val"] = clean_numeric(df_t[pct_col]).fillna(0)
                df_t = df_t.sort_values("_val", ascending=False).head(10)
                fig = go.Figure(go.Bar(
                    x=df_t["_val"], y=df_t[ter_col].astype(str), orientation="h",
                    marker=dict(color="#7c5cfc", line=dict(width=0)),
                ))
                apply_theme(fig); fig.update_layout(height=280, title="Top Bölgeler", yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig, use_container_width=True)
            else:
                with st.expander("Territories Verisi", expanded=False):
                    st.dataframe(make_unique_columns(df_t.copy()), use_container_width=True, hide_index=True)
        else:
            st.info("Territories verisi yok.")

    # Activity heatmap
    df_a = read_csv_safe(export_path(period, "follower_activity"))
    if df_a is not None and not df_a.empty:
        hour_col = find_col(df_a, ["hour","saat"])
        day_col  = find_col(df_a, ["day","gün","weekday"])
        val_col  = find_col(df_a, ["followers","active","activity","aktif"])
        if hour_col and day_col and val_col:
            df_a["_val"]  = clean_numeric(df_a[val_col]).fillna(0)
            pivot = df_a.pivot_table(index=day_col, columns=hour_col, values="_val", aggfunc="sum").fillna(0)
            fig = go.Figure(go.Heatmap(
                z=pivot.values, x=pivot.columns, y=pivot.index,
                colorscale=[[0,"#f0f2f5"],[0.5,"#00c8d4"],[1,"#7c5cfc"]],
                hovertemplate="Gün: %{y}<br>Saat: %{x}<br>Aktif: %{z:,.0f}<extra></extra>",
            ))
            apply_theme(fig); fig.update_layout(height=280, title="Aktivite Isı Haritası")
            st.plotly_chart(fig, use_container_width=True)
        else:
            with st.expander("Activity Verisi", expanded=False):
                st.dataframe(make_unique_columns(df_a.copy()), use_container_width=True, hide_index=True)
    else:
        st.info("Follower Activity verisi yok.")


# ── ROUTER ────────────────────────────────────────────────────────────────────
try:
    if   page == "Ayarlar":       page_settings()
    elif page == "Genel Bakış":   page_overview()
    elif page == "Growth Cockpit":page_growth_cockpit()
    elif page == "İçerik":        page_content()
    elif page == "İzleyiciler":   page_viewers()
    elif page == "Takipçiler":    page_followers()
except Exception as e:
    st.error(f"⚠️ Sayfa yüklenirken hata oluştu: {e}")
    with st.expander("Hata detayı", expanded=False):
        import traceback
        st.code(traceback.format_exc())
