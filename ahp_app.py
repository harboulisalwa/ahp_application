"""
AHP Calculator - Analytic Hierarchy Process (méthode de Saaty)
Outil d'aide à la décision multicritère : définissez un objectif, des critères et des
alternatives, comparez-les deux à deux, et l'application calcule et affiche directement
la meilleure option.

Lancer :        streamlit run ahp_app.py
Dépendances :   pip install streamlit numpy pandas plotly openpyxl
"""

import html
import io
import json
import re
from fractions import Fraction

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="AHP Calculator", page_icon="◆", layout="wide",
                   initial_sidebar_state="expanded")

ss = st.session_state
esc = html.escape

# ---------------------------------------------------------------------------
# 0. THÈMES (sombre / clair) : noir, rose, bleu et jaune
# ---------------------------------------------------------------------------

PINK, PINK_L, PINK_D = "#FF4D9D", "#FF8CC6", "#C2185B"
BLUE_HEX, YELLOW = "#3B82F6", "#FACC15"
BLUE_RGB = "59,130,246"
OK, WARN = "#34D399", "#FBBF24"
PALETTE = [PINK, BLUE_HEX, YELLOW, PINK_L, "#9CC3FF", "#FDE68A", PINK_D, "#1D4ED8", "#CA8A04", "#E040FB"]
FONT = "'Times New Roman', Times, 'Liberation Serif', serif"

THEMES = {
    "Sombre": dict(
        dark=True, bg="#0B0B0F", surf="#15151C", surf2="#1B1B24", border="#2A2A36", side="#0F0F15",
        text="#F5F5F7", muted="#9A9AAE", soft="#D5D5E0", cell="#E4E4EC",
        pinkt="#FF8CC6", bluet="#9CC3FF", yellowt="#FACC15", diag="#FDE68A",
        hero="linear-gradient(135deg,rgba(255,77,157,.18) 0%,rgba(21,21,28,.92) 55%)",
        bgimg=("radial-gradient(900px 520px at 100% -5%,rgba(255,77,157,.16),transparent 60%),"
               "radial-gradient(700px 480px at -5% 105%,rgba(59,130,246,.12),transparent 60%),"
               "radial-gradient(500px 360px at 55% 110%,rgba(250,204,21,.07),transparent 60%),"
               "radial-gradient(rgba(255,255,255,.05) 1px,transparent 1px) 0 0/26px 26px,#0B0B0F")),
    "Clair": dict(
        dark=False, bg="#FCF8FB", surf="#FFFFFF", surf2="#F5ECF2", border="#E8DAE3", side="#FFFFFF",
        text="#1C1424", muted="#6E5F78", soft="#3A2D44", cell="#2A2033",
        pinkt="#C2185B", bluet="#1D4ED8", yellowt="#A16207", diag="#A16207",
        hero="linear-gradient(135deg,rgba(255,77,157,.16) 0%,rgba(255,255,255,.95) 60%)",
        bgimg=("radial-gradient(900px 520px at 100% -5%,rgba(255,77,157,.13),transparent 60%),"
               "radial-gradient(700px 480px at -5% 105%,rgba(59,130,246,.10),transparent 60%),"
               "radial-gradient(500px 360px at 55% 110%,rgba(250,204,21,.12),transparent 60%),"
               "radial-gradient(rgba(0,0,0,.05) 1px,transparent 1px) 0 0/26px 26px,#FCF8FB")),
}
if ss.get("theme") not in THEMES:
    try:                                   # le thème choisi survit à un rechargement via l'URL (?theme=Clair)
        _q = st.query_params.get("theme")
    except Exception:
        _q = None
    ss["theme"] = _q if _q in THEMES else "Sombre"
T = THEMES[ss["theme"]]


def set_theme():
    v = ss.get("theme_pick")
    if v in THEMES:
        ss["theme"] = v
        try:
            st.query_params["theme"] = v
        except Exception:
            pass


ROOT = ("<style>:root{" + "".join(f"--{k}:{v};" for k, v in T.items() if k != "dark")
        + f"--pink:{PINK};--pinkl:{PINK_L};--pinkd:{PINK_D};--blue:{BLUE_HEX};--yellow:{YELLOW};"
        + f"--font:{FONT};color-scheme:{'dark' if T['dark'] else 'light'};}}</style>")

