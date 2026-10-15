"""Dark-blue HF-PathGuard demo theme inspired by the supplied mockup."""
STYLE = """
<style>
 .stApp {background:linear-gradient(135deg,#f2f7ff 0%,#fafcff 60%,#eef5ff 100%);}
 /* Keep Streamlit's dark-theme defaults from making headings invisible on light panels. */
 [data-testid="stMain"] {color:#193453;color-scheme:light;}
 [data-testid="stMain"] h1,
 [data-testid="stMain"] h2,
 [data-testid="stMain"] h3,
 [data-testid="stMain"] h4,
 [data-testid="stMain"] h5,
 [data-testid="stMain"] h6,
 [data-testid="stMain"] [data-testid="stWidgetLabel"] *,
 [data-testid="stMain"] [data-testid="stMarkdownContainer"] > p,
 [data-testid="stMain"] [data-testid="stMarkdownContainer"] > div > p,
 [data-testid="stMain"] [data-testid="stCaptionContainer"] * {
   color:#193453 !important;
 }
 [data-testid="stMain"] [data-baseweb="input"],
 [data-testid="stMain"] [data-baseweb="select"],
 [data-testid="stMain"] [data-baseweb="textarea"],
 [data-testid="stMain"] [data-testid="stTextInput"] input,
 [data-testid="stMain"] [data-testid="stNumberInput"] input {
   background:#fff !important;color:#163252 !important;border-color:#c9dcf3 !important;
 }
 [data-testid="stMain"] input,
 [data-testid="stMain"] textarea {color:#163252 !important;caret-color:#1663c8 !important;}
 [data-testid="stMain"] [data-baseweb="radio"] * {color:#193453;}
 [data-testid="stMain"] [data-testid="stDataFrame"] {background:#fff;border:1px solid #d6e4f5;border-radius:10px;}
 [data-testid="stMain"] .hf-hero h1,
 [data-testid="stMain"] .hf-hero p,
 [data-testid="stMain"] .hf-workflow h1,
 [data-testid="stMain"] .hf-workflow h2,
 [data-testid="stMain"] .hf-workflow p {color:#fff !important;}
 .block-container {padding-top:1.1rem;max-width:1500px;}
 [data-testid="stSidebar"] {background:#102341;}
 [data-testid="stSidebar"] * {color:#e6efff !important;}
 .hf-hero {border-radius:14px;padding:19px 25px;background:linear-gradient(110deg,#0b1f3c,#143767);color:#fff;margin-bottom:18px;}
 .hf-hero h1 {font-weight:780;font-size:28px;margin:0;color:#fff;}
 .hf-hero p {font-size:13px;color:#c7ddff;margin:4px 0 0;}
 .hf-panel {background:#fff;border:1px solid #dde7f8;border-radius:12px;padding:14px 18px;margin:8px 0;box-shadow:0 4px 16px #23436612;}
 .hf-panel h4 {margin:0 0 7px;color:#163766;}
 .hf-status {border-radius:12px;padding:16px 18px;background:#fff0f1;border:1px solid #ffc5cf;color:#ab1833;}
 .hf-agentbox {border-radius:11px;padding:15px;background:#fff;border:1px solid #d8e6fa;min-height:174px;}
 .hf-muted {color:#637b9b;font-size:12px;}
 .hf-network {padding:20px 10px;background:radial-gradient(circle,#18457c,#0c1b33);border-radius:14px;color:#fff;text-align:center;}
 .hf-network .agent {display:inline-block;min-width:110px;border:1px solid #5a8bc5;background:#193e6c;padding:10px;margin:5px;border-radius:10px;font-size:13px;}
 .hf-network .chief {background:#1670d9;border-radius:99px;padding:18px;width:165px;margin:0 auto 12px;font-weight:700;}
 /* The original seven-robot artwork never moves. Only status overlays animate. */
 .hf-workflow {background:#0b1d39;color:#fff;border-radius:14px;overflow:hidden;border:1px solid #29496f;box-shadow:0 9px 24px #10284624;}
 .hf-workflow-title {display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 15px;background:#102544;}
 .hf-workflow-title b {font-size:17px;color:#f4f8ff;}
 .hf-workflow-title span {font-size:11px;color:#afc9e9;}
 .hf-workflow-stage {position:relative;aspect-ratio:665 / 407;background-repeat:no-repeat;background-size:231% 251.6%;background-position:51% 14.1%;}
 .hf-agent-status {position:absolute;width:24%;box-sizing:border-box;padding:7px 9px;border:1px solid #5079a7;border-radius:11px;background:rgba(12,31,61,.97);box-shadow:0 4px 12px #0007;color:#eff7ff;font-size:11px;z-index:2;}
 .hf-agent-line {display:flex;justify-content:space-between;align-items:center;gap:4px;font-size:11px;font-weight:650;}
 .hf-agent-line strong {font-variant-numeric:tabular-nums;font-size:12px;color:#d7eeff;}
 .hf-agent-status small {display:block;margin-top:3px;color:#c0d1e9;font-size:10px;}
 .hf-progress-track {height:6px;border-radius:20px;overflow:hidden;background:#334969;margin-top:6px;}
 .hf-progress-fill {height:100%;background:#36b5ff;border-radius:20px;transition:width .45s ease;}
 .hf-cardiology .hf-progress-fill {background:#ff6d9b;}
 .hf-nephrology .hf-progress-fill {background:#35b4ff;}
 .hf-pharmacy .hf-progress-fill {background:#bd8cff;}
 .hf-evidence .hf-progress-fill {background:#54e7a7;}
 .hf-similarity .hf-progress-fill {background:#b9cde7;}
 .hf-safety .hf-progress-fill {background:#ffc065;}
 .hf-final .hf-progress-fill {background:#26dcff;}
 .hf-running .hf-progress-fill {width:45% !important;animation:hf-working 1.2s ease-in-out infinite alternate;}
 .hf-running .hf-agent-line strong {color:#78daff;}
 .hf-completed {border-color:#3b9e88;}
 .hf-failed {border-color:#ff6b7b;}
 .hf-failed .hf-progress-fill {background:#ff6b7b;}
 @keyframes hf-working {0%{transform:translateX(-90%);opacity:.45}100%{transform:translateX(190%);opacity:1}}
 .hf-workflow-foot {display:flex;justify-content:space-between;gap:10px;padding:9px 14px;background:#102544;font-size:11px;color:#bad1ed;}
 .hf-workflow-foot b {color:white;}
 .hf-workflow-foot span {opacity:.75;}
 @media(max-width:920px){.hf-agent-status{padding:4px;font-size:9px}.hf-agent-line{font-size:9px}.hf-agent-line strong{font-size:9px}.hf-agent-status small{font-size:8px}.hf-workflow-title span,.hf-workflow-foot span{display:none}}
 [data-testid="stMetric"] {background:#fff;padding:10px;border-radius:10px;border:1px solid #d8e6fa;}
</style>
"""
