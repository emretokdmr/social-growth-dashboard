import streamlit as st
import pandas as pd
import os, json, uuid
from datetime import datetime

st.set_page_config(page_title="Social Growth Dashboard", layout="wide")

# -----------------------------
# Style (modern dark tech)
# -----------------------------
st.markdown("""
<style>
.block-container {padding-top: 2rem; padding-bottom: 2rem; max-width: 1400px;}
[data-testid="stSidebar"] {background: linear-gradient(180deg, #0b1220 0%, #070b14 100%);}
h1,h2,h3 {letter-spacing: -0.02em;}
.small-muted {opacity: .75; font-size: 0.9rem;}
.card {
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 16px;
  padding: 14px 16px;
  background: rgba(255,255,255,.03);
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Storage helpers (local to server)
# NOTE: Streamlit Cloud storage is ephemeral. Re-upload exports when needed.
# -----------------------------
BASE_DIR = "storage"
EXPORT_DIR = os.path.join(BASE_DIR, "exports")      # exports/<period>/<type>.csv
VIDEO_DIR = os.path.join(BASE_DIR, "videos")        # videos/<video_id>.json
SS_DIR = os.path.join(BASE_DIR, "screenshots")      # screenshots/<video_id>/*

for d in [BASE_DIR, EXPORT_DIR, VIDEO_DIR, SS_DIR]:
    os.makedirs(d, exist_ok=True)

PERIODS = ["7", "28", "60", "365"]
EXPORT_TYPES = [
    ("overview", "Overview"),
    ("content", "Content"),
    ("viewers", "Viewers"),
    ("follower_history", "Follower History"),
    ("follower_activity", "Follower Activity"),
    ("follower_gender", "Follower Gender"),
    ("follower_top_territories", "Follower Top Territories"),
]
EXPORT_TYPE_LABEL = dict(EXPORT_TYPES)

def export_path(period: str, export_type: str) -> str:
    pdir = os.path.join(EXPORT_DIR, period)
    os.makedirs(pdir, exist_ok=True)
    return os.path.join(pdir, f"{export_type}.csv")

def read_csv_safe(path: str):
    if not os.path.exists(path):
        return None
    try:
        return pd.read_csv(path)
    except Exception as e:
        st.error(f"CSV okunamadı: {path}\n{e}")
        return None

def make_unique_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure unique column names for Arrow/Streamlit compatibility."""
    seen = {}
    new_cols = []
    for c in df.columns:
        base = str(c)
        if base not in seen:
            seen[base] = 0
            new_cols.append(base)
        else:
            seen[base] += 1
            new_cols.append(f"{base}__{seen[base]}")
    df.columns = new_cols
    return df

def norm_cols(df: pd.DataFrame) -> dict:
    return {c.lower().strip(): c for c in df.columns}

def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols = norm_cols(df)
    for c in candidates:
        if c in cols:
            return cols[c]
    return None

def sum_num(df: pd.DataFrame, colname: str | None) -> float:
    if not colname or colname not in df.columns:
        return 0.0
    s = pd.to_numeric(df[colname], errors="coerce").fillna(0)
    s[s < 0] = 0
    return float(s.sum())

# -----------------------------
# Upload type guessing (bulk mode)
# -----------------------------
def guess_export_type(df: pd.DataFrame, filename: str) -> str | None:
    name = filename.lower()
    cols = {c.lower().strip() for c in df.columns}

    if "overview" in name: return "overview"
    if "content" in name: return "content"
    if "viewer" in name: return "viewers"
    if "gender" in name: return "follower_gender"
    if "territor" in name: return "follower_top_territories"
    if "activity" in name: return "follower_activity"
    if "history" in name: return "follower_history"

    if {"video views", "profile views"} & cols: return "overview"
    if {"title", "video views"} & cols: return "content"
    if ("viewers" in cols) or ("total viewers" in cols): return "viewers"
    if ({"female", "male"} & cols) or ("gender" in cols): return "follower_gender"
    if ("territory" in cols) or ("country" in cols): return "follower_top_territories"
    if ("hour" in cols) or ("day" in cols): return "follower_activity"
    if ("followers" in cols) and (("date" in cols) or ("day" in cols)): return "follower_history"

    return None

# -----------------------------
# Content parsing
# -----------------------------
def list_videos_from_content(period: str) -> pd.DataFrame:
    df = read_csv_safe(export_path(period, "content"))
    if df is None or df.empty:
        return pd.DataFrame()

    cols = norm_cols(df)
    title_col = cols.get("title") or cols.get("video title") or cols.get("content") or list(df.columns)[0]
    date_col = cols.get("date") or cols.get("publish date") or cols.get("create time") or None
    views_col = cols.get("video views") or cols.get("views") or None
    likes_col = cols.get("likes") or None
    comments_col = cols.get("comments") or None
    shares_col = cols.get("shares") or None

    out = pd.DataFrame()
    out["title"] = df[title_col].astype(str)
    out["date"] = df[date_col].astype(str) if date_col else ""
    out["views"] = pd.to_numeric(df[views_col], errors="coerce") if views_col else pd.NA
    out["likes"] = pd.to_numeric(df[likes_col], errors="coerce") if likes_col else pd.NA
    out["comments"] = pd.to_numeric(df[comments_col], errors="coerce") if comments_col else pd.NA
    out["shares"] = pd.to_numeric(df[shares_col], errors="coerce") if shares_col else pd.NA

    if "comments" in out.columns:
        out["comments"] = out["comments"].fillna(0)
        out.loc[out["comments"] < 0, "comments"] = 0

    denom = out["views"].replace({0: pd.NA}) if "views" in out.columns else pd.Series([pd.NA]*len(out))
    num = out[["likes","comments","shares"]].fillna(0).sum(axis=1) if set(["likes","comments","shares"]).issubset(out.columns) else 0
    out["er"] = (num / denom).fillna(0) if len(out) else 0.0
    out["shares_per_1k"] = ((out["shares"].fillna(0) / denom) * 1000).fillna(0) if "shares" in out.columns else 0.0

    out["video_id"] = out.apply(lambda r: str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{r['title']}|{r['date']}")), axis=1)
    return out

# -----------------------------
# Per-video state + screenshots
# -----------------------------
def video_json_path(video_id: str) -> str:
    return os.path.join(VIDEO_DIR, f"{video_id}.json")

def load_video_state(video_id: str) -> dict:
    path = video_json_path(video_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "video_id": video_id,
        "notes": "",
        "duration_sec": None,
        "avg_watch_sec": None,
        "completion_pct": None,
        "followers_gained": None,
        "last_updated": None,
    }

def save_video_state(video_id: str, state: dict):
    state["last_updated"] = datetime.utcnow().isoformat()
    with open(video_json_path(video_id), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def save_screenshots(video_id: str, files):
    vdir = os.path.join(SS_DIR, video_id)
    os.makedirs(vdir, exist_ok=True)
    saved = []
    for f in files:
        fname = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{f.name}"
        path = os.path.join(vdir, fname)
        with open(path, "wb") as out:
            out.write(f.getbuffer())
        saved.append(path)
    return saved

def list_screenshots(video_id: str):
    vdir = os.path.join(SS_DIR, video_id)
    if not os.path.exists(vdir):
        return []
    return sorted([os.path.join(vdir, x) for x in os.listdir(vdir)])

# -----------------------------
# Scoring (no er/shares_per_1k return -> avoids collisions)
# -----------------------------
def compute_growth_score(row, vstate: dict):
    duration = vstate.get("duration_sec") or None
    avg_watch = vstate.get("avg_watch_sec") or None
    completion = vstate.get("completion_pct") or None
    followers_gained = vstate.get("followers_gained") or None

    views = row.get("views") or 0
    shares_per_1k = row.get("shares_per_1k", 0.0) or 0.0

    retention = None
    if duration and avg_watch and duration > 0:
        retention = max(0.0, min(1.0, float(avg_watch) / float(duration)))

    follow_per_1k = None
    if followers_gained is not None and views and views > 0:
        follow_per_1k = (float(followers_gained) / float(views)) * 1000.0

    retention_score = (retention or 0.0) * 50
    completion_score = (float(completion) / 100.0 if completion is not None else 0.0) * 25
    share_score = (float(shares_per_1k) / 10.0) * 15
    follow_score = (float(follow_per_1k) / 10.0 if follow_per_1k is not None else 0.0) * 10

    score = retention_score + completion_score + share_score + follow_score
    return {"retention": retention, "follow_per_1k": follow_per_1k, "score": score}

def safe_float(x, default=0.0) -> float:
    try:
        return float(pd.to_numeric(pd.Series([x]), errors="coerce").fillna(default).iloc[0])
    except Exception:
        return float(default)

def fmt_int(x) -> str:
    return f"{int(x):,}".replace(",", ".")

# -----------------------------
# Sidebar navigation
# -----------------------------
st.sidebar.title("Social Growth")
period = st.sidebar.radio("Dönem", PERIODS, horizontal=True)
page = st.sidebar.radio(
    "Menü",
    ["Genel Bakış", "Growth Cockpit", "İçerik", "İzleyiciler", "Takipçiler", "Ayarlar"],
)
st.sidebar.caption("Spor odaklı | Eğlence + Bilgi")

# -----------------------------
# Pages
# -----------------------------
def page_settings():
    st.title("Ayarlar: Veri Yükleme")
    st.write("CSV export’larını **toplu** yükle. Sistem dosya tipini otomatik bulur; bulamazsa sen seçersin.")

    period_sel = st.radio("Yükleme dönemi", PERIODS, horizontal=True, index=PERIODS.index(period) if period in PERIODS else 0)
    mode = st.segmented_control("Yükleme modu", ["Toplu (önerilen)", "Tekli"], default="Toplu (önerilen)")

    st.divider()

    if mode == "Toplu (önerilen)":
        ups = st.file_uploader("CSV dosyalarını seç (birden fazla)", type=["csv"], accept_multiple_files=True)
        if ups:
            results = []
            for up in ups:
                try:
                    df = pd.read_csv(up)
                except Exception as e:
                    results.append({"file": up.name, "status": f"OKUNAMADI: {e}", "type": None, "saved_to": None})
                    continue

                guessed = guess_export_type(df, up.name)
                etype = guessed

                if etype is None:
                    etype = st.selectbox(
                        f"Tür seç: {up.name}",
                        [x[0] for x in EXPORT_TYPES],
                        format_func=lambda t: EXPORT_TYPE_LABEL.get(t, t),
                        key=f"type_{up.name}"
                    )

                path = export_path(period_sel, etype)
                try:
                    up.seek(0)
                    with open(path, "wb") as f:
                        f.write(up.getbuffer())
                    results.append({"file": up.name, "status": "Yüklendi", "type": etype, "saved_to": path})
                except Exception as e:
                    results.append({"file": up.name, "status": f"KAYDEDİLEMEDİ: {e}", "type": etype, "saved_to": path})

            st.success("Yükleme tamamlandı.")
            st.dataframe(make_unique_columns(pd.DataFrame(results)), use_container_width=True, hide_index=True)

    else:
        col1, col2 = st.columns([1, 2])
        with col1:
            etype = st.selectbox(
                "Export türü",
                [x[0] for x in EXPORT_TYPES],
                format_func=lambda t: EXPORT_TYPE_LABEL.get(t, t),
            )
            up = st.file_uploader("CSV yükle", type=["csv"], key="single_upload")
            if up is not None:
                path = export_path(period_sel, etype)
                with open(path, "wb") as f:
                    f.write(up.getbuffer())
                st.success(f"Yüklendi: {path}")

        with col2:
            st.subheader("Yüklü dosyalar")
            rows = []
            for p in PERIODS:
                for et, _label in EXPORT_TYPES:
                    path = export_path(p, et)
                    rows.append({"period": p, "type": et, "exists": os.path.exists(path), "path": path})
            st.dataframe(make_unique_columns(pd.DataFrame(rows)), use_container_width=True, hide_index=True)

def page_overview():
    st.title("Genel Bakış")
    df = read_csv_safe(export_path(period, "overview"))
    if df is None or df.empty:
        st.info("Bu dönem için Overview yok. Ayarlar’dan yükle.")
        return

    views_col    = find_col(df, ["video views", "views", "total video views"])
    profile_col  = find_col(df, ["profile views", "profile visits", "profile view"])
    likes_col    = find_col(df, ["likes", "total likes"])
    comments_col = find_col(df, ["comments", "total comments"])
    shares_col   = find_col(df, ["shares", "total shares"])

    total_views    = sum_num(df, views_col)
    total_profile  = sum_num(df, profile_col)
    total_likes    = sum_num(df, likes_col)
    total_comments = sum_num(df, comments_col)
    total_shares   = sum_num(df, shares_col)

    profile_ctr = (total_profile / total_views) if total_views else 0
    er = ((total_likes + total_comments + total_shares) / total_views) if total_views else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Views", fmt_int(total_views))
    c2.metric("Profile Views", fmt_int(total_profile))
    c3.metric("Profile CTR", f"{profile_ctr*100:.2f}%")
    c4.metric("Engagement Rate", f"{er*100:.2f}%")

    st.subheader("Ham tablo (isteğe bağlı)")
    with st.expander("Göster", expanded=False):
        st.dataframe(make_unique_columns(df.copy()), use_container_width=True)

def page_growth_cockpit():
    st.title("Growth Cockpit")
    st.caption("Sadece büyüten metrikler. Diğer her şey gürültü.")

    o = read_csv_safe(export_path(period, "overview"))
    c = list_videos_from_content(period)
    if o is None or o.empty:
        st.info("Overview yok. Ayarlar’dan yükle.")
        return

    views_col    = find_col(o, ["video views", "views", "total video views"])
    profile_col  = find_col(o, ["profile views", "profile visits", "profile view"])
    likes_col    = find_col(o, ["likes", "total likes"])
    comments_col = find_col(o, ["comments", "total comments"])
    shares_col   = find_col(o, ["shares", "total shares"])

    total_views    = sum_num(o, views_col)
    total_profile  = sum_num(o, profile_col)
    total_likes    = sum_num(o, likes_col)
    total_comments = sum_num(o, comments_col)
    total_shares   = sum_num(o, shares_col)

    profile_ctr = (total_profile / total_views) if total_views else 0
    er_total = ((total_likes + total_comments + total_shares) / total_views) if total_views else 0
    shares_per_1k = (total_shares / total_views) * 1000 if total_views else 0

    follow_per_1k_list = []
    completion_list = []

    if not c.empty:
        for _, row in c.iterrows():
            vid = row["video_id"]
            vs = load_video_state(vid)
            if vs.get("followers_gained") is not None and row.get("views") and row.get("views") > 0:
                follow_per_1k_list.append((float(vs["followers_gained"]) / float(row["views"])) * 1000.0)
            if vs.get("completion_pct") is not None:
                completion_list.append(float(vs["completion_pct"]))

    avg_follow_per_1k = sum(follow_per_1k_list) / len(follow_per_1k_list) if follow_per_1k_list else None
    avg_completion = sum(completion_list) / len(completion_list) if completion_list else None

    a, b, cc, d, e, f = st.columns(6)
    a.metric("Views", fmt_int(total_views))
    b.metric("Profile CTR", f"{profile_ctr*100:.2f}%")
    cc.metric("Engagement", f"{er_total*100:.2f}%")
    d.metric("Shares / 1K", f"{shares_per_1k:.2f}")
    e.metric("Follow / 1K", "-" if avg_follow_per_1k is None else f"{avg_follow_per_1k:.2f}")
    f.metric("Completion %", "-" if avg_completion is None else f"{avg_completion:.1f}")

    st.divider()
    st.subheader("Bu dönem aksiyonları")
    actions = []
    if profile_ctr < 0.007:
        actions.append("Profile CTR düşük: bio + sabitlenmiş 3 video + net CTA şart. İzleyen profile gitmiyor.")
    if shares_per_1k < 3:
        actions.append("Paylaşım zayıf: bilgi içeriğini ‘kaydet/at’ formatına çevir, daha kısa ve net yap.")
    if avg_completion is not None and avg_completion < 25:
        actions.append("Completion düşük: giriş (ilk 2 saniye) tırt. Hook’u sertleştir, videoyu kısalt.")
    if not actions:
        actions.append("Sinyaller fena değil: en iyi 3 videonun formatını çoğalt, 3 hook varyasyonu test et.")
    for x in actions:
        st.write("• " + x)

def page_video_detail(vid: str):
    state = load_video_state(vid)

    shots = list_screenshots(vid)
    if shots:
        with st.expander("Yüklenen SS’ler", expanded=False):
            for p in shots[-8:]:
                st.image(p, use_container_width=True)

    st.divider()
    st.subheader("Retention / Conversion metrikleri (SS’den gir)")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        state["duration_sec"] = st.number_input("Video süresi (sn)", value=state["duration_sec"] or 0, min_value=0, step=1, key=f"dur_{vid}")
    with c2:
        state["avg_watch_sec"] = st.number_input("Avg watch (sn)", value=state["avg_watch_sec"] or 0.0, min_value=0.0, step=0.1, key=f"avg_{vid}")
    with c3:
        state["completion_pct"] = st.number_input("Completion %", value=state["completion_pct"] or 0.0, min_value=0.0, max_value=100.0, step=0.1, key=f"comp_{vid}")
    with c4:
        state["followers_gained"] = st.number_input("Followers gained", value=state["followers_gained"] or 0, min_value=0, step=1, key=f"fol_{vid}")

    state["notes"] = st.text_area("Notlar", value=state.get("notes",""), height=120, key=f"notes_{vid}")

    if st.button("Kaydet", key=f"save_{vid}"):
        if state["duration_sec"] == 0: state["duration_sec"] = None
        if state["avg_watch_sec"] == 0: state["avg_watch_sec"] = None
        if state["completion_pct"] == 0: state["completion_pct"] = None
        if state["followers_gained"] == 0: state["followers_gained"] = None
        save_video_state(vid, state)
        st.success("Kaydedildi.")

    st.divider()
    st.subheader("Otomatik ilk teşhis (kural tabanlı)")

    df = list_videos_from_content(period)
    row = df[df["video_id"]==vid].iloc[0].to_dict() if not df.empty else {"views": 0, "shares_per_1k": 0.0}
    res = compute_growth_score(row, state)

    colA, colB, colC = st.columns(3)
    colA.metric("Score", f"{safe_float(res.get('score')):.1f}")
    colB.metric("Retention", "-" if res.get("retention") is None else f"{safe_float(res.get('retention'))*100:.1f}%")
    colC.metric("Follow / 1K", "-" if res.get("follow_per_1k") is None else f"{safe_float(res.get('follow_per_1k')):.2f}")

    verdicts = []
    if res.get("retention") is not None and safe_float(res.get("retention")) < 0.35:
        verdicts.append("Hook/tempo tırt: izleyici videoda kalmıyor. İlk 2 saniyeyi sertleştir.")
    if state.get("completion_pct") is not None and safe_float(state.get("completion_pct")) < 20:
        verdicts.append("Completion düşük: video gereksiz uzuyor veya payoff geç geliyor.")
    if safe_float(row.get("shares_per_1k", 0)) < 3:
        verdicts.append("Paylaşım zayıf: bilgi içeriğini ‘kopyala-yapıştır değer’ gibi paketle, daha keskin başlık.")
    if not verdicts:
        verdicts.append("Sinyaller fena değil: aynı formatı 3 varyasyonla tekrar dene (hook değiştir, tempo sabit).")

    for v in verdicts:
        st.write("• " + v)

def page_content():
    st.title("İçerik")
    df = list_videos_from_content(period)
    if df.empty:
        st.info("Bu dönem için Content yok. Ayarlar’dan yükle.")
        return

    scores = []
    for _, row in df.iterrows():
        vs = load_video_state(row["video_id"])
        scores.append(compute_growth_score(row, vs))
    s = pd.DataFrame(scores)
    s = make_unique_columns(s)
    df2 = pd.concat([df.reset_index(drop=True), s.reset_index(drop=True)], axis=1)
    df2 = make_unique_columns(df2)

    with st.expander("Filtreler", expanded=False):
        min_views = st.number_input("Min Views", value=0)
        sort_by = st.selectbox("Sırala", ["score", "views", "er", "shares_per_1k"], index=1)
        top_n = st.slider("Grafiklerde gösterilecek video sayısı", 5, 50, 15)
        show_raw = st.toggle("Ham tabloyu göster", value=False)

    df2 = df2[pd.to_numeric(df2["views"], errors="coerce").fillna(0) >= min_views].copy()
    df2["views"] = pd.to_numeric(df2["views"], errors="coerce").fillna(0)
    df2["er"] = pd.to_numeric(df2["er"], errors="coerce").fillna(0)
    df2["shares_per_1k"] = pd.to_numeric(df2["shares_per_1k"], errors="coerce").fillna(0)
    df2["score"] = pd.to_numeric(df2["score"], errors="coerce").fillna(0)
    df2 = df2.sort_values(sort_by, ascending=False)

    total_videos = int(len(df2))
    total_views = int(df2["views"].sum())
    avg_er = float(df2["er"].mean()) if "er" in df2.columns else 0.0
    avg_shares_1k = float(df2["shares_per_1k"].mean()) if "shares_per_1k" in df2.columns else 0.0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Video sayısı", f"{total_videos}")
    k2.metric("Toplam Views", fmt_int(total_views))
    k3.metric("Ortalama ER", f"{avg_er*100:.2f}%")
    k4.metric("Ortalama Shares / 1K", f"{avg_shares_1k:.2f}")

    st.divider()

    top = df2.head(top_n).copy()
    top["title_short"] = top["title"].astype(str).str.slice(0, 42)

    cA, cB = st.columns(2)
    with cA:
        st.subheader("En çok izlenenler")
        chart_df = top[["title_short", "views"]].copy().rename(columns={"title_short": "Video"})
        st.bar_chart(chart_df.set_index("Video"))

    with cB:
        st.subheader("En çok paylaşılanlar (1K başına)")
        chart_df = top[["title_short", "shares_per_1k"]].copy().rename(columns={"title_short": "Video"})
        st.bar_chart(chart_df.set_index("Video"))

    cC, cD = st.columns(2)
    with cC:
        st.subheader("ER dağılımı")
        hist = df2["er"].copy()
        bins = pd.cut(hist, bins=[0,0.01,0.02,0.03,0.05,0.08,1.0], include_lowest=True)
        hist_df = bins.value_counts().sort_index().reset_index()
        hist_df.columns = ["ER bandı", "Video sayısı"]
        st.bar_chart(hist_df.set_index("ER bandı"))

    with cD:
        st.subheader("Score vs Views")
        scatter = df2[["views","score"]].copy()
        st.scatter_chart(scatter, x="views", y="score")

    st.divider()

    st.subheader("Video seç ve SS yükle (video bazlı)")
    pick = st.selectbox(
        "Video",
        df2["video_id"].tolist(),
        format_func=lambda vid: df2.loc[df2["video_id"]==vid,"title"].iloc[0],
        key="pick_video"
    )

    if pick:
        st.session_state["selected_video_id"] = pick
        row = df2[df2["video_id"] == pick].iloc[0]

        views_val = safe_float(row.get("views"), 0)
        er_val = safe_float(row.get("er"), 0) * 100.0
        sh_val = safe_float(row.get("shares_per_1k"), 0)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        left, right = st.columns([3,2])
        with left:
            st.markdown(f"### {row['title']}")
            st.markdown(f"<div class='small-muted'>Tarih: {row.get('date','')} | Video ID: <code>{pick}</code></div>", unsafe_allow_html=True)
        with right:
            st.metric("Views", fmt_int(views_val))
            st.metric("ER", f"{er_val:.2f}%")
            st.metric("Shares/1K", f"{sh_val:.2f}")
        st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("📌 Bu videonun Analytics SS'lerini yükle", expanded=True):
            ss_files = st.file_uploader(
                "SS seç (birden fazla)",
                type=["png","jpg","jpeg","webp"],
                accept_multiple_files=True,
                key=f"ss_uploader_{pick}"
            )
            if ss_files:
                saved = save_screenshots(pick, ss_files)
                st.success(f"{len(saved)} SS kaydedildi.")

            shots = list_screenshots(pick)
            if shots:
                st.caption("Son yüklenenler")
                for p in shots[-6:]:
                    st.image(p, use_container_width=True)

        st.caption("Detaylı metrik girmek için aşağıdaki Video Detay alanını kullan.")
        st.divider()
        st.subheader("Video Detay")
        page_video_detail(pick)

    if show_raw:
        st.divider()
        st.subheader("Ham tablo")
        show = df2[["title","date","views","er","shares_per_1k","retention","follow_per_1k","score","video_id"]].copy()
        show = make_unique_columns(show)
        st.dataframe(show, use_container_width=True, hide_index=True)

def page_viewers():
    st.title("İzleyiciler")
    df = read_csv_safe(export_path(period, "viewers"))
    if df is None or df.empty:
        st.info("Bu dönem için Viewers yok. Ayarlar’dan yükle.")
        return
    st.dataframe(make_unique_columns(df.copy()), use_container_width=True)

def page_followers():
    st.title("Takipçiler")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Follower History")
        df = read_csv_safe(export_path(period, "follower_history"))
        if df is None or df.empty:
            st.info("FollowerHistory yok.")
        else:
            st.dataframe(make_unique_columns(df.copy()), use_container_width=True)

    with c2:
        st.subheader("Follower Activity")
        df = read_csv_safe(export_path(period, "follower_activity"))
        if df is None or df.empty:
            st.info("FollowerActivity yok.")
        else:
            st.dataframe(make_unique_columns(df.copy()), use_container_width=True)

    st.subheader("Gender / Territories")
    g1, g2 = st.columns(2)
    with g1:
        df = read_csv_safe(export_path(period, "follower_gender"))
        if df is None or df.empty:
            st.info("FollowerGender yok.")
        else:
            st.dataframe(make_unique_columns(df.copy()), use_container_width=True)
    with g2:
        df = read_csv_safe(export_path(period, "follower_top_territories"))
        if df is None or df.empty:
            st.info("FollowerTopTerritories yok.")
        else:
            st.dataframe(make_unique_columns(df.copy()), use_container_width=True)

# -----------------------------
# Router
# -----------------------------
if page == "Ayarlar":
    page_settings()
elif page == "Genel Bakış":
    page_overview()
elif page == "Growth Cockpit":
    page_growth_cockpit()
elif page == "İçerik":
    page_content()
elif page == "İzleyiciler":
    page_viewers()
elif page == "Takipçiler":
    page_followers()