CSS = """
<style>
html, body, .stApp, .stApp div, .stApp p, .stApp label, .stApp li, .stApp button, .stApp input,
.stApp textarea, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp td, .stApp th, .stApp summary,
.stApp small, .stApp b, .stApp em, .stApp i, [data-testid="stSidebar"], [data-testid="stSidebar"] div,
[data-testid="stSidebar"] p, [data-testid="stSidebar"] button {font-family:var(--font) !important;}
/* Fond et textes : forcés pour que le mode clair soit réellement blanc et lisible */
.stApp {background:var(--bgimg) !important; color:var(--text) !important;}
[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stBottom"],
[data-testid="stHeader"] {background:transparent !important;}
#MainMenu, footer {visibility:hidden;}
.block-container {padding-top:2rem; padding-bottom:6.5rem; max-width:1180px;}
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {color:var(--text) !important; letter-spacing:-0.01em;}
.stApp p, .stApp li, .stApp label, .stApp label p, .stApp summary, .stApp summary p,
.stApp [data-testid="stMarkdownContainer"] p, .stApp [data-testid="stMarkdownContainer"] li,
.stApp [data-testid="stWidgetLabel"] p, .stApp [data-testid="stRadio"] label p,
.stApp [data-testid="stTabs"] button p, .stApp [data-testid="stExpander"] summary,
.stApp [data-testid="stExpander"] summary p {color:var(--text) !important;}
.stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stCaptionContainer"] p,
.stApp [data-testid="stTickBarMin"], .stApp [data-testid="stTickBarMax"] {color:var(--muted) !important;}
.stApp [data-testid="stToolbar"] button, .stApp [data-testid="stToolbar"] svg {color:var(--text) !important;}
.stApp [data-testid="stSidebarCollapseButton"] button, .stApp [data-testid="stExpandSidebarButton"] {color:var(--muted) !important;}
.stApp [data-testid="stExpander"] svg {color:var(--text) !important; fill:var(--text) !important;}
hr {border-color:var(--border);}

/* ---------- Barre latérale : boutons 210 x 40 ---------- */
[data-testid="stSidebar"] {background:var(--side) !important; border-right:1px solid var(--border);}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {gap:.5rem;}
[data-testid="stSidebar"] .stButton, [data-testid="stSidebar"] [data-testid="stButton"],
[data-testid="stSidebar"] [data-testid="stElementContainer"], [data-testid="stSidebar"] .element-container {
  display:flex !important; justify-content:center !important; align-items:center; width:100% !important;}
[data-testid="stSidebar"] .stButton > button {margin:0 auto !important;}
[data-testid="stSidebar"] .stButton > button {width:210px !important; min-width:210px; max-width:210px;
  height:40px !important; min-height:40px; padding:0 12px; justify-content:center; text-align:center;
  font-size:14px; line-height:1.1; border-radius:12px; white-space:nowrap; overflow:hidden;}
[data-testid="stSidebar"] .stButton > button p {white-space:nowrap; margin:0; font-size:14px;}
.brand {display:flex; flex-direction:column; align-items:center; text-align:center; gap:2px; padding:4px 0 8px 0;}
.brand .logo {width:56px; height:56px; border-radius:18px; margin-bottom:10px;
  background:linear-gradient(135deg,var(--pinkl),var(--pink) 45%,var(--pinkd));
  display:flex; align-items:center; justify-content:center; font-weight:800; color:#1A0612; font-size:18px;
  animation:ahp-float 3.2s ease-in-out infinite;}
@keyframes ahp-float {
  0%,100% {transform:translateY(0) rotate(-3deg); box-shadow:0 8px 20px -6px rgba(255,77,157,.5);}
  50% {transform:translateY(-8px) rotate(3deg); box-shadow:0 24px 30px -10px rgba(255,77,157,.8);}}
@media (prefers-reduced-motion: reduce) {.brand .logo {animation:none;}}
.brand b {font-size:18px; letter-spacing:-0.02em; color:var(--text);}
.brand small {display:block; color:var(--muted); font-size:12px;}
.side-label {color:var(--muted); font-size:11px; font-weight:700; letter-spacing:.09em; text-transform:uppercase; margin:10px 2px 2px 2px;}
.credit {width:210px; box-sizing:border-box; margin-left:auto !important; margin-right:auto !important; background:linear-gradient(135deg,rgba(255,77,157,.16),rgba(59,130,246,.14) 60%,rgba(250,204,21,.14));
  border:1px solid var(--pink); border-radius:14px; padding:12px 14px; margin-top:14px; text-align:center;
  font-size:13px; color:var(--muted); line-height:1.5;}
.credit b {display:block; color:var(--yellowt); font-size:15px; letter-spacing:.01em;}

/* ---------- Boutons : tous de la même couleur ---------- */
.stApp .stButton > button, .stApp .stDownloadButton > button {
  background:var(--surf) !important; color:var(--text) !important; border:1.5px solid var(--pink) !important;
  border-radius:12px; font-weight:700; padding:0 1rem; height:40px; min-height:40px; transition:all .15s ease;}
.stApp .stButton > button p, .stApp .stDownloadButton > button p {color:inherit !important;}
.stApp .stButton > button:hover, .stApp .stDownloadButton > button:hover {
  background:linear-gradient(135deg,#FF6BB0,#F0408C) !important; color:#0B0610 !important;
  border-color:var(--pink) !important; box-shadow:0 10px 24px -12px rgba(255,77,157,.9);}
.stApp .stButton > button:focus-visible {outline:2px solid var(--yellow); outline-offset:2px;}
/* page active dans le menu : même bouton + barre jaune */
.stApp [data-testid="stSidebar"] .stButton > button[kind="primary"],
.stApp [data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-primary"] {
  box-shadow:inset 6px 0 0 var(--yellow), 0 0 0 3px rgba(255,77,157,.22);}
/* boutons Précédent / Suivant : fixés en bas de la page */
.st-key-footer_nav {position:fixed; bottom:16px; right:28px; width:440px; max-width:90vw; z-index:100;}
.st-key-footer_nav .stButton > button {width:100%;}

/* ---------- Pied de page ---------- */
.app-footer {text-align:center; margin-top:34px; padding:14px 20px; border-top:1px solid var(--border);
  color:var(--muted); font-size:14px; font-weight:700; letter-spacing:.04em;}

/* ---------- Onglets en forme de pastilles ---------- */
[data-baseweb="tab-list"] {gap:10px; flex-wrap:wrap; justify-content:center; padding:2px 0 12px 0; border-bottom:none !important;}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {display:none !important;}
.stApp [data-testid="stTabs"] button[role="tab"] {height:40px; padding:0 20px !important; margin:0 !important;
  border-radius:999px; border:1.5px solid var(--border); background:var(--surf); transition:all .15s ease;}
.stApp [data-testid="stTabs"] button[role="tab"]:hover {border-color:var(--pink);}
.stApp [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
  background:linear-gradient(135deg,#FF6BB0,#F0408C); border-color:var(--pink); box-shadow:0 10px 22px -12px rgba(255,77,157,.95);}
.stApp [data-testid="stTabs"] button[role="tab"][aria-selected="true"] p {color:#0B0610 !important; font-weight:800;}

.stApp [data-testid="stDownloadButton"] button, .stApp [data-testid="stFileUploaderDropzone"] button {
  background:var(--surf) !important; color:var(--text) !important; border:1.5px solid var(--pink) !important;
  border-radius:12px; height:40px; min-height:40px; font-weight:700;}
.stApp [data-testid="stDownloadButton"] button *, .stApp [data-testid="stFileUploaderDropzone"] button * {color:var(--text) !important;}
.stApp [data-testid="stDownloadButton"] button:hover, .stApp [data-testid="stFileUploaderDropzone"] button:hover {
  background:linear-gradient(135deg,#FF6BB0,#F0408C) !important; border-color:var(--pink) !important;}
.stApp [data-testid="stDownloadButton"] button:hover *, .stApp [data-testid="stFileUploaderDropzone"] button:hover * {color:#0B0610 !important;}
[data-testid="stDownloadButton"] button {width:100% !important;}
/* « Ouvrir un projet » : la zone de dépôt est réduite à un bouton de même taille que « Enregistrer » */
[data-testid="stFileUploader"] section, [data-testid="stFileUploaderDropzone"] {border:none !important; outline:none !important;
  background:transparent !important; box-shadow:none !important; padding:0 !important; min-height:0 !important; display:flex !important;}
[data-testid="stFileUploaderDropzoneInstructions"], [data-testid="stFileUploaderDropzone"] svg {display:none !important;}
.stApp [data-testid="stFileUploaderDropzone"] button {flex:1 1 100% !important; width:100% !important; min-width:100% !important; max-width:none !important; font-size:0 !important;}
.stApp [data-testid="stFileUploaderDropzone"] button * {font-size:0 !important;}
.stApp [data-testid="stFileUploaderDropzone"] button::after {content:"Ouvrir un projet (.json)"; font-size:16px; font-weight:700; color:var(--text);}
.stApp [data-testid="stFileUploaderDropzone"] button:hover::after {color:#0B0610;}
.stApp [data-testid="stDownloadButton"] button:disabled {opacity:.5;}

/* ---------- Sélecteurs en pastilles (st.pills) : centrés ---------- */
[data-testid="stElementContainer"]:has(button[data-testid^="stBaseButton-pills"]),
[data-testid="stButtonGroup"] {display:flex !important; justify-content:center !important; width:100% !important;}
div:has(> button[data-testid^="stBaseButton-pills"]) {display:flex !important; justify-content:center !important; flex-wrap:wrap !important;
  gap:8px !important; width:fit-content !important; max-width:100% !important; margin-left:auto !important; margin-right:auto !important;}
.stApp button[data-testid^="stBaseButton-pills"] {height:36px; padding:0 16px !important; border-radius:999px !important;
  border:1.5px solid var(--border) !important; background:var(--surf) !important; color:var(--text) !important;
  font-weight:600; transition:all .15s ease;}
.stApp button[data-testid^="stBaseButton-pills"] p {color:inherit !important; font-size:14px; white-space:nowrap;}
.stApp button[data-testid^="stBaseButton-pills"]:hover {border-color:var(--pink) !important;}
.stApp button[data-testid="stBaseButton-pillsActive"] {background:linear-gradient(135deg,#FF6BB0,#F0408C) !important;
  border-color:var(--pink) !important; color:#0B0610 !important; font-weight:800;
  box-shadow:0 10px 22px -12px rgba(255,77,157,.95);}
.stApp button[data-testid="stBaseButton-pillsActive"] p {color:#0B0610 !important; font-weight:800;}
.flabel.c {text-align:center; margin:14px 0 6px 0;}

/* ---------- Choix (boutons radio) : pastilles centrées ---------- */
.stApp [data-testid="stRadio"] {display:flex; flex-direction:column; align-items:center;}
.stApp [data-testid="stRadio"] [data-testid="stWidgetLabel"] {justify-content:center; text-align:center; margin-bottom:6px;}
.stApp [data-testid="stRadio"] [role="radiogroup"] {justify-content:center; gap:10px; flex-wrap:wrap;}
.stApp [data-testid="stRadio"] [role="radiogroup"] > label {margin:0; padding:8px 22px; border-radius:999px; cursor:pointer;
  border:1.5px solid var(--border); background:var(--surf); transition:all .15s ease;}
.stApp [data-testid="stRadio"] [role="radiogroup"] > label > div:first-child {display:none;}
.stApp [data-testid="stRadio"] [role="radiogroup"] > label:hover {border-color:var(--pink);}
.stApp [data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) {
  background:linear-gradient(135deg,#FF6BB0,#F0408C); border-color:var(--pink); box-shadow:0 10px 22px -12px rgba(255,77,157,.95);}
.stApp [data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) p {color:#0B0610 !important; font-weight:800;}

/* ---------- Champs ---------- */
textarea, input {color:var(--text) !important; -webkit-text-fill-color:var(--text);}
textarea {background:transparent !important;}
textarea::placeholder, input::placeholder {color:var(--muted) !important; -webkit-text-fill-color:var(--muted); opacity:.8;}
[data-baseweb="base-input"], [data-baseweb="textarea"], [data-baseweb="input"] {background:var(--surf2) !important; border-radius:14px !important;}
[data-baseweb="textarea"]:focus-within, [data-baseweb="input"]:focus-within {border-color:var(--pink) !important;}
[data-testid="stSlider"] [role="slider"] {background-color:var(--pink) !important; box-shadow:0 0 0 4px rgba(255,77,157,.25);}
[data-testid="stThumbValue"] {color:var(--pinkt) !important; font-weight:700;}
[data-testid="stTickBarMin"], [data-testid="stTickBarMax"] {color:var(--muted);}
[data-testid="stExpander"] {border:1px solid var(--border); border-radius:14px; background:var(--surf);}
[data-testid="stExpander"] summary {font-weight:600;}
[data-testid="stTabs"] button[role="tab"] {font-weight:600;}
[data-testid="stSidebarCollapseButton"] button, [data-testid="stExpandSidebarButton"] {color:var(--muted);}

/* ---------- Bloc « publication » (page Problème) ---------- */
.st-key-composer {border:2px solid var(--pink); border-radius:22px; background:var(--surf);
  padding:0 22px 18px 22px; overflow:hidden; box-shadow:0 24px 60px -34px rgba(255,77,157,.7);}
.post-head {display:flex; align-items:center; gap:14px; margin:0 -22px 6px -22px; padding:16px 22px;
  background:linear-gradient(90deg,rgba(255,77,157,.20),rgba(59,130,246,.12) 60%,rgba(250,204,21,.12));
  border-bottom:1px solid var(--border);}
.avatar {position:relative; width:46px; height:46px; border-radius:50%; flex:none; display:flex; align-items:center;
  justify-content:center; font-weight:800; color:#1A0612; font-size:16px;
  background:linear-gradient(135deg,var(--pink),var(--yellow)); box-shadow:0 0 0 3px var(--surf), 0 0 0 5px var(--pink);}
.avatar::after {content:""; position:absolute; right:-1px; bottom:-1px; width:12px; height:12px; border-radius:50%;
  background:#34D399; border:2px solid var(--surf);}
.post-head b {display:block; font-size:16px; color:var(--text);}
.post-head span {color:var(--muted); font-size:13px;}
.flabel {font-size:12px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); margin:10px 0 2px 2px;}
.flabel em {font-style:normal; text-transform:none; letter-spacing:0; font-weight:500; margin-left:6px;}
.chips {display:flex; flex-wrap:wrap; gap:8px; margin:4px 0 2px 0;}
.chip {padding:5px 13px; border-radius:999px; font-size:13.5px; font-weight:700; border:1px solid;}
.chip.pink {background:rgba(255,77,157,.12); color:var(--pinkt); border-color:rgba(255,77,157,.45);}
.chip.blue {background:rgba(59,130,246,.12); color:var(--bluet); border-color:rgba(59,130,246,.45);}
.stats {display:flex; gap:26px; margin:12px 0 4px 2px; padding-top:12px; border-top:1px solid var(--border); color:var(--muted); font-size:13.5px;}
.stats b {color:var(--text); font-size:19px; margin-right:6px;}
.st-key-composer [data-baseweb="input"], .st-key-composer [data-baseweb="input"] > div {border-radius:999px !important;}
.st-key-composer input {font-size:16px; padding-left:18px !important;}
.st-key-composer [data-baseweb="textarea"] {border-radius:18px !important;}
.st-key-composer .stButton > button {padding:0 8px; font-size:13.5px;}

/* ---------- Cartes de comparaison : même taille ---------- */
[class*="st-key-pair_"] {background:var(--surf); border:1px solid var(--border); border-radius:16px;
  padding:14px 18px 10px 18px; min-height:160px; box-sizing:border-box;}
.pair {display:flex; align-items:center; gap:10px; margin-bottom:2px; font-size:15px; min-height:26px;}
.pair b {color:var(--text); max-width:42%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
.pair i {color:var(--pink); font-style:normal; font-weight:800;}
.pair-note {height:2.95em; overflow:hidden; font-size:13.5px; color:var(--muted); line-height:1.45; margin-top:2px;}
.pair-note b {color:var(--text);}

/* ---------- Cartes, bandeaux ---------- */
.card {background:var(--surf); border:1px solid var(--border); border-radius:16px; padding:16px 20px;}
.card-t {font-size:15px; font-weight:700; margin-bottom:6px; color:var(--text);}
.card.eq {box-sizing:border-box; overflow:auto;}
.card.eq .tbl-wrap {margin:4px 0 0 0;}
.hero {position:relative; overflow:hidden; background:var(--hero); border:1px solid rgba(255,77,157,.35);
  border-radius:22px; padding:30px 34px; margin-bottom:16px;}
.hero .eyebrow {color:var(--yellowt);}
.hero h1 {font-size:38px; line-height:1.1; margin:8px 0 10px 0; font-weight:800; color:var(--text);}
.hero h1 span {color:var(--pink);}
.hero .lead {color:var(--soft); font-size:16px; line-height:1.6;}
.hero.compact {padding:20px 26px; margin-bottom:14px; border-radius:18px;}
.hero.compact h1 {font-size:27px; margin:4px 0 6px 0;}
.hero.compact .lead {font-size:14px; line-height:1.5;}
.hero::after {content:""; position:absolute; right:-70px; top:-70px; width:280px; height:280px; border-radius:50%;
  background:radial-gradient(circle,rgba(255,77,157,.38),transparent 70%); pointer-events:none;}
.win {display:flex; align-items:center; justify-content:space-between; gap:18px; flex-wrap:wrap;
  background:linear-gradient(135deg,rgba(255,77,157,.26),var(--surf) 75%); border:1px solid var(--pink);
  border-radius:20px; padding:18px 26px; margin-bottom:14px;}
.win .big {font-size:32px; font-weight:800; letter-spacing:-0.02em; color:var(--text); line-height:1.1;}
.win .score {text-align:right; color:var(--soft); font-size:14px;}
.win .score b {display:block; font-size:28px; color:var(--yellowt);}

/* ---------- KPI ---------- */
.kpi {background:var(--surf); border:1px solid var(--border); border-radius:14px; padding:14px 16px; transition:transform .2s ease;}
.kpi .l {color:var(--muted); font-size:12px; font-weight:600; letter-spacing:.02em;}
.kpi .v {font-size:25px; font-weight:800; margin-top:2px; letter-spacing:-0.02em; color:var(--text);}
.kpi .s {color:var(--muted); font-size:12px; margin-top:2px;}
.kpi.pink, .kpi.blue, .kpi.yellow {position:relative; overflow:hidden; border:none; border-radius:20px; padding:20px 22px;}
.kpi.pink {background:linear-gradient(145deg,#FF74B5 0%,#F0408C 100%); box-shadow:0 16px 36px -14px rgba(255,77,157,.75);}
.kpi.blue {background:linear-gradient(145deg,#6AA8FF 0%,#2F6FE0 100%); box-shadow:0 16px 36px -14px rgba(59,130,246,.75);}
.kpi.yellow {background:linear-gradient(145deg,#FFE066 0%,#FACC15 100%); box-shadow:0 16px 36px -14px rgba(250,204,21,.65);}
.kpi.pink::after, .kpi.blue::after, .kpi.yellow::after {content:""; position:absolute; right:-28px; bottom:-34px; width:100px; height:100px;
  border-radius:50%; background:rgba(255,255,255,.22);}
.kpi.pink:hover, .kpi.blue:hover, .kpi.yellow:hover {transform:translateY(-4px);}
.kpi.pink .l, .kpi.blue .l, .kpi.yellow .l {color:rgba(10,8,20,.78); text-transform:uppercase; letter-spacing:.09em; font-size:11.5px; font-weight:800;}
.kpi.pink .v, .kpi.blue .v, .kpi.yellow .v {color:#0B0610; font-size:30px; margin-top:8px; line-height:1.1;}
.kpi.pink .s, .kpi.blue .s, .kpi.yellow .s {color:rgba(10,8,20,.75); font-weight:700; margin-top:6px;}
/* carte « Meilleure option » : suit maintenant le thème (plus de noir en dur) */
.kpi.dark {background:var(--surf); border:1px solid var(--pink); border-radius:20px; padding:20px 22px;
  box-shadow:0 16px 36px -18px rgba(255,77,157,.6);}
.kpi.dark .l {color:var(--pinkt); text-transform:uppercase; letter-spacing:.09em; font-size:11.5px; font-weight:800;}
.kpi.dark .v {color:var(--text); font-size:30px; margin-top:8px; line-height:1.1;}
.kpi.dark .s {color:var(--yellowt); font-weight:700; margin-top:6px;}
.kpi.compact {height:92px; box-sizing:border-box; padding:11px 16px; border-radius:16px; display:flex;
  flex-direction:column; justify-content:center; overflow:hidden;}
.kpi.compact .l {font-size:10.5px; letter-spacing:.07em;}
.kpi.compact .v {font-size:19px; margin-top:3px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.kpi.compact .s {font-size:11px; margin-top:2px;}
.kpi.compact::after {width:70px; height:70px; right:-22px; bottom:-26px;}

.pill {display:inline-block; padding:3px 11px; border-radius:999px; font-size:12.5px; font-weight:700;}
.pill.ok {background:rgba(52,211,153,.14); color:#10B981; border:1px solid rgba(52,211,153,.5);}
.pill.warn {background:rgba(251,191,36,.14); color:#D97706; border:1px solid rgba(251,191,36,.5);}

/* ---------- En-tête de page ---------- */
.phead {display:flex; align-items:flex-start; justify-content:space-between; gap:16px; flex-wrap:wrap;}
.eyebrow {color:var(--yellowt); font-size:12px; font-weight:700; letter-spacing:.12em; text-transform:uppercase;}
.ptitle {font-size:36px; font-weight:800; letter-spacing:-0.02em; margin:2px 0 8px 0;
  background:linear-gradient(90deg,var(--text) 20%,var(--pinkt)); -webkit-background-clip:text; background-clip:text; color:transparent;}
.psub {color:var(--muted); font-size:15px; margin:0 0 14px 0; max-width:780px; line-height:1.55;}
.live {display:inline-flex; align-items:center; gap:9px; padding:8px 16px; border-radius:999px; border:1px solid var(--pink);
  background:rgba(255,77,157,.10); font-size:13.5px; color:var(--soft); margin-top:6px;}
.live b {color:var(--yellowt);}
.live .dot {width:8px; height:8px; border-radius:50%; background:var(--yellow); box-shadow:0 0 0 4px rgba(250,204,21,.22);}

/* ---------- Tableaux et barres ---------- */
.tbl-wrap {overflow-x:auto; border:1px solid rgba(59,130,246,.35); border-radius:14px; margin:6px 0 10px 0;}
.ahp-table {width:100%; border-collapse:collapse; font-size:14px; font-variant-numeric:tabular-nums;}
.ahp-table th, .ahp-table td {padding:9px 14px; text-align:right; border-bottom:1px solid var(--border);}
.ahp-table thead th {background:rgba(59,130,246,.20); color:var(--bluet); font-weight:700; font-size:12.5px; letter-spacing:.03em;}
.ahp-table tbody th {text-align:left; font-weight:700; color:var(--bluet); background:var(--surf);}
.ahp-table thead th:first-child {text-align:left;}
.ahp-table td {background:var(--surf); color:var(--cell);}
.ahp-table td.diag {color:var(--diag); font-weight:700;}
.ahp-table tr:last-child th, .ahp-table tr:last-child td {border-bottom:none;}
.ahp-table tr.hl td, .ahp-table tr.hl th {background:rgba(255,77,157,.16); color:var(--text);}
.wbar {display:flex; align-items:center; gap:12px; margin:7px 0; font-size:13.5px;}
.wbar .n {width:140px; flex:none; color:var(--text); font-weight:600; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
.wbar .t {flex:1; background:var(--surf2); border-radius:999px; height:10px; overflow:hidden;}
.wbar .f {height:100%; background:linear-gradient(90deg,var(--pinkd),var(--pink)); border-radius:999px;}
.wbar .p {width:58px; text-align:right; color:var(--yellowt); font-weight:700; font-variant-numeric:tabular-nums;}
.tip {border-left:3px solid var(--pink); background:rgba(255,77,157,.07); padding:11px 16px; border-radius:0 12px 12px 0;
  color:var(--soft); font-size:14px; margin:8px 0 14px 0; line-height:1.55;}
.tip b {color:var(--pinkt);}
.help {color:var(--muted); font-size:13px; line-height:1.5; margin-top:10px;}
.help b {color:var(--text);}

.sec {font-size:21px; font-weight:700; letter-spacing:-0.01em; margin:26px 0 10px 0; display:flex; align-items:center; gap:12px; color:var(--text);}
.sec::before {content:""; width:6px; height:24px; border-radius:3px; background:linear-gradient(180deg,var(--pink),var(--yellow));}
.sec.sm {font-size:17px; margin:6px 0 8px 0;}

/* ---------- Hiérarchie centrée ---------- */
.stGraphVizChart, [data-testid="stGraphVizChart"] {display:flex !important; justify-content:center; text-align:center;}
.stGraphVizChart > div, [data-testid="stGraphVizChart"] > div {margin:0 auto; text-align:center; width:100%;}
.stGraphVizChart svg, [data-testid="stGraphVizChart"] svg {display:block; margin:0 auto !important; max-width:100%; height:auto;}

/* ---------- Guide ---------- */
.ggrid {display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:16px; align-items:stretch; margin-bottom:6px;}
.gcard {background:var(--surf); border:1px solid var(--border); border-radius:18px; padding:20px 22px; height:100%; box-sizing:border-box;}
.gcard .n {display:inline-flex; width:34px; height:34px; border-radius:11px; align-items:center; justify-content:center;
  font-weight:800; color:#0B0610; margin-bottom:12px; background:linear-gradient(135deg,var(--pink),#FF8CC6);}
.gcard.b .n {background:linear-gradient(135deg,#6AA8FF,#2F6FE0);}
.gcard.y .n {background:linear-gradient(135deg,#FFE066,#FACC15);}
.gcard h4 {margin:0 0 6px 0; font-size:17px;}
.gcard .d {color:var(--muted); font-size:14px; line-height:1.55;}
.scale {display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin:8px 0 12px 0;}
.scale .s {background:var(--surf); border:1px solid var(--border); border-radius:16px; padding:14px 16px; text-align:center;}
.scale .s b {display:block; font-size:34px; color:var(--pinkt); line-height:1.1;}
.scale .s span {color:var(--muted); font-size:13px;}
.scale .s:nth-child(2n) b {color:var(--bluet);}
.scale .s:nth-child(3n) b {color:var(--yellowt);}
.err {display:flex; gap:14px; align-items:flex-start; background:var(--surf); border:1px solid var(--border);
  border-left:4px solid var(--pink); border-radius:14px; padding:13px 18px; margin:8px 0; color:var(--soft); font-size:14.5px; line-height:1.5;}
.err b {color:var(--text);}
.swatch {display:flex; gap:14px; flex-wrap:wrap; margin:10px 0;}
.swatch div {flex:1; min-width:180px; border-radius:16px; padding:16px 18px; font-weight:700; border:1px solid;}
.swatch .d {background:#0B0B0F; color:#F5F5F7; border-color:#FF4D9D;}
.swatch .l {background:#FCF8FB; color:#1C1424; border-color:#E8DAE3;}

/* ======================================================================
   CORRECTIF THÈME : composants natifs Streamlit qui gardaient le fond noir
   ====================================================================== */
/* Alertes (st.error, st.warning, st.info) */
.stApp [data-testid="stAlert"], .stApp [data-testid="stAlertContainer"] {
  background:var(--surf2) !important; border:1px solid var(--border); border-radius:14px;}
.stApp [data-testid="stAlert"] *, .stApp [data-testid="stAlertContainer"] * {color:var(--text) !important;}
/* Expanders (fond du panneau ouvert) */
.stApp [data-testid="stExpander"] details, .stApp [data-testid="stExpander"] summary,
.stApp [data-testid="stExpanderDetails"] {background:var(--surf) !important; color:var(--text) !important;}
/* Barre latérale (conteneurs internes) */
[data-testid="stSidebarContent"], [data-testid="stSidebarHeader"] {background:var(--side) !important;}
/* Menus déroulants, popovers, infobulles */
[data-baseweb="popover"], [data-baseweb="popover"] > div, [data-baseweb="menu"],
[data-baseweb="tooltip"] > div, [data-baseweb="select"] > div {
  background:var(--surf) !important; color:var(--text) !important;}
[data-baseweb="menu"] li, [data-baseweb="tooltip"] * {color:var(--text) !important;}
/* Formules LaTeX et code */
.stApp .katex, .stApp .katex * {color:var(--text) !important;}
.stApp code {background:var(--surf2) !important; color:var(--pinkt) !important;}
/* Fichier chargé dans le uploader */
.stApp [data-testid="stFileUploaderFile"] * {color:var(--text) !important;}
/* Graphiques Plotly : fond transparent même si le thème natif est sombre */
.stApp [data-testid="stPlotlyChart"], .stApp .js-plotly-plot, .stApp .plotly, .stApp .main-svg {background:transparent !important;}

/* Pastilles (st.pills / groupes de boutons) : plusieurs sélecteurs, car le nom interne varie selon la version */
.stApp [data-testid="stButtonGroup"] button,
.stApp [data-testid="stPills"] button,
.stApp [data-baseweb="button-group"] button,
.stApp button[kind^="pills"],
.stApp button[data-testid*="pills"] {
  background:var(--surf) !important; background-image:none !important; color:var(--text) !important;
  border:1.5px solid var(--border) !important; border-radius:999px !important; box-shadow:none !important;}
.stApp [data-testid="stButtonGroup"] button *, .stApp [data-testid="stPills"] button *,
.stApp [data-baseweb="button-group"] button *, .stApp button[kind^="pills"] *,
.stApp button[data-testid*="pills"] * {color:var(--text) !important;}
.stApp [data-testid="stButtonGroup"] button:hover, .stApp [data-testid="stPills"] button:hover,
.stApp button[kind^="pills"]:hover, .stApp button[data-testid*="pills"]:hover {border-color:var(--pink) !important;}
/* pastille sélectionnée */
.stApp [data-testid="stButtonGroup"] button[aria-checked="true"],
.stApp [data-testid="stButtonGroup"] button[aria-pressed="true"],
.stApp [data-testid="stPills"] button[aria-checked="true"],
.stApp [data-testid="stPills"] button[aria-pressed="true"],
.stApp button[kind="pillsActive"], .stApp button[data-testid="stBaseButton-pillsActive"] {
  background:linear-gradient(135deg,#FF6BB0,#F0408C) !important; border-color:var(--pink) !important;
  box-shadow:0 10px 22px -12px rgba(255,77,157,.95) !important;}
.stApp [data-testid="stButtonGroup"] button[aria-checked="true"] *,
.stApp [data-testid="stButtonGroup"] button[aria-pressed="true"] *,
.stApp [data-testid="stPills"] button[aria-checked="true"] *,
.stApp [data-testid="stPills"] button[aria-pressed="true"] *,
.stApp button[kind="pillsActive"] *, .stApp button[data-testid="stBaseButton-pillsActive"] * {
  color:#0B0610 !important; font-weight:800;}

/* Champs de saisie (text_input, text_area, number_input, selectbox) : fond forcé à tous les niveaux */
.stApp [data-baseweb="input"], .stApp [data-baseweb="input"] > div,
.stApp [data-baseweb="base-input"], .stApp [data-baseweb="base-input"] > div,
.stApp [data-baseweb="textarea"], .stApp [data-baseweb="textarea"] > div,
.stApp [data-baseweb="select"] > div,
.stApp [data-testid="stTextInput"] > div, .stApp [data-testid="stTextArea"] > div,
.stApp [data-testid="stTextInputRootElement"], .stApp [data-testid="stTextAreaRootElement"],
.stApp [data-testid="stNumberInput"] > div, .stApp [data-testid="stNumberInputContainer"] {
  background:var(--surf2) !important; background-color:var(--surf2) !important;}
.stApp textarea, .stApp input[type="text"], .stApp input[type="number"], .stApp input:not([type]) {
  background:var(--surf2) !important; background-color:var(--surf2) !important;
  color:var(--text) !important; -webkit-text-fill-color:var(--text) !important; caret-color:var(--pink);}
.stApp textarea::placeholder, .stApp input::placeholder {
  color:var(--muted) !important; -webkit-text-fill-color:var(--muted) !important; opacity:.8;}
.stApp [data-baseweb="input"], .stApp [data-baseweb="textarea"] {border:1px solid var(--border) !important;}
.stApp [data-baseweb="input"]:focus-within, .stApp [data-baseweb="textarea"]:focus-within {border-color:var(--pink) !important;}
/* Autoremplissage du navigateur */
.stApp input:-webkit-autofill {-webkit-box-shadow:0 0 0 1000px var(--surf2) inset !important;
  -webkit-text-fill-color:var(--text) !important;}

/* Pastilles centrées : plusieurs sélecteurs selon la version de Streamlit */
.stApp [data-testid="stElementContainer"]:has([data-testid="stButtonGroup"]),
.stApp [data-testid="stElementContainer"]:has(button[kind^="pills"]),
.stApp [data-testid="stElementContainer"]:has(button[data-testid*="pills"]),
.stApp .element-container:has([data-testid="stButtonGroup"]),
.stApp [data-testid="stButtonGroup"], .stApp [data-testid="stPills"] {
  display:flex !important; justify-content:center !important; align-items:center !important;
  width:100% !important; text-align:center !important;}
.stApp [data-testid="stButtonGroup"] > div, .stApp [data-testid="stPills"] > div,
.stApp [data-baseweb="button-group"], .stApp [role="radiogroup"]:has(button),
.stApp div:has(> button[kind^="pills"]), .stApp div:has(> button[data-testid*="pills"]) {
  display:flex !important; flex-wrap:wrap !important; justify-content:center !important;
  gap:8px !important; width:fit-content !important; max-width:100% !important;
  margin-left:auto !important; margin-right:auto !important;}
</style>
"""
st.markdown(ROOT + CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 1. FONCTIONS DE CALCUL
# ---------------------------------------------------------------------------

RI_TABLE = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12,
            6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}

