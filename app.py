# app.py — Home page for FP&A Copilot
import streamlit as st

st.set_page_config(page_title="FP&A Copilot", layout="wide")

# Hide Streamlit’s default page list
st.markdown("""
    <style>
      [data-testid="stSidebarNav"] { display: none; }

      /* Center hero vertically & horizontally */
      .hero {
        min-height: calc(100vh - 6rem);
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
      }
      .hero h1 {
        font-size: clamp(2.6rem, 5vw, 4.2rem);
        line-height: 1.1;
        margin: 0 0 0.5rem 0;
        letter-spacing: 0.2px;
      }
      .tagline { font-size: clamp(1.05rem, 1.6vw, 1.25rem); opacity: .92; margin: .25rem 0 1.1rem 0; }
      .desc    { font-size: 1rem; opacity: .85; margin-bottom: 1.25rem; }
      .dev     { margin-top: 1.25rem; opacity: .9; font-style: italic; }
      .thin-divider { height: 1px; background: linear-gradient(90deg, transparent, rgba(255,255,255,.18), transparent);
                      margin: 1.25rem auto 0 auto; width: min(720px, 92%); }
    </style>
""", unsafe_allow_html=True)

# Sidebar (minimal nav)
st.sidebar.title("Sections")
choice = st.sidebar.radio("", ["🏠 Home", "🤖 Agent"], index=0, label_visibility="collapsed")

# Route to Agent page
if choice == "🤖 Agent":
    try:
        st.switch_page("pages/1_Agent.py")
    except Exception:
        try:
            st.page_link("pages/1_Agent.py", label="Open Agent", icon="🤖")
        except Exception:
            st.warning("Could not open Agent page. Make sure pages/1_Agent.py exists.")

# ---------- Home (centered hero) ----------
st.markdown(
    """
    <div class="hero">
      <div>
        <h1>FP&amp;A Copilot 🧮</h1>
        <p class="tagline">A Mini Financial Planning &amp; Analysis Assistant</p>
        <p class="desc">
          Answers finance questions directly from <code>fixtures/data.xlsx</code><br/>
          with <b>actuals</b>, <b>budget</b>, <b>fx</b>, and <b>cash</b> sheets.
        </p>
        <p class="dev"><b>Developed by:</b> Srividya Srinivasula</p>
        <div class="thin-divider"></div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


st.info("👉 Use **Sections → Agent** to chat with the FP&A assistant.")
