"""
FILMYNGINE — Cinematic Movie Discovery Platform
A premium cyberpunk-inspired Streamlit frontend for an existing FastAPI backend.

Backend endpoints (unchanged):
  GET /home?category={trending|popular|top_rated|upcoming|now_playing}
  GET /tmdb/search?query=...
  GET /movie/id/{tmdb_id}
  GET /movie/search?query=...&tfidf_top_n=...&genre_limit=...
  GET /recommend/genre?tmdb_id=...&limit=...
  GET /recommend/tfidf?query=...&top_n=...
"""

import html
import random
import urllib.parse
import requests
import streamlit as st

# =============================================================
# MARKDOWN-INDENT FIX
# -------------------------------------------------------------
# Every HTML string in this file is written as a pretty, indented
# multi-line f-string (for readability). Streamlit's st.markdown()
# runs text through a Markdown parser BEFORE inserting raw HTML, and
# Markdown treats any line indented with 4+ spaces as an "indented
# code block" — it renders that line (and what follows) as plain,
# tiny, syntax-highlighted text instead of live HTML. That's exactly
# why cards were showing as raw "<img class=..." text with a tiny
# font and no images.
#
# Fix: wrap st.markdown so every line has its leading whitespace
# stripped before Streamlit ever sees it. This only changes the
# *source* indentation — browsers don't care how HTML source is
# indented — so nothing about the actual visual layout changes.
# =============================================================
_original_markdown = st.markdown


def _st_markdown_no_indent(body, *args, **kwargs):
    if isinstance(body, str):
        body = "\n".join(line.lstrip() for line in body.split("\n"))
    return _original_markdown(body, *args, **kwargs)


st.markdown = _st_markdown_no_indent

# =============================================================
# CONFIG
# =============================================================
API_BASE = "https://movie-rec-466x.onrender.com"
TMDB_IMG_W500 = "https://image.tmdb.org/t/p/w500"
TMDB_IMG_ORIG = "https://image.tmdb.org/t/p/original"
TMDB_MOVIE_URL = "https://www.themoviedb.org/movie"

CATEGORIES = [
    ("trending",    "Trending Now"),
    ("popular",     "Popular Movies"),
    ("top_rated",   "Top Rated"),
    ("upcoming",    "Upcoming"),
    ("now_playing", "Now Playing"),
]

GENRE_SEEDS = [
    "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary",
    "Drama", "Family", "Fantasy", "History", "Horror", "Music", "Mystery",
    "Romance", "Science Fiction", "Thriller", "War", "Western",
]