# Curseur : k > 0 -> le 1er élément l'emporte (valeur k+1) ; k < 0 -> le 2e l'emporte (valeur 1/(|k|+1))
SCALE_OPTIONS = list(range(8, -9, -1))
DEGREE = {2: "légèrement", 3: "modérément", 4: "modérément à fortement", 5: "fortement",
          6: "fortement à très fortement", 7: "très fortement",
          8: "très fortement à extrêmement", 9: "extrêmement"}


def scale_value(k: int) -> float:
    if k == 0:
        return 1.0
    return float(k + 1) if k > 0 else 1.0 / (-k + 1)


def scale_label(k: int) -> str:
    if k == 0:
        return "1"
    return f"◀ {k + 1}" if k > 0 else f"{-k + 1} ▶"


def sentence_html(a: str, b: str, k: int) -> str:
    a, b = esc(a), esc(b)
    if k == 0:
        return f"<b>{a}</b> = <b>{b}</b> : même importance (1)"
    if k > 0:
        return f"<b>{a}</b> l'emporte : {DEGREE[k + 1]} ({k + 1})"
    return f"<b>{b}</b> l'emporte : {DEGREE[-k + 1]} (1/{-k + 1})"


def frac(x: float) -> str:
    f = Fraction(float(x)).limit_denominator(9)
    return str(f.numerator) if f.denominator == 1 else f"{f.numerator}/{f.denominator}"


