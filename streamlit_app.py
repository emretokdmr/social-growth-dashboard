import streamlit as st
import pandas as pd
import os, json, uuid
from datetime import datetime

st.set_page_config(page_title="Social Growth Dashboard", layout="wide")

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

def list_videos_from_content(period: str):
    df = read_csv_safe(export_path(period, "content"))
    if df is None or df.empty:
        return pd.DataFrame()
    # Normalize column names a bit
    cols = {c.lower().strip(): c for c in df.columns}
    # Try to find likely columns
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

    # Clean weird negatives in comments (seen in your exports)
    if "comments" in out.columns:
        out["comments"] = out["comments"].fillna(0)
        out.loc[out["comments"] < 0, "comments"] = 0

    # Engagement rate if possible
    if out["views"].notna().any():
        denom = out["views"].replace({0: pd.NA})
        num = out[["likes","comments","shares"]].fillna(0).sum(axis=1)
        out["er"] = (num / denom).fillna(0)
        out["shares_per_1k"] = ((out["shares"].fillna(0) / denom) * 1000).fillna(0)
    else:
        out["er"] = 0.0
        out["shares_per_1k"] = 0.0

    # Attach stable video_id (hash-like)
    out["video_id"] = out.apply(lambda r: str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{r['title']}|{r['date']}")), axis=1)
    return out

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

def compute_growth_score(row, vstate: dict):
    # Simple scoring: retention-heavy
    # retention = avg_watch / duration
    duration = vstate.get("duration_sec") or None
    avg_watch = vstate.get("avg_watch_sec") or None
    completion = vstate.get("completion_pct") or None
    followers_gained = vstate.get("followers_gained") or None

    views = row.get("views")
    shares_per_1k = row.get("shares_per_1k", 0.0)
    er = row.get("er", 0.0)

    retention = None
    if duration and avg_watch and duration > 0:
        retention = max(0.0, min(1.0, float(avg_watch) / float(duration)))

    follow_per_1k = None
    if followers_gained is not None and views and views > 0:
        follow_per_1k = (float(followers_gained) / float(views)) * 1000.0

    # Score components (missing values treated as 0)
    retention_score = (retention or 0.0) * 50
    completion_score = (float(completion) / 100.0 if completion is not None else 0.0) * 25
    share_score = (float(shares_per_1k) / 10.0) * 15  # rough scaling
    follow_score = (float(follow_per_1k) / 10.0 if follow_per_1k is not None else 0.0) * 10

    score = retention_score + completion_score + share_score + follow_score
    return {
        "retention": retention,
        "follow_per_1k": follow_per_1k,
        "score": score,
        "er": er,
        "shares_per_1k": shares_per_1k,
    }

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
    st.write("Export CSV’lerini buradan yükle. Dönemi (7/28/60/365) doğru seçmeyi unutma.")

    col1, col2 = st.columns([1, 2])

    with col1:
        etype = st.selectbox("Export türü", EXPORT_TYPES, format_func=lambda x: x[1])[0]
        up = st.file_uploader("CSV yükle", type=["csv"])
        if up is not None:
            path = export_path(period, etype)
            with open(path, "wb") as f:
                f.write(up.getbuffer())
            st.success(f"Yüklendi: {path}")

    with col2:
        st.subheader("Yüklü dosyalar")
        rows = []
        for p in PERIODS:
            for et, label in EXPORT_TYPES:
                path = export_path(p, et)
                rows.append({
                    "period": p,
                    "type": et,
                    "exists": os.path.exists(path),
                    "path": path
                })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

def page_overview():
    st.title("Genel Bakış")
    df = read_csv_safe(export_path(period, "overview"))
    if df is None or df.empty:
        st.info("Bu dönem için Overview yok. Ayarlar’dan yükle.")
        return

    # Try to detect common columns in your exports
    cols = {c.lower().strip(): c for c in df.columns}
    views_col = cols.get("video views") or cols.get("views")
    profile_col = cols.get("profile views") or cols.get("profile visits") or cols.get("profile view")
    likes_col = cols.get("likes")
    comments_col = cols.get("comments")
    shares_col = cols.get("shares")

    # Aggregate
    total_views = pd.to_numeric(df[views_col], errors="coerce").fillna(0).sum() if views_col else 0
    total_profile = pd.to_numeric(df[profile_col], errors="coerce").fillna(0).sum() if profile_col else 0
    total_likes = pd.to_numeric(df[likes_col], errors="coerce").fillna(0).sum() if likes_col else 0
    total_comments = pd.to_numeric(df[comments_col], errors="coerce").fillna(0)
    total_comments[total_comments < 0] = 0
    total_comments = total_comments.sum() if comments_col else 0
    total_shares = pd.to_numeric(df[shares_col], errors="coerce").fillna(0).sum() if shares_col else 0

    profile_ctr = (total_profile / total_views) if total_views else 0
    er = ((total_likes + total_comments + total_shares) / total_views) if total_views else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Views", f"{int(total_views):,}".replace(",", "."))
    c2.metric("Profile Views", f"{int(total_profile):,}".replace(",", "."))
    c3.metric("Profile CTR", f"{profile_ctr*100:.2f}%")
    c4.metric("Engagement Rate", f"{er*100:.2f}%")

    st.subheader("Ham tablo")
    st.dataframe(df, use_container_width=True)

def page_growth_cockpit():
    st.title("Growth Cockpit")
    st.caption("Sadece büyüten metrikler. Diğer her şey gürültü.")

    # overview summary
    o = read_csv_safe(export_path(period, "overview"))
    c = list_videos_from_content(period)

    if o is None or o.empty:
        st.info("Overview yok. Ayarlar’dan yükle.")
        return

    cols = {x.lower().strip(): x for x in o.columns}
    views_col = cols.get("video views") or cols.get("views")
    profile_col = cols.get("profile views") or cols.get("profile visits") or cols.get("profile view")
    likes_col = cols.get("likes")
    comments_col = cols.get("comments")
    shares_col = cols.get("shares")

    total_views = pd.to_numeric(o[views_col], errors="coerce").fillna(0).sum() if views_col else 0
    total_profile = pd.to_numeric(o[profile_col], errors="coerce").fillna(0).sum() if profile_col else 0
    total_likes = pd.to_numeric(o[likes_col], errors="coerce").fillna(0).sum() if likes_col else 0
    total_comments = pd.to_numeric(o[comments_col], errors="coerce").fillna(0)
    total_comments[total_comments < 0] = 0
    total_comments = total_comments.sum() if comments_col else 0
    total_shares = pd.to_numeric(o[shares_col], errors="coerce").fillna(0).sum() if shares_col else 0

    profile_ctr = (total_profile / total_views) if total_views else 0
    er = ((total_likes + total_comments + total_shares) / total_views) if total_views else 0
    shares_per_1k = (total_shares / total_views) * 1000 if total_views else 0

    # Pull SS metrics from per-video json (if available)
    follow_per_1k_list = []
    completion_list = []
    avg_watch_list = []

    if not c.empty:
        for _, row in c.iterrows():
            vid = row["video_id"]
            vs = load_video_state(vid)
            if vs.get("followers_gained") is not None and row.get("views") and row.get("views") > 0:
                follow_per_1k_list.append((float(vs["followers_gained"]) / float(row["views"])) * 1000.0)
            if vs.get("completion_pct") is not None:
                completion_list.append(float(vs["completion_pct"]))
            if vs.get("avg_watch_sec") is not None:
                avg_watch_list.append(float(vs["avg_watch_sec"]))

    avg_follow_per_1k = sum(follow_per_1k_list) / len(follow_per_1k_list) if follow_per_1k_list else None
    avg_completion = sum(completion_list) / len(completion_list) if completion_list else None
    avg_watch = sum(avg_watch_list) / len(avg_watch_list) if avg_watch_list else None

    a, b, cc, d, e, f = st.columns(6)
    a.metric("Views", f"{int(total_views):,}".replace(",", "."))
    b.metric("Profile CTR", f"{profile_ctr*100:.2f}%")
    cc.metric("Engagement", f"{er*100:.2f}%")
    d.metric("Shares / 1K", f"{shares_per_1k:.2f}")

    e.metric("Follow / 1K", "-" if avg_follow_per_1k is None else f"{avg_follow_per_1k:.2f}")
    f.metric("Completion %", "-" if avg_completion is None else f"{avg_completion:.1f}")

    st.divider()
    st.subheader("Bu dönem aksiyonları (ilk sürüm)")
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

def page_content():
    st.title("İçerik")
    df = list_videos_from_content(period)
    if df.empty:
        st.info("Bu dönem için Content yok. Ayarlar’dan yükle.")
        return

    # Filters
    with st.expander("Filtreler", expanded=False):
        min_views = st.number_input("Min Views", value=0)
        sort_by = st.selectbox("Sırala", ["score (SS varsa)", "views", "er", "shares_per_1k"], index=1)

    # Compute scores using saved SS metrics
    scores = []
    for _, row in df.iterrows():
        vs = load_video_state(row["video_id"])
        scores.append(compute_growth_score(row, vs))
    s = pd.DataFrame(scores)
    df2 = pd.concat([df.reset_index(drop=True), s.reset_index(drop=True)], axis=1)

    df2 = df2[df2["views"].fillna(0) >= min_views].copy()

    if sort_by.startswith("score"):
        df2 = df2.sort_values("score", ascending=False)
    else:
        df2 = df2.sort_values(sort_by, ascending=False)

    st.caption("Satıra tıkla → video sayfası (SS yükleme orada).")

    # show table
    show = df2[["title","date","views","er","shares_per_1k","retention","follow_per_1k","score","video_id"]].copy()
    st.dataframe(show, use_container_width=True, hide_index=True)

    # Video selector
    st.subheader("Video Detay")
    pick = st.selectbox("Bir video seç", df2["video_id"].tolist(), format_func=lambda vid: df2.loc[df2["video_id"]==vid,"title"].iloc[0])
    if pick:
        st.session_state["selected_video_id"] = pick
        st.success("Seçildi. Aşağıdaki Video Detay sayfasına geç.")

def page_video_detail():
    vid = st.session_state.get("selected_video_id")
    if not vid:
        st.info("Önce İçerik sayfasından bir video seç.")
        return

    st.title("Video Detayı")
    state = load_video_state(vid)

    # Header controls
    left, right = st.columns([3, 2])
    with left:
        st.write(f"**Video ID:** `{vid}`")
    with right:
        st.write("")

    st.subheader("SS Yükle (bu videoya özel)")
    ss_files = st.file_uploader("Analytics SS (birden fazla seçebilirsin)", type=["png","jpg","jpeg","webp"], accept_multiple_files=True)
    if ss_files:
        saved = save_screenshots(vid, ss_files)
        st.success(f"{len(saved)} dosya kaydedildi.")

    shots = list_screenshots(vid)
    if shots:
        with st.expander("Yüklenen SS’ler", expanded=False):
            for p in shots[-8:]:
                st.image(p, use_column_width=True)

    st.divider()
    st.subheader("Retention / Conversion metrikleri (SS’den gir)")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        state["duration_sec"] = st.number_input("Video süresi (sn)", value=state["duration_sec"] or 0, min_value=0, step=1)
    with c2:
        state["avg_watch_sec"] = st.number_input("Avg watch (sn)", value=state["avg_watch_sec"] or 0.0, min_value=0.0, step=0.1)
    with c3:
        state["completion_pct"] = st.number_input("Completion %", value=state["completion_pct"] or 0.0, min_value=0.0, max_value=100.0, step=0.1)
    with c4:
        state["followers_gained"] = st.number_input("Followers gained", value=state["followers_gained"] or 0, min_value=0, step=1)

    state["notes"] = st.text_area("Notlar", value=state.get("notes",""), height=120)

    if st.button("Kaydet"):
        # Normalize zeros to None for cleanliness
        if state["duration_sec"] == 0: state["duration_sec"] = None
        if state["avg_watch_sec"] == 0: state["avg_watch_sec"] = None
        if state["completion_pct"] == 0: state["completion_pct"] = None
        if state["followers_gained"] == 0: state["followers_gained"] = None
        save_video_state(vid, state)
        st.success("Kaydedildi.")

    st.divider()
    st.subheader("Otomatik ilk teşhis (kural tabanlı)")
    # We need row context from content
    df = list_videos_from_content(period)
    row = df[df["video_id"]==vid].iloc[0].to_dict() if not df.empty else {"views": None, "er": 0.0, "shares_per_1k": 0.0}
    res = compute_growth_score(row, state)

    colA, colB, colC = st.columns(3)
    colA.metric("Score", f"{res['score']:.1f}")
    colB.metric("Retention", "-" if res["retention"] is None else f"{res['retention']*100:.1f}%")
    colC.metric("Follow / 1K", "-" if res["follow_per_1k"] is None else f"{res['follow_per_1k']:.2f}")

    verdicts = []
    if res["retention"] is not None and res["retention"] < 0.35:
        verdicts.append("Hook/tempo tırt: izleyici videoda kalmıyor. İlk 2 saniyeyi sertleştir.")
    if state.get("completion_pct") is not None and float(state["completion_pct"]) < 20:
        verdicts.append("Completion düşük: video gereksiz uzuyor veya payoff geç geliyor.")
    if row.get("shares_per_1k", 0) < 3:
        verdicts.append("Paylaşım zayıf: bilgi içeriğini ‘kopyala-yapıştır değer’ gibi paketle, daha keskin başlık.")
    if not verdicts:
        verdicts.append("Sinyaller fena değil: aynı formatı 3 varyasyonla tekrar dene (hook değiştir, tempo sabit).")

    for v in verdicts:
        st.write("• " + v)

def page_viewers():
    st.title("İzleyiciler")
    df = read_csv_safe(export_path(period, "viewers"))
    if df is None or df.empty:
        st.info("Bu dönem için Viewers yok. Ayarlar’dan yükle.")
        return
    st.dataframe(df, use_container_width=True)

def page_followers():
    st.title("Takipçiler")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Follower History")
        df = read_csv_safe(export_path(period, "follower_history"))
        if df is None or df.empty:
            st.info("FollowerHistory yok.")
        else:
            st.dataframe(df, use_container_width=True)
    with c2:
        st.subheader("Follower Activity")
        df = read_csv_safe(export_path(period, "follower_activity"))
        if df is None or df.empty:
            st.info("FollowerActivity yok.")
        else:
            st.dataframe(df, use_container_width=True)

    st.subheader("Gender / Territories")
    g1, g2 = st.columns(2)
    with g1:
        df = read_csv_safe(export_path(period, "follower_gender"))
        if df is None or df.empty:
            st.info("FollowerGender yok.")
        else:
            st.dataframe(df, use_container_width=True)
    with g2:
        df = read_csv_safe(export_path(period, "follower_top_territories"))
        if df is None or df.empty:
            st.info("FollowerTopTerritories yok.")
        else:
            st.dataframe(df, use_container_width=True)

# Router
if page == "Ayarlar":
    page_settings()
elif page == "Genel Bakış":
    page_overview()
elif page == "Growth Cockpit":
    page_growth_cockpit()
elif page == "İçerik":
    page_content()
    st.divider()
    st.subheader("Video sayfası")
    page_video_detail()
elif page == "İzleyiciler":
    page_viewers()
elif page == "Takipçiler":
    page_followers()