st.set_page_config(
    page_title="FILMYNGINE — Cinematic Discovery",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================
# GLOBAL CSS  —  Cyberpunk / Sci-Fi / Premium streaming aesthetic
# =============================================================
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Audiowide&family=Chakra+Petch:wght@300;400;500;600;700&family=Barlow:wght@300;400;500;600;700&display=swap');

:root{
    --bg-0:#050509;
    --bg-1:#0b0b14;
    --bg-2:#12121e;
    --graphite:#1a1a26;
    --line:rgba(255,255,255,0.06);
    --text:#e9e9f2;
    --muted:#8a8aa3;
    --cyan:#00e5ff;
    --purple:#b14bff;
    --magenta:#ff2fd0;
    --blue:#3d5afe;
    --gold:#ffd166;
    --glow-cyan:0 0 24px rgba(0,229,255,0.55);
    --glow-mag:0 0 24px rgba(255,47,208,0.45);
}

html, body, [data-testid="stAppViewContainer"]{
    background: radial-gradient(1200px 700px at 12% -10%, rgba(61,90,254,0.18), transparent 55%),
                radial-gradient(900px 600px at 100% 0%, rgba(255,47,208,0.12), transparent 55%),
                radial-gradient(1000px 800px at 50% 120%, rgba(0,229,255,0.10), transparent 60%),
                var(--bg-0) !important;
    color:var(--text);
    font-family:'Barlow', system-ui, sans-serif;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header {visibility:hidden; height:0;}
[data-testid="stToolbar"]{display:none;}
[data-testid="stDecoration"]{display:none;}
.block-container{padding-top:0.5rem !important; padding-bottom:4rem; max-width:1500px;}

/* Sidebar */
[data-testid="stSidebar"]{
    background: linear-gradient(180deg, #08080f 0%, #0a0a14 100%) !important;
    border-right:1px solid var(--line);
}
[data-testid="stSidebar"] * { color: var(--text) !important; font-family:'Chakra Petch', sans-serif;}
[data-testid="stSidebar"] .stButton>button{
    width:100%;
    background: rgba(255,255,255,0.03);
    color: var(--text) !important;
    border:1px solid var(--line);
    border-radius:14px;
    padding:10px 14px;
    text-align:left;
    font-family:'Chakra Petch', sans-serif;
    font-weight:500;
    letter-spacing:.5px;
    transition: all .25s ease;
}
[data-testid="stSidebar"] .stButton>button:hover{
    border-color: var(--cyan);
    background: rgba(0,229,255,0.06);
    color: var(--cyan) !important;
    box-shadow: var(--glow-cyan);
    transform: translateX(2px);
}

/* Typography */
h1, h2, h3, h4 { font-family:'Chakra Petch', sans-serif !important; letter-spacing:.5px; color:var(--text); }
h1 { font-weight:700; }
p, span, div, label { color: var(--text); }

/* Brand logo */
.brand{
    font-family:'Audiowide', sans-serif;
    font-size: 28px;
    letter-spacing: 4px;
    background: linear-gradient(90deg, #00e5ff 0%, #b14bff 50%, #ff2fd0 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 0 30px rgba(0,229,255,0.35);
}
.brand-sub{
    font-family:'Chakra Petch', sans-serif;
    color: var(--muted);
    font-size: 11px;
    letter-spacing: 6px;
    text-transform: uppercase;
    margin-top:-4px;
}

/* HERO */
.hero-wrap{
    position:relative;
    border-radius:22px;
    overflow:hidden;
    margin: 14px 0 30px 0;
    min-height: 460px;
    border: 1px solid var(--line);
    box-shadow: 0 30px 80px rgba(0,0,0,0.55), inset 0 0 0 1px rgba(255,255,255,0.03);
}
.hero-bg{
    position:absolute; inset:0;
    background-size: cover;
    background-position: center;
    filter: saturate(1.05) contrast(1.02);
    transform: scale(1.03);
    transition: transform 6s ease;
}
.hero-wrap:hover .hero-bg{ transform: scale(1.06); }
.hero-scrim{
    position:absolute; inset:0;
    background:
        linear-gradient(90deg, rgba(5,5,9,0.92) 0%, rgba(5,5,9,0.55) 45%, rgba(5,5,9,0.05) 80%),
        linear-gradient(0deg, rgba(5,5,9,0.95) 0%, rgba(5,5,9,0.15) 60%, transparent 100%);
}
.hero-grain{
    position:absolute; inset:0;
    opacity:.22;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence baseFrequency='0.85' numOctaves='2' seed='7'/></filter><rect width='100%' height='100%' filter='url(%23n)' opacity='0.55'/></svg>");
    mix-blend-mode: overlay;
    pointer-events:none;
}
.hero-content{
    position:relative;
    padding: 60px 60px 44px 60px;
    max-width: 780px;
}
.hero-eyebrow{
    display:inline-flex; align-items:center; gap:8px;
    font-family:'Chakra Petch', sans-serif;
    font-size:12px; letter-spacing:5px; text-transform:uppercase;
    color: var(--cyan);
    padding: 6px 12px;
    border:1px solid rgba(0,229,255,0.35);
    border-radius:999px;
    background: rgba(0,229,255,0.06);
    backdrop-filter: blur(8px);
}
.hero-title{
    font-family:'Chakra Petch', sans-serif;
    font-weight:700;
    font-size: clamp(38px, 5.4vw, 72px);
    line-height:1.02;
    margin: 16px 0 10px 0;
    color: #fff;
    text-shadow: 0 4px 40px rgba(0,0,0,0.6);
}
.hero-meta{
    display:flex; flex-wrap:wrap; gap:10px; align-items:center;
    margin-bottom: 14px;
    color: var(--muted);
    font-family:'Chakra Petch', sans-serif;
    font-size:14px; letter-spacing:1.5px;
}
.chip{
    display:inline-flex; align-items:center; gap:6px;
    padding:5px 12px; border-radius:999px;
    background: rgba(255,255,255,0.05);
    border:1px solid var(--line);
    color: var(--text);
    font-size:12px; letter-spacing:1px;
    backdrop-filter: blur(6px);
}
.chip.rating{ border-color: rgba(255,209,102,0.5); color: var(--gold); background: rgba(255,209,102,0.08);}
.chip.year  { border-color: rgba(0,229,255,0.4); color: var(--cyan); background: rgba(0,229,255,0.06);}

.hero-desc{
    color: #d6d6e5;
    font-size: 16px;
    line-height:1.55;
    max-width: 620px;
    margin: 8px 0 22px 0;
    text-shadow: 0 2px 20px rgba(0,0,0,0.5);
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
.hero-cta{ display:flex; gap:12px; flex-wrap:wrap;}
.btn{
    display:inline-flex; align-items:center; gap:8px;
    padding: 12px 22px;
    border-radius: 999px;
    font-family:'Chakra Petch', sans-serif;
    font-weight:600;
    letter-spacing:1.5px;
    text-transform:uppercase;
    font-size:13px;
    text-decoration:none !important;
    border:1px solid transparent;
    transition: all .25s ease;
    cursor:pointer;
}
.btn-primary{
    background: linear-gradient(90deg, #00e5ff 0%, #3d5afe 100%);
    color: #04040a !important;
    box-shadow: 0 10px 30px rgba(0,229,255,0.35);
}
.btn-primary:hover{ transform: translateY(-2px); box-shadow: 0 14px 40px rgba(0,229,255,0.55);}
.btn-ghost{
    background: rgba(255,255,255,0.04);
    color: #fff !important;
    border:1px solid rgba(255,255,255,0.15);
    backdrop-filter: blur(10px);
}
.btn-ghost:hover{
    border-color: var(--magenta);
    color: var(--magenta) !important;
    box-shadow: var(--glow-mag);
}

/* SECTION HEADERS */
.section-head{
    display:flex; align-items:flex-end; justify-content:space-between;
    margin: 34px 4px 14px 4px;
}
.section-title{
    font-family:'Chakra Petch', sans-serif;
    font-weight:600;
    font-size: 24px;
    letter-spacing:1.5px;
    color:#fff;
    display:flex; align-items:center; gap:12px;
}
.section-title:before{
    content:"";
    width:6px; height:26px; border-radius:2px;
    background: linear-gradient(180deg, var(--cyan), var(--magenta));
    box-shadow: var(--glow-cyan);
}
.section-sub{ color: var(--muted); font-size:12px; letter-spacing:3px; text-transform:uppercase;}

/* CAROUSEL */
.carousel{
    display:flex; gap:16px;
    overflow-x:auto; overflow-y:visible;
    padding: 10px 4px 26px 4px;
    scroll-snap-type: x mandatory;
    scrollbar-width: thin;
    scrollbar-color: rgba(0,229,255,0.35) transparent;
}
.carousel::-webkit-scrollbar{ height:8px;}
.carousel::-webkit-scrollbar-thumb{
    background: linear-gradient(90deg, rgba(0,229,255,0.5), rgba(255,47,208,0.5));
    border-radius:999px;
}
.carousel::-webkit-scrollbar-track{ background: transparent;}

.card{
    flex: 0 0 auto;
    width: 190px;
    scroll-snap-align: start;
    text-decoration:none !important;
    position:relative;
    transition: transform .35s cubic-bezier(.2,.7,.2,1);
}
.card:hover{ transform: translateY(-6px) scale(1.03); z-index:5;}
.poster-wrap{
    position:relative;
    border-radius:14px;
    overflow:hidden;
    aspect-ratio: 2/3;
    background: linear-gradient(180deg, #14141f, #08080f);
    border:1px solid var(--line);
    box-shadow: 0 12px 30px rgba(0,0,0,0.5);
    transition: box-shadow .3s ease, border-color .3s ease;
}
.card:hover .poster-wrap{
    border-color: rgba(0,229,255,0.55);
    box-shadow: 0 18px 50px rgba(0,229,255,0.25), var(--glow-cyan);
}
.poster-img{
    width:100%; height:100%; object-fit:cover; display:block;
    transition: transform .5s ease;
}
.card:hover .poster-img{ transform: scale(1.08); }
.poster-noimg{
    width:100%; height:100%;
    display:flex; align-items:center; justify-content:center;
    color: var(--muted); font-family:'Chakra Petch', sans-serif; letter-spacing:2px;
}
.poster-scrim{
    position:absolute; inset:0;
    background: linear-gradient(180deg, transparent 55%, rgba(5,5,9,0.95) 100%);
    opacity:0; transition: opacity .3s ease;
}
.card:hover .poster-scrim{ opacity:1;}
.poster-play{
    position:absolute; inset:0;
    display:flex; align-items:center; justify-content:center;
    opacity:0; transition: opacity .3s ease;
}
.card:hover .poster-play{ opacity:1;}
.play-dot{
    width:52px; height:52px; border-radius:50%;
    background: rgba(0,229,255,0.15);
    border:1px solid var(--cyan);
    display:flex; align-items:center; justify-content:center;
    color: var(--cyan);
    font-size:20px;
    backdrop-filter: blur(8px);
    box-shadow: var(--glow-cyan);
}
.card-title{
    margin-top:10px;
    color:#fff;
    font-family:'Chakra Petch', sans-serif;
    font-weight:500;
    font-size:14px;
    letter-spacing:.4px;
    line-height:1.25;
    display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;
}
.card-sub{
    color: var(--muted);
    font-size:11px;
    letter-spacing:2px;
    text-transform:uppercase;
    margin-top:2px;
}

/* SIMILARITY BADGE */
.sim-badge{
    position:absolute; top:10px; left:10px;
    padding: 4px 10px;
    border-radius: 999px;
    font-family:'Chakra Petch', sans-serif;
    font-weight:700;
    font-size:11px;
    letter-spacing:1.5px;
    color: #04040a;
    background: linear-gradient(90deg, var(--cyan), var(--magenta));
    box-shadow: var(--glow-cyan);
    z-index:2;
}
.wl-badge{
    position:absolute; top:10px; right:10px;
    width:28px; height:28px; border-radius:50%;
    background: rgba(0,0,0,0.55);
    border:1px solid rgba(255,255,255,0.15);
    display:flex; align-items:center; justify-content:center;
    color: var(--magenta);
    font-size:14px;
    backdrop-filter: blur(6px);
    z-index:2;
}

/* SEARCH BAR */
.search-shell{
    position:relative;
    margin: 6px 0 8px 0;
}
[data-testid="stTextInput"] > div > div > input{
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(0,229,255,0.25) !important;
    border-radius: 14px !important;
    color: #fff !important;
    font-family: 'Chakra Petch', sans-serif !important;
    font-size: 16px !important;
    letter-spacing:.5px;
    padding: 14px 18px !important;
    backdrop-filter: blur(10px);
    transition: all .25s ease;
}
[data-testid="stTextInput"] > div > div > input:focus{
    border-color: var(--cyan) !important;
    box-shadow: 0 0 0 3px rgba(0,229,255,0.15), var(--glow-cyan) !important;
    background: rgba(0,229,255,0.05) !important;
}
[data-testid="stTextInput"] label{ color: var(--muted) !important; font-family:'Chakra Petch',sans-serif !important; letter-spacing:3px; text-transform:uppercase; font-size:11px !important;}

/* Selectbox */
[data-baseweb="select"] > div{
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid var(--line) !important;
    border-radius:12px !important;
    color:#fff !important;
}
[data-baseweb="select"] * { color: #fff !important; }

/* Details */
.details-hero{
    position:relative;
    border-radius: 22px;
    overflow:hidden;
    min-height: 520px;
    border:1px solid var(--line);
    margin-bottom: 24px;
}
.details-poster{
    border-radius:16px;
    overflow:hidden;
    border:1px solid var(--line);
    box-shadow: 0 30px 60px rgba(0,0,0,0.6), 0 0 60px rgba(0,229,255,0.12);
    aspect-ratio: 2/3;
    background:#0a0a14;
}
.details-poster img{ width:100%; height:100%; object-fit:cover; display:block;}
.details-title{
    font-family:'Chakra Petch', sans-serif;
    font-size: clamp(32px, 4vw, 56px);
    font-weight:700;
    line-height:1.02;
    color:#fff;
    margin-bottom:14px;
}
.rating-ring{
    display:inline-flex; align-items:center; gap:10px;
    padding: 6px 16px;
    border-radius: 999px;
    background: rgba(255,209,102,0.08);
    border:1px solid rgba(255,209,102,0.5);
    color: var(--gold);
    font-family:'Chakra Petch',sans-serif;
    font-weight:600;
    letter-spacing:1.5px;
    font-size:14px;
}

/* Empty state */
.empty{
    padding: 40px 20px;
    text-align:center;
    color: var(--muted);
    border:1px dashed var(--line);
    border-radius: 14px;
    background: rgba(255,255,255,0.02);
    font-family:'Chakra Petch',sans-serif;
    letter-spacing:2px;
    text-transform:uppercase;
    font-size:12px;
}

/* Genre chips */
.genre-row{ display:flex; flex-wrap:wrap; gap:10px; margin: 6px 0 14px 0;}
.gchip{
    padding: 8px 16px;
    border-radius: 999px;
    background: rgba(255,255,255,0.04);
    border:1px solid var(--line);
    color: #d6d6e5;
    font-family:'Chakra Petch',sans-serif;
    font-size:12px;
    letter-spacing:2px;
    text-transform:uppercase;
    text-decoration:none !important;
    transition: all .2s ease;
}
.gchip:hover{
    border-color: var(--magenta);
    color: var(--magenta);
    background: rgba(255,47,208,0.06);
    box-shadow: var(--glow-mag);
    transform: translateY(-2px);
}
.gchip.active{
    background: linear-gradient(90deg, rgba(0,229,255,0.15), rgba(255,47,208,0.15));
    border-color: var(--cyan);
    color: var(--cyan);
    box-shadow: var(--glow-cyan);
}

/* Loading skeleton */
.skeleton{
    display:flex; gap:16px; overflow:hidden; padding: 10px 4px;
}
.sk-card{
    flex:0 0 auto; width:190px; aspect-ratio:2/3;
    background: linear-gradient(90deg, #0f0f19 0%, #16162a 50%, #0f0f19 100%);
    background-size: 200% 100%;
    animation: shimmer 1.4s infinite linear;
    border-radius:14px;
}
@keyframes shimmer{ 0%{background-position: 200% 0;} 100%{background-position:-200% 0;} }

/* Fade-in for content */
.fade-in{ animation: fadeIn .6s ease both; }
@keyframes fadeIn{ from{ opacity:0; transform: translateY(8px);} to{ opacity:1; transform:none;} }

/* Divider */
hr, [data-testid="stDivider"] { border-color: var(--line) !important; opacity:.6;}

/* Buttons (Streamlit) */
.stButton>button{
    background: rgba(255,255,255,0.04);
    color:#fff;
    border:1px solid var(--line);
    border-radius:12px;
    font-family:'Chakra Petch',sans-serif;
    letter-spacing:1px;
    transition: all .2s ease;
}
.stButton>button:hover{
    border-color: var(--cyan);
    color: var(--cyan);
    box-shadow: var(--glow-cyan);
}

/* Alerts */
.stAlert{ background: rgba(255,255,255,0.03) !important; border:1px solid var(--line) !important; color: var(--text) !important; border-radius:12px !important;}

/* Recent search chips */
.recent-row{ display:flex; flex-wrap:wrap; gap:8px; margin: 6px 0 0 0;}
.rchip{
    padding: 5px 12px;
    font-size:11px; letter-spacing:1.5px; text-transform:uppercase;
    color: var(--muted);
    background: rgba(255,255,255,0.03);
    border:1px solid var(--line);
    border-radius:999px;
    font-family:'Chakra Petch',sans-serif;
    text-decoration:none !important;
    transition: all .2s ease;
}
.rchip:hover{ color: var(--cyan); border-color: rgba(0,229,255,0.35); }

/* Suggestions dropdown */
.sugg-box{
    background: rgba(10,10,20,0.85);
    border:1px solid rgba(0,229,255,0.25);
    backdrop-filter: blur(14px);
    border-radius: 14px;
    padding: 6px;
    margin-top: 6px;
    box-shadow: 0 20px 50px rgba(0,0,0,0.6);
}
.sugg-item{
    display:flex; align-items:center; gap:12px;
    padding: 8px 10px;
    border-radius: 10px;
    color: #d6d6e5 !important;
    text-decoration:none !important;
    font-family:'Chakra Petch',sans-serif;
    font-size:14px;
    letter-spacing:.4px;
    transition: all .15s ease;
}
.sugg-item:hover{ background: rgba(0,229,255,0.08); color: var(--cyan) !important;}
.sugg-thumb{
    width:38px; height:56px; border-radius:6px; object-fit:cover; flex:0 0 auto;
    background:#0a0a14;
}
.sugg-year{ color: var(--muted); font-size:11px; letter-spacing:2px; margin-left:auto;}

/* Watchlist tab-like nav */
.tabline{
    display:flex; gap:6px; margin: 6px 0 16px 0;
    border-bottom: 1px solid var(--line);
}
.tabline a{
    padding: 10px 18px;
    color: var(--muted);
    text-decoration:none;
    font-family:'Chakra Petch',sans-serif;
    letter-spacing:2px;
    text-transform:uppercase;
    font-size:12px;
    border-bottom: 2px solid transparent;
    transition: all .2s ease;
}
.tabline a:hover{ color:#fff;}
.tabline a.active{ color: var(--cyan); border-bottom-color: var(--cyan);}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# =============================================================
# SESSION STATE
# =============================================================
def _init_state():
    defaults = {
        "watchlist": {},          # tmdb_id -> card dict
        "favorites": {},
        "recently_viewed": [],    # list of card dicts (most recent first)
        "search_history": [],     # list of strings (most recent first, unique)
        "active_genre": None,
        "hero_pick": None,        # cached hero movie tmdb id
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# =============================================================
# ROUTING (via query params)
# =============================================================
def _get_qp(key, default=None):
    v = st.query_params.get(key)
    if isinstance(v, list):
        v = v[0] if v else None
    return v if v is not None else default

view = _get_qp("view", "home")
qp_id = _get_qp("id")
qp_action = _get_qp("action")
qp_query = _get_qp("q")
qp_genre = _get_qp("genre")

# Handle actions (add/remove watchlist/favorite) via query params
def _consume_action():
    if not qp_action or not qp_id:
        return
    try:
        tid = int(qp_id)
    except Exception:
        return
    # We need card metadata; store minimal from qp
    title = _get_qp("t") or f"#{tid}"
    poster = _get_qp("p") or ""
    card = {"tmdb_id": tid, "title": title, "poster_url": poster or None}

    if qp_action == "wl_add":
        st.session_state.watchlist[tid] = card
    elif qp_action == "wl_rm":
        st.session_state.watchlist.pop(tid, None)
    elif qp_action == "fav_add":
        st.session_state.favorites[tid] = card
    elif qp_action == "fav_rm":
        st.session_state.favorites.pop(tid, None)
    elif qp_action == "hist_clear":
        st.session_state.search_history = []
    elif qp_action == "recent_clear":
        st.session_state.recently_viewed = []

    # Clean action from URL to prevent replay
    for k in ("action", "t", "p"):
        if k in st.query_params:
            del st.query_params[k]

_consume_action()

# =============================================================
# API HELPERS
# =============================================================
@st.cache_data(ttl=300, show_spinner=False)
def api_get(path: str, params: tuple = ()):
    """params passed as tuple of (k,v) for hashability."""
    try:
        p = dict(params) if params else None
        r = requests.get(f"{API_BASE}{path}", params=p, timeout=25)
        if r.status_code >= 400:
            return None, f"HTTP {r.status_code}"
        return r.json(), None
    except Exception as e:
        return None, str(e)

def _params(d: dict):
    return tuple(sorted((k, str(v)) for k, v in d.items() if v is not None))

# ---- Normalizers ------------------------------------------------
def norm_card(m: dict) -> dict:
    """Normalize any backend movie shape → card."""
    if not isinstance(m, dict):
        return {}
    tmdb_id = m.get("tmdb_id") or m.get("id")
    if not tmdb_id:
        return {}
    title = (m.get("title") or m.get("name") or "Untitled").strip()
    poster = m.get("poster_url")
    if not poster:
        pp = m.get("poster_path")
        if pp:
            poster = f"{TMDB_IMG_W500}{pp}"
    backdrop = m.get("backdrop_url")
    if not backdrop:
        bp = m.get("backdrop_path")
        if bp:
            backdrop = f"{TMDB_IMG_ORIG}{bp}"
    rating = m.get("vote_average") or m.get("rating")
    return {
        "tmdb_id": int(tmdb_id),
        "title": title,
        "poster_url": poster,
        "backdrop_url": backdrop,
        "release_date": m.get("release_date") or "",
        "overview": m.get("overview") or "",
        "rating": float(rating) if rating not in (None, "") else None,
        "genres": m.get("genres") or [],
    }

def cards_from_any(data):
    """Handle multiple shapes → list of cards."""
    if not data:
        return []
    if isinstance(data, dict):
        if "results" in data:
            return [c for c in (norm_card(x) for x in data["results"]) if c]
        if "tfidf_recommendations" in data:
            out = []
            for x in data["tfidf_recommendations"] or []:
                tmdb = x.get("tmdb") or {}
                c = norm_card(tmdb)
                if c:
                    if x.get("score") is not None:
                        c["score"] = float(x["score"])
                    out.append(c)
            return out
        return []
    if isinstance(data, list):
        return [c for c in (norm_card(x) for x in data) if c]
    return []

# =============================================================
# UI HELPERS
# =============================================================
def _e(s):  # html escape
    return html.escape(s or "", quote=True)

def _url(**params):
    """Build a same-page URL with merged query params."""
    q = {**{k: v for k, v in st.query_params.items()}, **params}
    # Flatten list values
    flat = {}
    for k, v in q.items():
        if isinstance(v, list):
            flat[k] = v[0] if v else ""
        else:
            flat[k] = v
    # Remove empty
    flat = {k: v for k, v in flat.items() if v not in (None, "")}
    return "?" + urllib.parse.urlencode(flat, safe=":/")

def details_url(tmdb_id):
    return "?" + urllib.parse.urlencode({"view": "details", "id": tmdb_id})

def action_url(action: str, card: dict, back_view: str = None):
    p = {
        "action": action,
        "id": card.get("tmdb_id"),
        "t": (card.get("title") or "")[:120],
        "p": card.get("poster_url") or "",
        "view": back_view or view,
    }
    if back_view == "details":
        p["id"] = card.get("tmdb_id")  # keep same
    return "?" + urllib.parse.urlencode({k: v for k, v in p.items() if v not in (None, "")}, safe=":/")

def card_html(card: dict, show_score: bool = False) -> str:
    if not card or not card.get("tmdb_id"):
        return ""
    tid = card["tmdb_id"]
    title = _e(card.get("title") or "Untitled")
    poster = card.get("poster_url")
    year = (card.get("release_date") or "")[:4]

    in_wl = tid in st.session_state.watchlist
    wl_html = f'<div class="wl-badge" title="In Watchlist">♥</div>' if in_wl else ""

    score_html = ""
    if show_score and card.get("score") is not None:
        pct = int(round(min(max(card["score"], 0), 1) * 100))
        score_html = f'<div class="sim-badge">◈ {pct}% MATCH</div>'

    if poster:
        img = f'<img class="poster-img" src="{_e(poster)}" alt="{title}" loading="lazy"/>'
    else:
        img = f'<div class="poster-noimg">NO POSTER</div>'

    return f"""
    <a class="card" href="{details_url(tid)}" target="_self" title="{title}">
      <div class="poster-wrap">
        {score_html}
        {wl_html}
        {img}
        <div class="poster-scrim"></div>
        <div class="poster-play"><div class="play-dot">▶</div></div>
      </div>
      <div class="card-title">{title}</div>
      <div class="card-sub">{_e(year) if year else "—"}</div>
    </a>
    """

def carousel(cards, section_id: str, show_score: bool = False, empty_msg="No titles here yet."):
    cards = [c for c in cards if c and c.get("tmdb_id")]
    if not cards:
        st.markdown(f'<div class="empty">{_e(empty_msg)}</div>', unsafe_allow_html=True)
        return
    inner = "".join(card_html(c, show_score=show_score) for c in cards)
    st.markdown(f'<div class="carousel fade-in" id="car-{section_id}">{inner}</div>', unsafe_allow_html=True)

def grid(cards, cols=6, show_score: bool = False, empty_msg="Nothing to show."):
    cards = [c for c in cards if c and c.get("tmdb_id")]
    if not cards:
        st.markdown(f'<div class="empty">{_e(empty_msg)}</div>', unsafe_allow_html=True)
        return
    # Custom flex grid (looks better than st.columns for uniformity)
    html_cards = "".join(card_html(c, show_score=show_score) for c in cards)
    st.markdown(
        f'<div class="carousel fade-in" style="flex-wrap:wrap; overflow:visible; scroll-snap-type:none;">{html_cards}</div>',
        unsafe_allow_html=True,
    )

def section_header(title: str, subtitle: str = ""):
    st.markdown(
        f'''
        <div class="section-head">
          <div class="section-title">{_e(title)}</div>
          <div class="section-sub">{_e(subtitle)}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

def record_recent(card: dict):
    if not card or not card.get("tmdb_id"):
        return
    tid = card["tmdb_id"]
    lst = [c for c in st.session_state.recently_viewed if c.get("tmdb_id") != tid]
    lst.insert(0, {
        "tmdb_id": tid,
        "title": card.get("title"),
        "poster_url": card.get("poster_url"),
    })
    st.session_state.recently_viewed = lst[:24]

def record_search(q: str):
    q = (q or "").strip()
    if not q:
        return
    lst = [s for s in st.session_state.search_history if s.lower() != q.lower()]
    lst.insert(0, q)
    st.session_state.search_history = lst[:10]

# =============================================================
# SIDEBAR — Navigation
# =============================================================
with st.sidebar:
    st.markdown('<div class="brand">FILMYNGINE</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-sub">Cinematic · Discovery</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    nav_items = [
        ("home",      "◉  HOME"),
        ("search",    "⌕  SEARCH"),
        ("genres",    "◆  GENRES"),
        ("watchlist", "♥  WATCHLIST"),
        ("favorites", "★  FAVORITES"),
        ("recent",    "↻  RECENTLY VIEWED"),
    ]
    for key, label in nav_items:
        if st.button(label, key=f"nav_{key}", use_container_width=True):
            st.query_params.clear()
            st.query_params["view"] = key
            st.rerun()

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="brand-sub">Session</div>', unsafe_allow_html=True)
    st.markdown(
        f'''<div style="color:#8a8aa3; font-family:'Chakra Petch',sans-serif; font-size:12px; letter-spacing:2px; margin-top:6px; line-height:1.9">
        ♥ Watchlist &nbsp;·&nbsp; <span style="color:#00e5ff">{len(st.session_state.watchlist)}</span><br>
        ★ Favorites &nbsp;·&nbsp; <span style="color:#ff2fd0">{len(st.session_state.favorites)}</span><br>
        ↻ Recent &nbsp;·&nbsp; <span style="color:#b14bff">{len(st.session_state.recently_viewed)}</span>
        </div>''',
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    st.caption("Powered by TMDB · Free forever")

# =============================================================
# TOP BRAND BAR
# =============================================================
st.markdown(
    '''
    <div style="display:flex; align-items:baseline; justify-content:space-between; margin: 4px 0 6px 0;">
      <div>
        <div class="brand" style="font-size:34px;">FILMYNGINE</div>
        <div class="brand-sub">The Cinema Engine · Cyberpunk Edition</div>
      </div>
      <div class="brand-sub" style="letter-spacing:5px;">v1.0 · NEURAL FEED</div>
    </div>
    ''',
    unsafe_allow_html=True,
)
st.markdown("<hr/>", unsafe_allow_html=True)

# =============================================================
# VIEW: HOME
# =============================================================
def render_hero(pick: dict):
    if not pick:
        return
    backdrop = pick.get("backdrop_url") or pick.get("poster_url") or ""
    title = _e(pick.get("title") or "Untitled")
    overview = _e((pick.get("overview") or "")[:400])
    year = (pick.get("release_date") or "")[:4]
    rating = pick.get("rating")
    rating_html = f'<span class="chip rating">★ {rating:.1f}</span>' if rating else ""
    year_html = f'<span class="chip year">{_e(year)}</span>' if year else ""

    tmdb_id = pick.get("tmdb_id")
    trailer_url = f"{TMDB_MOVIE_URL}/{tmdb_id}"
    add_wl = action_url("wl_add", pick, back_view="home")

    st.markdown(
        f'''
        <div class="hero-wrap fade-in">
          <div class="hero-bg" style="background-image: url('{_e(backdrop)}');"></div>
          <div class="hero-scrim"></div>
          <div class="hero-grain"></div>
          <div class="hero-content">
            <div class="hero-eyebrow">◈ Featured Tonight</div>
            <div class="hero-title">{title}</div>
            <div class="hero-meta">
              {rating_html}{year_html}
              <span class="chip">CINEMATIC</span>
            </div>
            <div class="hero-desc">{overview or "A cinematic experience awaits. Dive into the neural feed and discover what to watch next."}</div>
            <div class="hero-cta">
              <a class="btn btn-primary" href="{details_url(tmdb_id)}" target="_self">▶ View Details</a>
              <a class="btn btn-ghost" href="{trailer_url}" target="_blank">◈ Watch Trailer</a>
              <a class="btn btn-ghost" href="{add_wl}" target="_self">＋ Add to Watchlist</a>
            </div>
          </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

def render_home():
    # Fetch trending for hero + carousel first
    trending_raw, err_t = api_get("/home", _params({"category": "trending", "limit": 20}))
    trending_cards = cards_from_any(trending_raw)

    # Pick hero
    hero_pick = None
    if trending_cards:
        # Deterministic per session
        if not st.session_state.hero_pick or st.session_state.hero_pick not in [c["tmdb_id"] for c in trending_cards[:8]]:
            st.session_state.hero_pick = random.choice(trending_cards[:8])["tmdb_id"]
        for c in trending_cards:
            if c["tmdb_id"] == st.session_state.hero_pick:
                hero_pick = c
                break
        # Fetch full details to enrich hero (overview + backdrop)
        det, _ = api_get(f"/movie/id/{hero_pick['tmdb_id']}")
        if det:
            det_c = norm_card(det)
            for k in ("overview", "backdrop_url", "rating", "release_date"):
                if det_c.get(k):
                    hero_pick[k] = det_c[k]

    render_hero(hero_pick or {})

    # Quick search entry
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    q = st.text_input(
        "SEARCH THE ENGINE",
        placeholder="Type a movie title… e.g. Dune, Inception, Interstellar",
        key="home_search_input",
        label_visibility="visible",
    )
    if q and q.strip():
        record_search(q.strip())
        st.query_params.clear()
        st.query_params["view"] = "search"
        st.query_params["q"] = q.strip()
        st.rerun()

    # Recently viewed strip (if any)
    if st.session_state.recently_viewed:
        section_header("Continue Exploring", "Recently Viewed")
        carousel(st.session_state.recently_viewed, section_id="recent_home")

    # Category carousels
    for slug, label in CATEGORIES:
        if slug == "trending" and trending_cards:
            section_header(label, "TMDB · Live")
            carousel(trending_cards, section_id=slug)
            continue
        data, err = api_get("/home", _params({"category": slug, "limit": 20}))
        cards = cards_from_any(data)
        section_header(label, f"TMDB · {slug.replace('_',' ').title()}")
        if err:
            st.markdown(f'<div class="empty">Feed unavailable — {err}</div>', unsafe_allow_html=True)
        else:
            carousel(cards, section_id=slug)

    # Genre teaser
    section_header("Discover by Genre", "Neural Genre Map")
    chips_html = '<div class="genre-row">' + "".join(
        f'<a class="gchip" href="?view=genres&genre={urllib.parse.quote(g)}" target="_self">{_e(g)}</a>'
        for g in GENRE_SEEDS[:12]
    ) + '</div>'
    st.markdown(chips_html, unsafe_allow_html=True)

# =============================================================
# VIEW: SEARCH
# =============================================================
def render_search():
    st.markdown('<div class="brand-sub" style="letter-spacing:5px;">◍ NEURAL SEARCH</div>', unsafe_allow_html=True)
    st.markdown(
        '<h2 style="margin:6px 0 20px 0;">Find your next obsession</h2>',
        unsafe_allow_html=True,
    )

    default_q = qp_query or ""
    q = st.text_input(
        "QUERY",
        value=default_q,
        placeholder="Type at least 2 characters…",
        key="search_input",
    )
    q_stripped = (q or "").strip()

    # Recent searches
    if st.session_state.search_history:
        chips = "".join(
            f'<a class="rchip" href="?view=search&q={urllib.parse.quote(s)}" target="_self">↺ {_e(s)}</a>'
            for s in st.session_state.search_history
        )
        st.markdown(
            f'<div style="display:flex; align-items:center; gap:12px; margin-top:6px; flex-wrap:wrap;">'
            f'<span class="brand-sub">Recent</span>'
            f'<div class="recent-row">{chips}</div>'
            f'<a class="rchip" href="?view=search&action=hist_clear" target="_self" style="color:#ff2fd0;">✕ Clear</a>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if not q_stripped:
        st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
        st.markdown('<div class="empty">Start typing to summon the engine.</div>', unsafe_allow_html=True)
        # Show trending as inspiration
        data, _ = api_get("/home", _params({"category": "trending", "limit": 18}))
        cards = cards_from_any(data)
        section_header("Trending Right Now", "For Inspiration")
        carousel(cards, section_id="search_inspo")
        return

    if len(q_stripped) < 2:
        st.caption("Type at least 2 characters for suggestions.")
        return

    record_search(q_stripped)

    with st.spinner("Scanning cinematic index…"):
        data, err = api_get("/tmdb/search", _params({"query": q_stripped}))

    if err:
        st.error(f"Search failed: {err}")
        return

    cards = cards_from_any(data)
    if not cards:
        st.markdown('<div class="empty">No results. Try another keyword.</div>', unsafe_allow_html=True)
        return

    # Autocomplete-style suggestions (top 6)
    sugg_items = ""
    for c in cards[:6]:
        y = (c.get("release_date") or "")[:4]
        thumb = f'<img class="sugg-thumb" src="{_e(c["poster_url"])}"/>' if c.get("poster_url") else '<div class="sugg-thumb"></div>'
        sugg_items += f'''
        <a class="sugg-item" href="{details_url(c["tmdb_id"])}" target="_self">
          {thumb}
          <div>{_e(c["title"])}</div>
          <div class="sugg-year">{_e(y)}</div>
        </a>
        '''
    st.markdown(f'<div class="sugg-box">{sugg_items}</div>', unsafe_allow_html=True)

    section_header(f'Results for “{q_stripped}”', f"{len(cards)} titles")
    grid(cards)

# =============================================================
# VIEW: DETAILS
# =============================================================
def render_details():
    try:
        tmdb_id = int(qp_id)
    except Exception:
        st.error("Invalid movie id.")
        return

    with st.spinner("Loading cinematic profile…"):
        data, err = api_get(f"/movie/id/{tmdb_id}")

    if err or not data:
        st.error(f"Could not load details: {err or 'Unknown error'}")
        return

    card = norm_card(data)
    record_recent(card)

    backdrop = card.get("backdrop_url") or ""
    genres = card.get("genres") or []
    if isinstance(genres, list):
        genre_names = [g["name"] if isinstance(g, dict) else str(g) for g in genres]
    else:
        genre_names = []
    year = (card.get("release_date") or "")[:4]
    rating = card.get("rating")
    rating_str = f"{rating:.1f}" if rating else "—"

    in_wl = tmdb_id in st.session_state.watchlist
    in_fav = tmdb_id in st.session_state.favorites
    wl_url = action_url("wl_rm" if in_wl else "wl_add", card, back_view="details")
    fav_url = action_url("fav_rm" if in_fav else "fav_add", card, back_view="details")
    trailer_url = f"{TMDB_MOVIE_URL}/{tmdb_id}"

    # Hero backdrop
    hero_html = f'''
    <div class="details-hero fade-in">
      <div class="hero-bg" style="background-image: url('{_e(backdrop)}');"></div>
      <div class="hero-scrim"></div>
      <div class="hero-grain"></div>
      <div class="hero-content" style="padding: 44px 44px 20px 44px;">
        <div class="hero-eyebrow">◈ Cinematic Profile</div>
      </div>
    </div>
    '''
    st.markdown(hero_html, unsafe_allow_html=True)

    # Body
    left, right = st.columns([1, 2.2], gap="large")
    with left:
        if card.get("poster_url"):
            st.markdown(
                f'<div class="details-poster fade-in"><img src="{_e(card["poster_url"])}" alt="{_e(card["title"])}"/></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<div class="details-poster"><div class="poster-noimg">NO POSTER</div></div>', unsafe_allow_html=True)

    with right:
        genre_chips = "".join(f'<span class="chip">{_e(g)}</span>' for g in genre_names) or '<span class="chip">—</span>'
        st.markdown(
            f'''
            <div class="fade-in">
              <div class="details-title">{_e(card["title"])}</div>
              <div class="hero-meta" style="margin-bottom:16px;">
                <span class="chip year">{_e(year) if year else "—"}</span>
                <span class="rating-ring">★ {rating_str}</span>
                {genre_chips}
              </div>
              <div style="color:#d6d6e5; font-size:16px; line-height:1.7; max-width: 780px; margin-bottom:20px;">
                {_e(card.get("overview") or "No overview available.")}
              </div>
              <div style="display:flex; gap:12px; flex-wrap:wrap;">
                <a class="btn btn-primary" href="{trailer_url}" target="_blank">▶ Watch Trailer</a>
                <a class="btn btn-ghost" href="{wl_url}" target="_self">{"✓ In Watchlist" if in_wl else "＋ Add to Watchlist"}</a>
                <a class="btn btn-ghost" href="{fav_url}" target="_self">{"★ Favorited" if in_fav else "☆ Favorite"}</a>
                <a class="btn btn-ghost" href="?view=home" target="_self">← Back</a>
              </div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    # Recommendations
    title = (card.get("title") or "").strip()
    if title:
        bundle, err2 = api_get(
            "/movie/search",
            _params({"query": title, "tfidf_top_n": 14, "genre_limit": 14}),
        )
        if not err2 and bundle:
            tfidf_cards = cards_from_any(bundle)  # handles tfidf_recommendations
            genre_cards = [norm_card(x) for x in (bundle.get("genre_recommendations") or []) if norm_card(x)]

            section_header("Because You Watched This", "TF-IDF · Neural Similarity")
            carousel(tfidf_cards, section_id="det_tfidf", show_score=True,
                     empty_msg="No similar titles indexed yet.")

            section_header("More Like This", "Genre Match")
            carousel(genre_cards, section_id="det_genre",
                     empty_msg="No genre-based recommendations available.")
        else:
            genre_only, err3 = api_get("/recommend/genre", _params({"tmdb_id": tmdb_id, "limit": 18}))
            g_cards = cards_from_any(genre_only)
            section_header("More Like This", "Genre Match · Fallback")
            carousel(g_cards, section_id="det_genre_fb",
                     empty_msg="No recommendations available right now.")

# =============================================================
# VIEW: GENRES
# =============================================================
def render_genres():
    st.markdown('<div class="brand-sub" style="letter-spacing:5px;">◆ GENRE EXPLORER</div>', unsafe_allow_html=True)
    st.markdown('<h2 style="margin:6px 0 16px 0;">Explore by mood & genre</h2>', unsafe_allow_html=True)

    active = qp_genre or GENRE_SEEDS[0]
    chips_html = '<div class="genre-row">' + "".join(
        f'<a class="gchip {"active" if g == active else ""}" href="?view=genres&genre={urllib.parse.quote(g)}" target="_self">{_e(g)}</a>'
        for g in GENRE_SEEDS
    ) + '</div>'
    st.markdown(chips_html, unsafe_allow_html=True)

    # Use TMDB search on genre keyword as a proxy (backend has no /discover)
    with st.spinner(f"Loading {active}…"):
        data, err = api_get("/tmdb/search", _params({"query": active}))
    cards = cards_from_any(data)
    section_header(f"Explore · {active}", f"{len(cards)} titles")
    if err:
        st.error(err)
    else:
        grid(cards)

# =============================================================
# VIEW: WATCHLIST / FAVORITES / RECENT
# =============================================================
def render_collection(kind: str):
    labels = {
        "watchlist": ("My Watchlist", "Saved · Session Only", st.session_state.watchlist),
        "favorites": ("Favorites", "Your handpicked classics", st.session_state.favorites),
        "recent":    ("Recently Viewed", "Your trail through the engine", None),
    }
    title, sub, source = labels[kind]
    st.markdown(f'<div class="brand-sub" style="letter-spacing:5px;">♥ COLLECTION</div>', unsafe_allow_html=True)
    st.markdown(f'<h2 style="margin:6px 0 8px 0;">{_e(title)}</h2>', unsafe_allow_html=True)
    st.markdown(f'<div class="brand-sub" style="margin-bottom:16px;">{_e(sub)}</div>', unsafe_allow_html=True)

    if kind == "recent":
        items = list(st.session_state.recently_viewed)
        if items:
            st.markdown(
                f'<a class="rchip" href="?view=recent&action=recent_clear" target="_self" style="color:#ff2fd0;">✕ Clear History</a>',
                unsafe_allow_html=True,
            )
        cards = items
    else:
        cards = list(source.values())

    if not cards:
        st.markdown(
            f'<div class="empty" style="padding:60px 20px;">Nothing here yet. Explore the engine and add titles.</div>',
            unsafe_allow_html=True,
        )
        return
    grid(cards)

# =============================================================
# ROUTER
# =============================================================
if view == "home":
    render_home()
elif view == "search":
    render_search()
elif view == "details":
    if qp_id:
        render_details()
    else:
        render_home()
elif view == "genres":
    render_genres()
elif view == "watchlist":
    render_collection("watchlist")
elif view == "favorites":
    render_collection("favorites")
elif view == "recent":
    render_collection("recent")
else:
    render_home()

# =============================================================
# FOOTER
# =============================================================
st.markdown(
    '''
    <div style="margin-top: 60px; padding: 24px 0; border-top:1px solid rgba(255,255,255,0.06); text-align:center;">
      <div class="brand" style="font-size:20px;">FILMYNGINE</div>
      <div class="brand-sub" style="margin-top:6px;">Powered by TMDB · Free forever · Cyberpunk edition</div>
    </div>
    ''',
    unsafe_allow_html=True,
)