def geometric_priorities(A: np.ndarray):
    n = A.shape[0]
    products = np.prod(A, axis=1)
    geo = products ** (1.0 / n)
    return products, geo, geo / geo.sum()


def consistency(A: np.ndarray, w: np.ndarray):
    n = A.shape[0]
    Aw = A @ w
    ratios = Aw / w
    lam = float(ratios.mean())
    ci = (lam - n) / (n - 1) if n > 1 else 0.0
    ri = RI_TABLE.get(n, 1.49)
    cr = ci / ri if ri > 0 else 0.0
    return lam, ci, ri, cr, Aw, ratios


def matrix_from_state(prefix: str, n: int) -> np.ndarray:
    A = np.ones((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            v = scale_value(ss.get(f"{prefix}_{i}_{j}", 0))
            A[i, j], A[j, i] = v, 1.0 / v
    return A


# ---------------------------------------------------------------------------
# 2. ÉTAT, EXEMPLES ET NAVIGATION
# ---------------------------------------------------------------------------

# Conserve l'état des widgets quand on change de page (Streamlit les supprime sinon)
_KEEP = ("goal", "crit_", "alt", "theme")
for _k in list(ss.keys()):
    if _k.startswith(_KEEP):
        ss[_k] = ss[_k]

EX_CRIT_JUDG = {(0, 1): 4, (0, 2): 3, (0, 3): 7, (1, 2): 1 / 3, (1, 3): 3, (2, 3): 5}
# Valeurs approximatives (les matrices exactes du cours ne sont pas connues)
EX_ALT_JUDG = [
    {(0, 1): 1 / 3, (0, 2): 3, (1, 2): 9},
    {(0, 1): 2, (0, 2): 1 / 4, (1, 2): 1 / 9},
    {(0, 1): 4, (0, 2): 9, (1, 2): 3},
    {(0, 1): 1 / 3, (0, 2): 4, (1, 2): 9},
]
TEMPLATES = {
    "Candidat": ("Choisir le meilleur candidat", ["Expérience", "Éducation", "Charisme", "Âge"],
                 ["Pers 1", "Pers 2", "Pers 3"]),
    "Voiture": ("Choisir une voiture", ["Prix", "Consommation", "Confort", "Sécurité"],
                ["Citadine", "Berline", "SUV"]),
    "Fournisseur": ("Choisir un fournisseur", ["Coût", "Qualité", "Délai de livraison", "Service après-vente"],
                    ["Fournisseur A", "Fournisseur B", "Fournisseur C"]),
    "Projet vide": ("", [], []),
}


def value_to_index(v: float) -> int:
    return int(round(v)) - 1 if v >= 1 else -(int(round(1 / v)) - 1)


def reset_judgments():
    for k in list(ss.keys()):
        if re.fullmatch(r"(crit|alt\d+)_\d+_\d+", k) or k in ("sens_crit", "detail_sel"):
            del ss[k]


def apply_template(name: str):
    reset_judgments()
    goal_, crit_, alts_ = TEMPLATES[name]
    ss["goal"] = goal_
    ss["crit_text"] = "\n".join(crit_)
    ss["alt_text"] = "\n".join(alts_)
    ss["_store"] = {}
    ss["_names"] = (list(crit_), list(alts_))
    if name == "Candidat":   # jugements de l'exemple du cours
        for (i, j), v in EX_CRIT_JUDG.items():
            ss[f"crit_{i}_{j}"] = value_to_index(v)
        for c, judg in enumerate(EX_ALT_JUDG):
            for (i, j), v in judg.items():
                ss[f"alt{c}_{i}_{j}"] = value_to_index(v)


def go_to(page: str):
    ss["page"] = page


def _pairs(k):
    return [(i, j) for i in range(k) for j in range(i + 1, k)]


def _find(store, head, a, b):
    """Jugement mémorisé pour (a, b), quel que soit leur ordre actuel."""
    if (*head, a, b) in store:
        return store[(*head, a, b)]
    if (*head, b, a) in store:
        return -store[(*head, b, a)]
    return None


def judgments_snapshot(cr_names, al_names):
    """Jugements actuels, indexés par NOMS (et non par position)."""
    d = {}
    for i, j in _pairs(len(cr_names)):
        if f"crit_{i}_{j}" in ss:
            d[("crit", cr_names[i], cr_names[j])] = ss[f"crit_{i}_{j}"]
    for c, cn in enumerate(cr_names):
        for i, j in _pairs(len(al_names)):
            if f"alt{c}_{i}_{j}" in ss:
                d[("alt", cn, al_names[i], al_names[j])] = ss[f"alt{c}_{i}_{j}"]
    return d


def remap_judgments(cr_names, al_names):
    """Si les noms changent (renommer, réordonner, ajouter, supprimer), chaque jugement suit son nom."""
    prev, now = ss.get("_names"), (list(cr_names), list(al_names))
    if prev is not None and prev != now:
        store = ss.setdefault("_store", {})
        store.update(judgments_snapshot(*prev))
        for k in [k for k in ss.keys() if re.fullmatch(r"(crit|alt\d+)_\d+_\d+", k)]:
            del ss[k]
        for i, j in _pairs(len(cr_names)):
            v = _find(store, ("crit",), cr_names[i], cr_names[j])
            if v is not None:
                ss[f"crit_{i}_{j}"] = v
        for c, cn in enumerate(cr_names):
            for i, j in _pairs(len(al_names)):
                v = _find(store, ("alt", cn), al_names[i], al_names[j])
                if v is not None:
                    ss[f"alt{c}_{i}_{j}"] = v
    ss["_names"] = now


def project_json(goal_, cr_names, al_names) -> bytes:
    data = {
        "version": 1, "goal": goal_, "criteria": cr_names, "alternatives": al_names,
        "criteria_judgments": [{"a": cr_names[i], "b": cr_names[j], "k": int(ss.get(f"crit_{i}_{j}", 0))}
                               for i, j in _pairs(len(cr_names))],
        "alternative_judgments": [{"criterion": cn, "a": al_names[i], "b": al_names[j],
                                   "k": int(ss.get(f"alt{c}_{i}_{j}", 0))}
                                  for c, cn in enumerate(cr_names) for i, j in _pairs(len(al_names))],
    }
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


def load_project():
    """Ouvre un fichier projet (.json) enregistré par l'application."""
    f = ss.get("proj_file")
    if f is None:
        return
    try:
        data = json.loads(f.getvalue().decode("utf-8"))
        goal_ = str(data.get("goal", ""))
        cr_names = [str(x).strip() for x in data["criteria"]]
        al_names = [str(x).strip() for x in data["alternatives"]]
        store = {}
        for r in data.get("criteria_judgments", []):
            store[("crit", str(r["a"]), str(r["b"]))] = max(-8, min(8, int(r["k"])))
        for r in data.get("alternative_judgments", []):
            store[("alt", str(r["criterion"]), str(r["a"]), str(r["b"]))] = max(-8, min(8, int(r["k"])))
    except Exception:
        ss["_load_error"] = True
        return
    reset_judgments()
    ss["goal"] = goal_
    ss["crit_text"] = "\n".join(cr_names)
    ss["alt_text"] = "\n".join(al_names)
    ss["_store"] = store
    ss["_names"] = ([], [])     # force la reconstruction des curseurs à partir des noms


if "crit_text" not in ss:
    apply_template("Candidat")
ss.setdefault("page", "home")

PAGES = [
    ("home", "Accueil", "home"),
    ("probleme", "1 · Problème", "account_tree"),
    ("criteres", "2 · Critères", "tune"),
    ("alternatives", "3 · Alternatives", "compare_arrows"),
    ("resultats", "4 · Résultats", "emoji_events"),
    ("guide", "Guide AHP", "menu_book"),
]
ORDER = [p[0] for p in PAGES]
LAST_STEP = ORDER.index("resultats")


def button(label, icon, key, on_click, args=()):
    kw = dict(key=key, on_click=on_click, args=args)
    try:
        st.button(label, icon=f":material/{icon}:", **kw)
    except Exception:
        st.button(label, **kw)


def nav_button(label, icon, target, key):
    button(label, icon, key, go_to, (target,))


# ---------------------------------------------------------------------------
# 3. LECTURE DES DONNÉES ET CALCULS (automatiques, à chaque action)
# ---------------------------------------------------------------------------

crit = [x.strip() for x in ss.get("crit_text", "").splitlines() if x.strip()]
alts = [x.strip() for x in ss.get("alt_text", "").splitlines() if x.strip()]
goal = (ss.get("goal") or "").strip() or "Objectif"
remap_judgments(crit, alts)

errors = []
if not 2 <= len(crit) <= 10:
    errors.append("Il faut entre 2 et 10 critères (un par ligne).")
if not 2 <= len(alts) <= 10:
    errors.append("Il faut entre 2 et 10 alternatives (une par ligne).")
if len(set(crit)) != len(crit):
    errors.append("Les noms des critères doivent être tous différents.")
if len(set(alts)) != len(alts):
    errors.append("Les noms des alternatives doivent être tous différents.")
valid = not errors

n, m = len(crit), len(alts)

if valid:
    A_crit = matrix_from_state("crit", n)
    w_crit = geometric_priorities(A_crit)[2]
    cr_crit = consistency(A_crit, w_crit)[3]
    crs = {"Critères": cr_crit}
    alt_mats = [matrix_from_state(f"alt{c}", m) for c in range(n)]
    local = np.zeros((m, n))
    for c in range(n):
        local[:, c] = geometric_priorities(alt_mats[c])[2]
        crs[f"Alternatives · {crit[c]}"] = consistency(alt_mats[c], local[:, c])[3]
    scores = local @ w_crit
    all_ok = all(v < 0.1 for v in crs.values())
    best_idx = int(np.argmax(scores))
    tie = bool(np.ptp(scores) < 1e-9)      # aucune préférence exprimée -> égalité parfaite
    best_name = "Égalité" if tie else alts[best_idx]


# ---------------------------------------------------------------------------
# 4. COMPOSANTS D'INTERFACE
# ---------------------------------------------------------------------------

def _num(v):
    return isinstance(v, (float, np.floating))


def table_html(rows, header, corner="", fmt="{:.4f}", highlight=None, diag=False, heat=None):
    """Tableau HTML stylé (renvoie le code HTML). rows = liste de (nom, [valeurs]).
    heat : None | "col" (dégradé bleu par colonne) | fonction (ligne, colonne) -> intensité 0..1."""
    bounds = {}
    if heat == "col":
        for c in range(len(header)):
            vals = [float(vs[c]) for _, vs in rows if _num(vs[c])]
            if vals:
                bounds[c] = (min(vals), max(vals))
    out = ["<div class='tbl-wrap'><table class='ahp-table'><thead><tr>"]
    out += [f"<th>{esc(str(c))}</th>" for c in [corner] + list(header)]
    out.append("</tr></thead><tbody>")
    for r, (name, vals) in enumerate(rows):
        out.append("<tr class='hl'>" if r == highlight else "<tr>")
        out.append(f"<th scope='row'>{esc(str(name))}</th>")
        for c, v in enumerate(vals):
            txt = fmt.format(v) if _num(v) else str(v)
            cls = " class='diag'" if diag and r == c else ""
            t = None
            if callable(heat):
                t = heat(r, c)
            elif heat == "col" and c in bounds and _num(v):
                lo, hi = bounds[c]
                t = (float(v) - lo) / (hi - lo) if hi > lo else 0.5
            style = "" if t is None else f" style='background:rgba({BLUE_RGB},{0.10 + 0.60 * min(max(t, 0.0), 1.0):.2f})'"
            out.append(f"<td{cls}{style}>{esc(txt)}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def df_html(*args, **kwargs):
    st.markdown(table_html(*args, **kwargs), unsafe_allow_html=True)


def matrix_html(A, names):
    """Matrice colorée en bleu : plus la valeur de Saaty est grande, plus la case est intense."""
    L = np.log(9)
    tone = lambda r, c: 0.5 + 0.5 * float(np.clip(np.log(A[r, c]) / L, -1, 1))
    return table_html([(names[i], [frac(v) for v in A[i]]) for i in range(len(names))], names, diag=True, heat=tone)


def matrix_table(A, names):
    st.markdown(matrix_html(A, names), unsafe_allow_html=True)


def twin_cards(title_l, html_l, title_r, html_r, k):
    """Deux blocs côte à côte, exactement de même taille (hauteur fixée selon le nombre de lignes)."""
    h = 130 + 40 * k
    left, right = st.columns(2)
    for col, t, body in ((left, title_l, html_l), (right, title_r, html_r)):
        col.markdown(f"<div class='card eq' style='height:{h}px'><div class='card-t'>{t}</div>{body}</div>",
                     unsafe_allow_html=True)


def bars_html(names, w):
    return "".join(
        f"<div class='wbar'><div class='n' title='{esc(nm)}'>{esc(nm)}</div>"
        f"<div class='t'><div class='f' style='width:{v * 100:.1f}%'></div></div>"
        f"<div class='p'>{v * 100:.1f} %</div></div>" for nm, v in zip(names, w))


def badge(cr: float) -> str:
    if cr < 0.1:
        return f"<span class='pill ok'>Cohérent · CR = {cr:.3f}</span>"
    return f"<span class='pill warn'>À revoir · CR = {cr:.3f}</span>"


def kpi(label, value, sub="", tone=""):
    s = f"<div class='s'>{sub}</div>" if sub else ""
    return f"<div class='kpi {tone}'><div class='l'>{label}</div><div class='v'>{value}</div>{s}</div>"


def section(title, small=False):
    st.markdown(f"<div class='sec{' sm' if small else ''}'>{title}</div>", unsafe_allow_html=True)


def page_header(step, title, subtitle=""):
    sub = f"<div class='psub'>{subtitle}</div>" if subtitle else ""
    live = ""
    if step and step > 1 and valid:
        who = "égalité pour l'instant" if tie else f"<b>{esc(best_name)}</b> · {scores[best_idx]:.3f}"
        live = f"<div class='live'><span class='dot'></span>Meilleur choix actuel : {who}</div>"
    label = f"Étape {step} sur 4" if step else "AHP Calculator"
    st.markdown(f"<div class='phead'><div><div class='eyebrow'>{label}</div>"
                f"<div class='ptitle'>{title}</div></div>{live}</div>{sub}", unsafe_allow_html=True)


def footer_box():
    try:
        return st.container(key="footer_nav")
    except TypeError:
        return st.container()


def app_footer():
    st.markdown("<div class='app-footer'>AHP Calculator 2026</div>", unsafe_allow_html=True)


def footer_nav(page):
    """Pied de page, puis Précédent / Suivant fixés en bas à droite."""
    app_footer()
    idx = ORDER.index(page)
    has_prev, has_next = 0 < idx <= LAST_STEP, idx < LAST_STEP
    with footer_box():
        c1, c2 = st.columns(2)
        if has_prev:
            with c1:
                nav_button("Précédent", "arrow_back", ORDER[idx - 1], key=f"prev_{page}")
        if has_next:
            with c2:
                nav_button("Suivant", "arrow_forward", ORDER[idx + 1], key=f"next_{page}")
        if page == "guide":
            with c2:
                nav_button("Accueil", "home", "home", key="guide_home")


def need_valid():
    if valid:
        return
    st.markdown("<div class='tip'><b>Il manque des informations.</b> Complétez d'abord l'étape 1 "
                "(objectif, critères et alternatives).</div>", unsafe_allow_html=True)
    for e in errors:
        st.error(e)
    nav_button("Aller à l'étape 1", "account_tree", "probleme", key="fix_problem")
    st.stop()


def style_fig(fig, height=360):
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=T["text"], family="Times New Roman, Times, serif"),
        margin=dict(l=10, r=10, t=50, b=10),
        title_font=dict(size=15, color=T["text"]), legend=dict(bgcolor="rgba(0,0,0,0)"),
        colorway=PALETTE)
    fig.update_xaxes(gridcolor=T["border"], zerolinecolor=T["border"], linecolor=T["border"])
    fig.update_yaxes(gridcolor=T["border"], zerolinecolor=T["border"], linecolor=T["border"])
    return fig


def pair_box(key):
    """Carte de comparaison : toutes de la même taille (hauteur minimale fixée en CSS)."""
    try:
        return st.container(key=f"pair_{key}")
    except TypeError:
        return st.container(border=True)


def pairwise_inputs(names, prefix):
    pairs = [(i, j) for i in range(len(names)) for j in range(i + 1, len(names))]
    cols = st.columns(2)
    for idx, (i, j) in enumerate(pairs):
        key = f"{prefix}_{i}_{j}"
        ss.setdefault(key, 0)
        with cols[idx % 2]:
            with pair_box(key):
                st.markdown(f"<div class='pair'><b title='{esc(names[i])}'>{esc(names[i])}</b><i>vs</i>"
                            f"<b title='{esc(names[j])}'>{esc(names[j])}</b></div>", unsafe_allow_html=True)
                k = st.select_slider("Comparaison", options=SCALE_OPTIONS, key=key,
                                     format_func=scale_label, label_visibility="collapsed")
                st.markdown(f"<div class='pair-note'>{sentence_html(names[i], names[j], k)}</div>",
                            unsafe_allow_html=True)


def proj_box(key):
    """Bloc de taille fixe (identique pour « Enregistrer » et « Ouvrir »)."""
    try:
        return st.container(key=key)
    except TypeError:
        return st.container(border=True)


def _fix_choice(key, first):
    if ss.get(key) is None:          # un clic sur la pastille active la désélectionne : on la rétablit
        ss[key] = first


def choice(options, key):
    """Sélecteur moderne en pastilles, centré (remplace onglets et boutons radio)."""
    if ss.get(key) not in options:
        ss.pop(key, None)
    try:
        v = st.pills("Choix", options, selection_mode="single", default=options[0], key=key,
                     label_visibility="collapsed", on_change=_fix_choice, args=(key, options[0]))
    except Exception:                # anciennes versions de Streamlit : boutons radio
        v = st.radio("Choix", options, key=key, horizontal=True, label_visibility="collapsed")
    return v if v in options else options[0]


def composer():
    """Bloc « publication » avec cadre rose (la clé permet de le cibler en CSS)."""
    try:
        return st.container(key="composer")
    except TypeError:
        return st.container(border=True)


# ---------------------------------------------------------------------------
# 5. PAGES
# ---------------------------------------------------------------------------

def page_home():
    # Accueil compact : tout tient dans l'écran, sans défilement
    st.markdown("<style>.block-container{padding-top:1.2rem !important; padding-bottom:5rem !important;}</style>",
                unsafe_allow_html=True)
    st.markdown(
        "<div class='hero compact'><div class='eyebrow'>Analytic Hierarchy Process</div>"
        "<h1>Décidez avec méthode, <span>pas au feeling</span>.</h1>"
        "<div class='lead'>L'AHP (méthode de Saaty) transforme des jugements subjectifs en poids chiffrés. "
        "Comparez vos critères et vos options deux à deux : l'application calcule les priorités, "
        "vérifie la cohérence de vos choix et désigne directement la meilleure alternative.</div></div>",
        unsafe_allow_html=True)
    if valid:
        k = st.columns(4)
        short = esc(goal) if len(goal) < 26 else esc(goal[:24]) + "…"
        k[0].markdown(kpi("Objectif", short, tone="pink compact"), unsafe_allow_html=True)
        k[1].markdown(kpi("Critères", n, "à pondérer", tone="blue compact"), unsafe_allow_html=True)
        k[2].markdown(kpi("Alternatives", m, "à comparer", tone="yellow compact"), unsafe_allow_html=True)
        sub = "aucune préférence saisie" if tie else f"score {scores[best_idx]:.3f}"
        k[3].markdown(kpi("Meilleure option", esc(best_name), sub, tone="dark compact"), unsafe_allow_html=True)
        top = np.argsort(-scores)[:5]
        st.markdown("<div style='height:12px'></div><div class='card'><div class='card-t'>Classement actuel</div>"
                    + bars_html([alts[i] for i in top], [scores[i] for i in top]) + "</div>",
                    unsafe_allow_html=True)
    else:
        st.info("Projet incomplet : " + " ".join(errors))
    footer_nav("home")


def page_probleme():
    page_header(1, "Problème", "Décrivez votre décision. Les critères et les alternatives peuvent être "
                "ceux de n'importe quel scénario : tout est recalculé automatiquement.")
    if valid:
        q = lambda s: s.replace('"', "'")
        dot = ('digraph H { rankdir=TB; bgcolor="transparent"; nodesep=0.3; ranksep=0.9; '
               f'node [shape=box, style="rounded,filled", fillcolor="{T["surf"]}", color="{PINK}", '
               f'fontcolor="{T["text"]}", fontname="Times-Roman", margin="0.2,0.1"]; edge [color="{T["muted"]}"];\n'
               f'"{q(goal)}" [fillcolor="{PINK}", fontcolor="#0B0B0F", color="{PINK}"];\n')
        for c in crit:
            dot += f'"{q(goal)}" -> "{q(c)}";\n'
        for c in crit:
            for a in alts:
                dot += f'"{q(c)}" -> "{q(a)}";\n'
        dot += "}"
        st.graphviz_chart(dot)

    with composer():
        st.markdown("<div class='post-head'><div class='avatar'>HS</div><div><b>Harbouli Salwa</b>"
                    "<span>Nouveau problème de décision · à l'instant</span></div></div>", unsafe_allow_html=True)
        st.text_input("Objectif de la décision", key="goal", label_visibility="collapsed",
                      placeholder="Quelle décision voulez-vous prendre ?")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<div class='flabel'>Critères<em>un par ligne · 2 à 10</em></div>", unsafe_allow_html=True)
            st.text_area("Critères", key="crit_text", height=160, label_visibility="collapsed",
                         placeholder="Expérience\nÉducation\nCharisme\nÂge")
        with c2:
            st.markdown("<div class='flabel'>Alternatives<em>une par ligne · 2 à 10</em></div>", unsafe_allow_html=True)
            st.text_area("Alternatives", key="alt_text", height=160, label_visibility="collapsed",
                         placeholder="Pers 1\nPers 2\nPers 3")
        chips = "".join(f"<span class='chip pink'>#{esc(c)}</span>" for c in crit) \
            + "".join(f"<span class='chip blue'>@{esc(a)}</span>" for a in alts)
        if chips:
            st.markdown(f"<div class='chips'>{chips}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='stats'><span><b>{n}</b>critères</span><span><b>{m}</b>alternatives</span>"
                    f"<span><b>{n * (n - 1) // 2}</b>comparaisons de critères</span>"
                    f"<span><b>{m * (m - 1) // 2}</b>par critère pour les alternatives</span></div>",
                    unsafe_allow_html=True)
        for e in errors:
            st.error(e)
        st.markdown("<div class='flabel'>Charger un autre scénario</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for col, (name, icon) in zip(cols, [("Candidat", "person"), ("Voiture", "directions_car"),
                                            ("Fournisseur", "local_shipping"), ("Projet vide", "add_circle")]):
            with col:
                button(name, icon, f"tpl_{name}", apply_template, (name,))

    section("Enregistrer ou ouvrir un projet", small=True)
    p1, p2 = st.columns(2)
    with p1:
        st.download_button("Enregistrer le projet (.json)",
                           project_json(ss.get("goal", ""), crit, alts) if valid else b"",
                           file_name="projet_ahp.json", mime="application/json", disabled=not valid,
                           key="dl_proj")
    with p2:
        st.file_uploader("Ouvrir un projet", type=["json"], key="proj_file", on_change=load_project,
                         label_visibility="collapsed")
    if ss.pop("_load_error", False):
        st.error("Fichier illisible : ouvrez un projet enregistré par cette application (.json).")
    footer_nav("probleme")


def page_criteres():
    need_valid()
    page_header(2, "Critères", "Pour chaque paire, indiquez quel critère est le plus important et dans "
                "quelle mesure. La matrice et les poids se calculent automatiquement.")
    pairwise_inputs(crit, "crit")
    twin_cards("Matrice des comparaisons", matrix_html(A_crit, crit), "Aperçu sur les critères",
               bars_html(crit, w_crit) + f"<div style='margin-top:8px'>{badge(cr_crit)}</div>", n)
    footer_nav("criteres")


def page_alternatives():
    need_valid()
    page_header(3, "Alternatives", "Pour chaque critère, comparez les alternatives entre elles : "
                "la matrice et l'aperçu s'affichent au fur et à mesure.")
    sel = choice(crit, "pick_crit")
    c = crit.index(sel)
    pairwise_inputs(alts, f"alt{c}")
    A = matrix_from_state(f"alt{c}", m)
    w = geometric_priorities(A)[2]
    cr = consistency(A, w)[3]
    twin_cards(f"Matrice · {esc(crit[c])}", matrix_html(A, alts), "Aperçu sur les alternatives",
               bars_html(alts, w) + f"<div style='margin-top:8px'>{badge(cr)}</div>", m)
    footer_nav("alternatives")


def detail_content(names, A):
    """Calcul pas à pas d'une matrice (utile pour vérifier à la main)."""
    p, g, w = geometric_priorities(A)
    lam, ci, ri, cr, Aw, ratios = consistency(A, w)
    k = len(names)
    st.markdown("**1 · Matrice de comparaison**")
    matrix_table(A, names)
    st.markdown(f"**2 · Moyenne géométrique** (racine {k}-ième du produit de chaque ligne) puis **normalisation**")
    df_html([(names[i], [p[i], g[i], w[i], Aw[i], ratios[i]]) for i in range(k)],
            ["Produit de la ligne", f"Racine {k}-ième", "Priorité (normalisée)", "A × w", "(A × w) / w"],
            corner="", heat="col")
    st.caption(f"Somme des moyennes géométriques = {g.sum():.4f} · somme des priorités = {w.sum():.4f}")
    st.markdown("**3 · Cohérence**")
    c = st.columns(4)
    c[0].markdown(kpi("λmax", f"{lam:.4f}", "moyenne de (A×w)/w"), unsafe_allow_html=True)
    c[1].markdown(kpi("CI", f"{ci:.4f}", "(λmax − n) / (n − 1)"), unsafe_allow_html=True)
    c[2].markdown(kpi(f"RI (n = {k})", f"{ri:.2f}", "tableau de Saaty"), unsafe_allow_html=True)
    c[3].markdown(kpi("CR", f"{cr:.4f}", "CI / RI"), unsafe_allow_html=True)
    st.markdown(f"<div style='margin-top:10px'>{badge(cr)}</div>", unsafe_allow_html=True)


def build_excel():
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xl:
        pd.DataFrame(A_crit, index=crit, columns=crit).to_excel(xl, sheet_name="Matrice criteres")
        pd.DataFrame({"Poids": w_crit}, index=crit).to_excel(xl, sheet_name="Poids criteres")
        for c in range(n):
            pd.DataFrame(alt_mats[c], index=alts, columns=alts).to_excel(xl, sheet_name=f"Alt {c + 1}"[:31])
        pd.DataFrame(local, index=alts, columns=crit).to_excel(xl, sheet_name="Priorites locales")
        rk = pd.DataFrame({"Score": scores}, index=alts).sort_values("Score", ascending=False)
        rk.insert(0, "Rang", range(1, m + 1))
        rk.to_excel(xl, sheet_name="Classement")
    return buf.getvalue()


def page_resultats():
    need_valid()
    page_header(4, "Résultats", "Score global de chaque alternative : somme des priorités locales "
                "pondérées par le poids des critères.")
    order = np.argsort(-scores)
    if tie:
        st.markdown("<div class='win'><div><div class='eyebrow'>Résultat</div><div class='big'>Égalité</div></div>"
                    "<div class='score'>Aucune préférence saisie : toutes les options ont le même score.</div></div>",
                    unsafe_allow_html=True)
    else:
        st.markdown(
            f"<div class='win'><div><div class='eyebrow'>Meilleure alternative</div>"
            f"<div class='big'>{esc(alts[best_idx])}</div></div>"
            f"<div class='score'><b>{scores[best_idx]:.4f}</b>{scores[best_idx] * 100:.1f} % de la priorité totale</div></div>",
            unsafe_allow_html=True)
    if not all_ok:
        st.warning("Attention : au moins une matrice est incohérente (CR ≥ 0,1). "
                   "Le classement est à interpréter avec prudence (voir « Cohérence » plus bas).")

    # --- Graphiques et courbes en premier ---
    g1, g2 = st.columns(2)
    with g1:
        fig = go.Figure(go.Bar(
            x=[scores[i] for i in order], y=[alts[i] for i in order], orientation="h",
            marker_color=[PINK if r == 0 else BLUE_HEX for r in range(m)],
            text=[f"{scores[i]:.3f}" for i in order], textposition="outside"))
        fig.update_layout(title="Scores finaux", yaxis=dict(autorange="reversed"))
        st.plotly_chart(style_fig(fig, 330), theme=None)
    with g2:
        fig = go.Figure(go.Bar(x=crit, y=w_crit, marker_color=YELLOW,
                               text=[f"{v:.3f}" for v in w_crit], textposition="outside"))
        fig.update_layout(title="Poids des critères")
        st.plotly_chart(style_fig(fig, 330), theme=None)
    g3, g4 = st.columns(2)
    with g3:
        fig = go.Figure()
        for c in range(n):
            fig.add_bar(name=crit[c], x=alts, y=local[:, c] * w_crit[c], marker_line=dict(color=T["bg"], width=1.5))
        fig.update_layout(barmode="stack", title="Contribution de chaque critère au score")
        st.plotly_chart(style_fig(fig, 360), theme=None)
    with g4:
        fig = go.Figure()
        for a in range(m):
            fig.add_trace(go.Scatterpolar(r=list(local[a]) + [local[a, 0]], theta=crit + [crit[0]],
                                          name=alts[a], fill="toself", opacity=0.55))
        fig.update_layout(title="Profil des alternatives (priorités locales)",
                          polar=dict(bgcolor="rgba(0,0,0,0)",
                                     radialaxis=dict(gridcolor=T["border"], linecolor=T["border"],
                                                     tickfont=dict(color=T["muted"])),
                                     angularaxis=dict(gridcolor=T["border"], linecolor=T["border"])))
        st.plotly_chart(style_fig(fig, 360), theme=None)

    section("Courbes de sensibilité", small=True)
    sel = choice(crit, "sens_crit")
    c = crit.index(sel)
    xs = np.linspace(0, 1, 41)
    others = np.delete(w_crit, c)
    fig = go.Figure()
    for a in range(m):
        ys = []
        for x in xs:
            w2 = np.empty(n)
            w2[c] = x
            w2[np.arange(n) != c] = (1 - x) * others / others.sum()
            ys.append(float(local[a] @ w2))
        fig.add_scatter(x=xs, y=ys, name=alts[a], mode="lines", line=dict(width=3))
    fig.add_vline(x=float(w_crit[c]), line_dash="dot", line_color=YELLOW,
                  annotation_text="poids actuel", annotation_font_color=YELLOW)
    fig.update_layout(title=f"Score selon le poids de « {sel} » (les autres poids restent proportionnels)",
                      xaxis_title="Poids du critère", yaxis_title="Score global")
    st.plotly_chart(style_fig(fig, 380), theme=None)
    st.caption("Si deux courbes se croisent près du poids actuel, le classement est fragile.")

    # --- Tableaux ---
    section("Classement final", small=True)
    df_html([(alts[i], [r + 1, f"{scores[i]:.4f}", f"{scores[i] * 100:.1f} %"]) for r, i in enumerate(order)],
            ["Rang", "Score", "Part"], corner="Alternative", highlight=None if tie else 0)
    tl, tr = st.columns(2)
    with tl:
        section("Poids des critères", small=True)
        df_html([(crit[c], [w_crit[c]]) for c in range(n)], ["Poids"], corner="Critère", heat="col")
    with tr:
        section("Priorités locales", small=True)
        df_html([(alts[a], list(local[a])) for a in range(m)], crit, corner="", heat="col")
    section("Cohérence des jugements", small=True)
    df_html([(k, [f"{v:.4f}", "Cohérent" if v < 0.1 else "À revoir"]) for k, v in crs.items()],
            ["CR", "Verdict"], corner="Matrice")

    # --- Détail des calculs : optionnel, replié ---
    with st.expander("Détail des calculs (optionnel : pour vérifier à la main)"):
        labels = ["Critères"] + [f"Alternatives · {c}" for c in crit]
        pick = choice(labels, "detail_sel")
        idx = labels.index(pick)
        if idx == 0:
            detail_content(crit, A_crit)
        else:
            detail_content(alts, alt_mats[idx - 1])
        st.markdown("**Score final** = Σ (priorité locale × poids du critère)")
        for a in range(m):
            terms = " + ".join(f"{local[a, c]:.4f}×{w_crit[c]:.4f}" for c in range(n))
            st.markdown(f"**{alts[a]}** = {terms} = **{scores[a]:.4f}**")

    try:
        st.download_button("Télécharger les résultats (Excel)", build_excel(), file_name="resultats_ahp.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except ImportError:
        st.info("Installez openpyxl (pip install openpyxl) pour activer l'export Excel.")
    footer_nav("resultats")


def page_guide():
    st.markdown(
        "<div class='hero compact'><div class='eyebrow'>Guide</div>"
        "<h1>La méthode AHP en <span>5 minutes</span></h1>"
        "<div class='lead'>Principe, échelle de Saaty, formules, pièges à éviter, et réglage de l'apparence.</div></div>",
        unsafe_allow_html=True)
    gsel = choice(["Comprendre", "Échelle de Saaty", "Formules", "Pièges à éviter", "Apparence"], "guide_tab")
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    if gsel == "Comprendre":
        st.markdown(
            "<div class='ggrid'>"
            "<div class='gcard'><div class='n'>1</div><h4>Décomposer</h4><div class='d'>Un objectif, "
            "des critères pour le juger, des alternatives à départager.</div></div>"
            "<div class='gcard b'><div class='n'>2</div><h4>Comparer</h4><div class='d'>Deux éléments à la "
            "fois, sur l'échelle de Saaty : plus simple et plus fiable qu'un classement global.</div></div>"
            "<div class='gcard y'><div class='n'>3</div><h4>Décider</h4><div class='d'>Les comparaisons "
            "deviennent des poids ; on vérifie leur cohérence, puis on calcule le score de chaque option.</div></div>"
            "</div>", unsafe_allow_html=True)
        st.markdown("<div class='tip'><b>Dans l'application :</b> saisissez le problème (étape 1), comparez les "
                    "critères (étape 2) puis les alternatives pour chaque critère (étape 3). Le meilleur choix est "
                    "calculé en direct et affiché à l'étape 4.</div>", unsafe_allow_html=True)

    if gsel == "Échelle de Saaty":
        st.markdown("<div class='scale'>"
                    "<div class='s'><b>1</b><span>Importance égale</span></div>"
                    "<div class='s'><b>3</b><span>Modérément plus important</span></div>"
                    "<div class='s'><b>5</b><span>Fortement plus important</span></div>"
                    "<div class='s'><b>7</b><span>Très fortement plus important</span></div>"
                    "<div class='s'><b>9</b><span>Importance extrême</span></div></div>", unsafe_allow_html=True)
        st.caption("2, 4, 6 et 8 sont des valeurs intermédiaires. Réciprocité : si A vaut x fois B, "
                   "alors B vaut 1/x de A. La diagonale vaut toujours 1.")

    if gsel == "Formules":
        a, b = st.columns(2)
        with a:
            st.markdown("**Moyenne géométrique d'une ligne** (n éléments)")
            st.latex(r"g_i = \sqrt[n]{\prod_{j=1}^{n} a_{ij}}")
            st.markdown("**Priorité (normalisation)**")
            st.latex(r"w_i = \frac{g_i}{\sum_k g_k}")
        with b:
            st.markdown("**Indice de consistance**")
            st.latex(r"CI = \frac{\lambda_{max} - n}{n - 1}")
            st.markdown("**Ratio de cohérence**")
            st.latex(r"CR = \frac{CI}{RI} \quad (\text{cohérent si } CR < 0{,}1)")
        st.markdown("**Score global d'une alternative**")
        st.latex(r"S(a) = \sum_{c} p_c(a) \times w_c")
        st.markdown("**Indice aléatoire RI** (selon la taille n de la matrice)")
        df_html([("RI", [f"{RI_TABLE[k]:.2f}" for k in range(3, 11)])], [str(k) for k in range(3, 11)], corner="n")

    if gsel == "Pièges à éviter":
        for txt in ["<b>Oublier la réciprocité</b> : écrire 3 au lieu de 1/3 dans la case symétrique.",
                    "<b>Ne pas normaliser</b> : les priorités doivent sommer à 1.",
                    "<b>Utiliser le mauvais RI</b> : il dépend de la taille de chaque matrice (0,90 pour 4×4, 0,58 pour 3×3).",
                    "<b>Ne vérifier que les critères</b> : la cohérence des matrices d'alternatives compte aussi.",
                    "<b>Abuser du 9</b> : les valeurs extrêmes fragilisent la cohérence."]:
            st.markdown(f"<div class='err'><span>⚠</span><div>{txt}</div></div>", unsafe_allow_html=True)
        with st.expander("Que faire si CR ≥ 0,1 ?"):
            st.markdown("Repérez la comparaison la plus extrême ou la plus discutable, rapprochez-la de 1, "
                        "puis regardez le CR se mettre à jour. Recommencez jusqu'à passer sous 0,1.")

    if gsel == "Apparence":
        st.markdown("**Mode d'affichage**")
        ss["theme_pick"] = ss["theme"]
        try:
            st.pills("Thème de l'application", list(THEMES), selection_mode="single", key="theme_pick",
                     on_change=set_theme, label_visibility="collapsed")
        except Exception:
            st.radio("Thème de l'application", list(THEMES), key="theme_pick", horizontal=True,
                     label_visibility="collapsed", on_change=set_theme)
        st.markdown("<div class='swatch'><div class='d'>Mode sombre<br><small>Noir, rose, bleu et jaune</small></div>"
                    "<div class='l'>Mode clair<br><small>Fond clair, mêmes accents</small></div></div>",
                    unsafe_allow_html=True)
        st.caption("Le changement s'applique à toute l'application.")
    footer_nav("guide")


# ---------------------------------------------------------------------------
# 6. BARRE LATÉRALE ET ROUTAGE
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("<div class='brand'><div class='logo'>AHP</div><b>AHP Calculator</b>"
                "<small>Aide à la décision multicritère</small></div>", unsafe_allow_html=True)
    for key, label, icon in PAGES:
        try:
            st.button(label, icon=f":material/{icon}:", key=f"nav_{key}", on_click=go_to, args=(key,),
                      type="primary" if ss["page"] == key else "secondary")
        except Exception:
            st.button(label, key=f"nav_{key}", on_click=go_to, args=(key,),
                      type="primary" if ss["page"] == key else "secondary")
    st.markdown("<div class='credit'>Réalisée par<b>Harbouli Salwa</b></div>", unsafe_allow_html=True)

ROUTES = {"home": page_home, "probleme": page_probleme, "criteres": page_criteres,
          "alternatives": page_alternatives, "resultats": page_resultats, "guide": page_guide}
ROUTES.get(ss["page"], page_home)()
