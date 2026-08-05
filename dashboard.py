"""
Trading-terminal style dashboard -- run and open in your browser.

    streamlit run dashboard.py

Read-only. Reads everything from output/healthcare.db (see db.py) which
lives on this computer -- nothing here is ever uploaded anywhere. No
trade is ever placed from here. Refresh your browser after running
main.py again to see the latest numbers; the top ticker strip and alert
panel also auto-refresh every 60 seconds on their own.

Accessibility: use "Display size" in the sidebar to make everything
bigger, and "Go to page" to jump straight to a section instead of
scrolling through everything.
"""

import datetime as dt
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

import config
import db
import explain

st.set_page_config(page_title="Healthcare & Pharma AI Terminal", layout="wide", page_icon="📈",
                    initial_sidebar_state="expanded")

# ---- Bloomberg TradingView AI Terminal theme (same palette as the Power BI build) ----
BG, CARD, BORDER = "#0B1220", "#162235", "#26334A"
BLUE, GREEN, RED, AMBER, GREY = "#2D8CFF", "#00C853", "#FF5252", "#FFC107", "#8A93A6"
TEXT, SUBTEXT = "#FFFFFF", "#C9D1D9"

# =========================
# SIDEBAR: ACCESSIBILITY + NAVIGATION
# =========================

st.sidebar.markdown("### ⚙️ Display Settings")
size_choice = st.sidebar.radio(
    "Text & visual size", ["Normal", "Large", "Extra Large"], index=1,
    help="Makes fonts, charts and tables bigger or smaller everywhere on the page.",
)
BASE_PX = {"Normal": 16, "Large": 20, "Extra Large": 25}[size_choice]
CHART_TITLE_PX = {"Normal": 16, "Large": 20, "Extra Large": 24}[size_choice]
CHART_AXIS_PX = {"Normal": 13, "Large": 16, "Extra Large": 19}[size_choice]
CHART_H = {"Normal": 380, "Large": 440, "Extra Large": 520}[size_choice]
GAUGE_H = {"Normal": 240, "Large": 280, "Extra Large": 340}[size_choice]

st.sidebar.markdown("---")
st.sidebar.markdown("### 📂 Navigation")
PAGES = [
    "🗺️ Overview",
    "📊 Predictions & Recommendations",
    "🧪 Backtest & Accuracy",
    "💼 Portfolio (Paper Trading)",
    "🏦 Institution Activity",
]
page = st.sidebar.radio("Go to page", PAGES, label_visibility="collapsed")

st.markdown(f"""
<style>
html, body, [class*="css"]  {{ font-family: 'Segoe UI', sans-serif !important; }}
.stApp {{ background-color: {BG}; }}
.stApp, .stApp p, .stApp span, .stApp label, .stMarkdown {{ font-size: {BASE_PX}px !important; color: {TEXT}; }}
section[data-testid="stSidebar"] {{ background-color: {CARD}; border-right: 1px solid {BORDER}; }}
section[data-testid="stSidebar"] * {{ font-size: {BASE_PX}px !important; }}
h1 {{ font-size: {BASE_PX * 2.2:.0f}px !important; font-weight: 600 !important; }}
h2 {{ font-size: {BASE_PX * 1.7:.0f}px !important; font-weight: 600 !important; }}
h3 {{ font-size: {BASE_PX * 1.35:.0f}px !important; font-weight: 600 !important; }}
[data-testid="stMetricValue"] {{ font-size: {BASE_PX * 1.9:.0f}px !important; }}
[data-testid="stMetricLabel"] {{ font-size: {BASE_PX * 0.9:.0f}px !important; color: {SUBTEXT} !important; }}
[data-testid="stMetricDelta"] {{ font-size: {BASE_PX * 1.05:.0f}px !important; }}
.stDataFrame, .stDataFrame * {{ font-size: {BASE_PX * 0.95:.0f}px !important; }}
button[data-baseweb="tab"] {{ font-size: {BASE_PX}px !important; }}
.panel {{ background-color: {CARD}; border-radius: 12px; padding: 16px 18px; margin-bottom: 12px; border: 1px solid {BORDER}; }}
.alert-buy {{ border-left: 5px solid {GREEN}; padding: 10px 14px; margin: 6px 0; background-color: #0F2318; border-radius: 6px; }}
.alert-sell {{ border-left: 5px solid {RED}; padding: 10px 14px; margin: 6px 0; background-color: #2A1414; border-radius: 6px; }}
.alert-warn {{ border-left: 5px solid {AMBER}; padding: 10px 14px; margin: 6px 0; background-color: #2A2013; border-radius: 6px; }}
</style>
""", unsafe_allow_html=True)


def style_fig(fig, height=None):
    fig.update_layout(
        font=dict(family="Segoe UI, sans-serif", size=CHART_AXIS_PX, color=TEXT),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=height or CHART_H,
    )
    # Only touch the figure-level title font if a title was actually set.
    # Setting title_font with no title text is what was rendering the
    # literal word "undefined" above every gauge (gauges have their own
    # internal title, not a figure-level one) -- this guard fixes that.
    if fig.layout.title and fig.layout.title.text:
        fig.update_layout(title_font=dict(size=CHART_TITLE_PX))
    return fig


# =========================
# DATA LOADING
# =========================

@st.cache_data(ttl=60)
def load_all():
    return {
        "latest": db.load_table("predictions_latest"),
        "history": db.load_table("predictions"),
        "news": db.load_table("news_archive"),
        "indexes": db.load_table("market_indexes"),
        "accuracy_summary": db.load_table("accuracy_summary"),
        "accuracy_detail": db.load_table("accuracy_detail"),
        "paper_trades": db.load_table("paper_trades"),
        "timeline": db.load_table("predictions_timeline"),
    }


data = load_all()
latest = data["latest"]

st.title("📈 Healthcare & Pharma AI Trading Terminal")
st.caption("All data stays on this computer -- read from a local file only, nothing is uploaded anywhere.")


# =========================
# TOP TICKER STRIP (auto-refreshing, shown on every page)
# =========================

@st.fragment(run_every="60s")
def ticker_strip():
    d = db.load_table("market_indexes")
    cols = st.columns(6)
    if config.AUTOMATION_ENABLED:
        cols[0].markdown(f"**Automation**  \n:green[● ON ({config.AUTOMATION_MODE})]")
    else:
        cols[0].markdown("**Automation**  \n:red[● OFF]")
    hist = db.load_table("predictions")
    last_date = hist["Prediction Date"].max() if not hist.empty else "—"
    cols[1].markdown(f"**Last Run**  \n{last_date}")
    if not d.empty:
        latest_idx = d.sort_values("Date").groupby("Index").tail(1)
        for i, (_, r) in enumerate(latest_idx.iterrows()):
            if i + 2 >= len(cols):
                break
            arrow = "▲" if r["Day Return (%)"] >= 0 else "▼"
            cols[i + 2].markdown(
                f"**{r['Index']}**  \n{r['Close']:.2f}  "
                f":{'green' if r['Day Return (%)'] >= 0 else 'red'}[{arrow} {r['Day Return (%)']:.2f}%]"
            )
    st.caption(f"Auto-refreshes every 60s · {dt.datetime.now().strftime('%H:%M:%S')}")


ticker_strip()
st.divider()

if latest.empty:
    st.warning("No predictions yet. Run `python main.py` first, then reload this page.")
    st.stop()


# =========================
# ALERT PANEL (shown on every page)
# =========================

def build_alerts(df: pd.DataFrame):
    alerts = []
    for _, r in df.iterrows():
        rec = r.get("Recommendation")
        conf = r.get("Prediction Confidence (%)")
        if rec in ("STRONG BUY", "BUY"):
            alerts.append(("buy", f"{r['Company']}: {rec} · {r.get('Expected Return (%)', 0):+.1f}% expected · {conf:.0f}% confidence"))
        elif rec in ("STRONG SELL", "SELL"):
            alerts.append(("sell", f"{r['Company']}: {rec} · {r.get('Expected Return (%)', 0):+.1f}% expected · {conf:.0f}% confidence"))
        if r.get("Signal Agreement") == "Disagreement":
            alerts.append(("warn", f"{r['Company']}: Recommendation and AI Score disagree -- needs manual review"))
        if pd.notna(conf) and conf < 60:
            alerts.append(("warn", f"{r['Company']}: low model confidence ({conf:.0f}%) -- treat prediction cautiously"))
    return alerts


with st.container():
    st.subheader("🔔 Alert Panel")
    alerts = build_alerts(latest)
    if not alerts:
        st.caption("No alerts right now.")
    else:
        buy_a = [a for k, a in alerts if k == "buy"]
        sell_a = [a for k, a in alerts if k == "sell"]
        warn_a = [a for k, a in alerts if k == "warn"]
        c1, c2 = st.columns(2)
        with c1:
            for a in buy_a:
                st.markdown(f'<div class="alert-buy">🟢 {a}</div>', unsafe_allow_html=True)
            for a in sell_a:
                st.markdown(f'<div class="alert-sell">🔴 {a}</div>', unsafe_allow_html=True)
        with c2:
            for a in warn_a[:8]:
                st.markdown(f'<div class="alert-warn">🟡 {a}</div>', unsafe_allow_html=True)

st.divider()


# =========================
# PAGE: OVERVIEW
# =========================

if page == "🗺️ Overview":
    st.subheader("🗺️ Market Heatmap")
    st.caption("Box size = AI Opportunity Score, color = expected return. Each box is one company, grouped by sector.")
    heat_df = latest.dropna(subset=["Expected Return (%)", "AI Opportunity Score"]).copy()
    if not heat_df.empty:
        heat_df["Size"] = heat_df["AI Opportunity Score"].clip(lower=1)
        fig = px.treemap(
            heat_df, path=[px.Constant("All"), "Sector", "Company"], values="Size",
            color="Expected Return (%)", color_continuous_scale=[RED, "#3A3F4B", GREEN],
            color_continuous_midpoint=0,
            hover_data={"Prediction Confidence (%)": True, "Recommendation": True},
        )
        fig.update_traces(textfont_size=CHART_AXIS_PX + 2)
        style_fig(fig)
        st.plotly_chart(fig, width="stretch")

    st.divider()

    st.subheader("🏭 Sector Heatmap")
    st.caption(
        "**Avg Expected Return (%)** is the average of every company's predicted return within that "
        "sector, today -- Pharma showing a higher number than Hospital simply means the model currently "
        "expects Pharma stocks, on average, to move up more than Hospital stocks. It recalculates every "
        "run and isn't fixed."
    )
    if not heat_df.empty:
        sector_agg = heat_df.groupby("Sector").agg(
            **{"Avg Expected Return (%)": ("Expected Return (%)", "mean"),
               "Avg AI Score": ("AI Opportunity Score", "mean"),
               "Companies": ("Company", "count")}
        ).reset_index().round(2)
        fig2 = go.Figure(go.Bar(
            x=sector_agg["Avg Expected Return (%)"], y=sector_agg["Sector"], orientation="h",
            marker_color=[GREEN if v >= 0 else RED for v in sector_agg["Avg Expected Return (%)"]],
            text=sector_agg["Avg Expected Return (%)"].astype(str) + "%", textposition="outside",
            textfont=dict(size=CHART_AXIS_PX + 2),
        ))
        style_fig(fig2)
        fig2.update_layout(xaxis_title="Avg Expected Return (%)")
        st.plotly_chart(fig2, width="stretch")
        st.dataframe(sector_agg, width="stretch", hide_index=True)

    st.divider()

    st.subheader("🟢 Buy Signals")
    buys = latest[latest["Recommendation"].isin(["BUY", "STRONG BUY"])].sort_values(
        "Expected Return (%)", ascending=False)
    if buys.empty:
        st.caption("No Buy-rated stocks right now.")
    else:
        st.dataframe(buys[["Company", "Price", "Expected Return (%)", "Prediction Confidence (%)", "Recommendation"]],
                     width="stretch", hide_index=True)

    st.divider()

    st.subheader("🔴 Sell Signals")
    sells = latest[latest["Recommendation"].isin(["SELL", "STRONG SELL"])].sort_values(
        "Expected Return (%)")
    if sells.empty:
        st.caption("No Sell-rated stocks right now.")
    else:
        st.dataframe(sells[["Company", "Price", "Expected Return (%)", "Prediction Confidence (%)", "Recommendation"]],
                     width="stretch", hide_index=True)


# =========================
# PAGE: PREDICTIONS & RECOMMENDATIONS
# =========================

elif page == "📊 Predictions & Recommendations":
    st.header("📊 Predictions + Recommendation")

    c1, c2, c3 = st.columns(3)
    sectors = ["All"] + sorted(latest["Sector"].dropna().unique().tolist())
    sector_filter = c1.selectbox("Sector", sectors)
    recs = ["All"] + sorted(latest["Recommendation"].dropna().unique().tolist())
    rec_filter = c2.selectbox("Recommendation", recs)
    agreements = ["All"] + sorted(latest["Signal Agreement"].dropna().unique().tolist()) \
        if "Signal Agreement" in latest.columns else ["All"]
    agreement_filter = c3.selectbox("Signal Agreement", agreements)

    view = latest.copy()
    if sector_filter != "All":
        view = view[view["Sector"] == sector_filter]
    if rec_filter != "All":
        view = view[view["Recommendation"] == rec_filter]
    if agreement_filter != "All" and "Signal Agreement" in view.columns:
        view = view[view["Signal Agreement"] == agreement_filter]

    st.caption(
        "**Ensemble** is the headline predicted price -- a weighted average of 5 models, weighted by "
        "which ones have actually been more accurate recently. **Confidence** reflects model agreement "
        "and a real prediction interval -- higher is more trustworthy, not a guarantee."
    )
    st.caption(
        "**Executive Signal** is a separate rating built from a composite AI Opportunity Score (blends "
        "confidence, technical indicators, news/fundamentals -- not just price). **Signal Agreement** "
        "compares that against the simpler price-only **Recommendation**: **Agree** = both point the same "
        "way, **Mild Disagreement** = one step apart (e.g. Buy vs Hold), **Disagreement** = they point in "
        "different directions and are worth a manual look before acting."
    )

    display_cols = [c for c in [
        "AI Rank", "Company", "Sector", "Price",
        "Ensemble Next Day", "Ensemble Next Week", "Ensemble Next Month", "Ensemble Next 3 Months",
        "Prediction Confidence (%)", "Recommendation", "Executive Signal", "Signal Agreement", "Risk Level",
    ] if c in view.columns]
    st.dataframe(view[display_cols].sort_values("AI Rank") if "AI Rank" in view.columns else view[display_cols],
                 width="stretch", hide_index=True)

    st.subheader("Company Deep-Dive")
    company_choice = st.selectbox("Pick a company", sorted(view["Company"].unique()) if not view.empty else [])

    if company_choice:
        row = latest[latest["Company"] == company_choice].iloc[0]

        g1, g2, g3 = st.columns(3)
        with g1:
            ret = row.get("Expected Return (%)", 0) or 0
            fig = go.Figure(go.Indicator(
                mode="gauge+number", value=ret, title={"text": "Prediction Gauge (Expected Return %)"},
                number={"font": {"size": CHART_TITLE_PX + 20}},
                gauge={"axis": {"range": [-15, 15]},
                       "bar": {"color": GREEN if ret >= 0 else RED},
                       "steps": [{"range": [-15, -5], "color": "#3A1414"}, {"range": [-5, 5], "color": "#2A2F3B"},
                                 {"range": [5, 15], "color": "#132318"}]}))
            style_fig(fig, height=GAUGE_H)
            st.plotly_chart(fig, width="stretch")
        with g2:
            conf = row.get("Prediction Confidence (%)", 0) or 0
            fig = go.Figure(go.Indicator(
                mode="gauge+number", value=conf, title={"text": "Confidence Meter"},
                number={"font": {"size": CHART_TITLE_PX + 20}},
                gauge={"axis": {"range": [0, 100]}, "bar": {"color": AMBER},
                       "steps": [{"range": [0, 60], "color": "#3A1414"}, {"range": [60, 85], "color": "#2A2013"},
                                 {"range": [85, 100], "color": "#132318"}]}))
            style_fig(fig, height=GAUGE_H)
            st.plotly_chart(fig, width="stretch")
        with g3:
            risk_map = {"Low": 20, "Medium": 55, "High": 90}
            risk_val = risk_map.get(row.get("Risk Level"), 50)
            fig = go.Figure(go.Indicator(
                mode="gauge+number", value=risk_val, title={"text": f"Risk Meter ({row.get('Risk Level', 'N/A')})"},
                number={"suffix": "", "valueformat": "", "font": {"size": CHART_TITLE_PX + 20}},
                gauge={"axis": {"range": [0, 100], "tickvals": [20, 55, 90], "ticktext": ["Low", "Med", "High"]},
                       "bar": {"color": {"Low": GREEN, "Medium": AMBER, "High": RED}.get(row.get("Risk Level"), GREY)}}))
            style_fig(fig, height=GAUGE_H)
            st.plotly_chart(fig, width="stretch")

        st.markdown(f"**🤖 AI Explanation:** {explain.explain_row(row)}")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Current Price", f"₹{row.get('Price', 'N/A')}")
        m2.metric("Next Day", f"₹{row.get('Ensemble Next Day', 'N/A')}")
        m3.metric("Next Week", f"₹{row.get('Ensemble Next Week', 'N/A')}")
        m4.metric("Next Month", f"₹{row.get('Ensemble Next Month', 'N/A')}")

        with st.expander("All 5 models, all horizons"):
            model_rows = []
            for horizon in ["Next Day", "Next Week", "Next Month", "Next 3 Months"]:
                model_rows.append({
                    "Horizon": horizon, "Ensemble": row.get(f"Ensemble {horizon}"),
                    "LR": row.get(f"LR {horizon}"), "RF": row.get(f"RF {horizon}"),
                    "XGB": row.get(f"XGB {horizon}"), "LGBM": row.get(f"LGBM {horizon}"),
                    "CAT": row.get(f"CAT {horizon}"), "Confidence Interval": row.get(f"Confidence Interval {horizon}"),
                })
            st.dataframe(pd.DataFrame(model_rows), width="stretch", hide_index=True)

        hist = data["history"]
        if not hist.empty and "Company" in hist.columns:
            comp_hist = hist[hist["Company"] == company_choice].sort_values("Prediction Date")
            if len(comp_hist) > 1:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=comp_hist["Prediction Date"], y=comp_hist["Price"],
                                          name="Actual Price", mode="lines+markers",
                                          line=dict(color=AMBER, width=3), marker=dict(size=9)))
                if "Ensemble Next Day" in comp_hist.columns:
                    fig.add_trace(go.Scatter(x=comp_hist["Prediction Date"], y=comp_hist["Ensemble Next Day"],
                                              name="Predicted (Next Day)", mode="lines+markers",
                                              line=dict(color=GREEN, width=3), marker=dict(size=9)))
                fig.update_layout(title=f"{company_choice}: price vs. next-day prediction over time")
                style_fig(fig)
                st.plotly_chart(fig, width="stretch")

        st.subheader("📈 Prediction Timeline (all horizons)")
        timeline_df = data["timeline"]
        if not timeline_df.empty and "Company" in timeline_df.columns:
            comp_timeline = timeline_df[timeline_df["Company"] == company_choice].copy()
            horizon_order = {"Next Day": 1, "Next Week": 2, "Next Month": 3, "Next 3 Months": 4}
            if not comp_timeline.empty and "Horizon" in comp_timeline.columns:
                comp_timeline["_order"] = comp_timeline["Horizon"].map(horizon_order).fillna(99)
                comp_timeline = comp_timeline.sort_values("_order")
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=comp_timeline["Horizon"], y=comp_timeline["Predicted Price"],
                    mode="lines+markers", name="Predicted Price",
                    line=dict(color=BLUE, width=3), marker=dict(size=10),
                ))
                fig.update_layout(title=f"{company_choice}: predicted price path across horizons")
                style_fig(fig, height=CHART_H - 60)
                st.plotly_chart(fig, width="stretch")
                with st.expander("Confidence & recommendation per horizon"):
                    detail_cols = [c for c in ["Horizon", "Predicted Price", "Confidence Interval",
                                                "Prediction Confidence (%)", "Recommendation"]
                                    if c in comp_timeline.columns]
                    st.dataframe(comp_timeline[detail_cols], width="stretch", hide_index=True)
            else:
                st.caption("No timeline data for this company yet.")
        else:
            st.caption("Prediction timeline table is empty -- run main.py to populate it.")

        st.subheader("📰 News Timeline")
        news_df = data["news"]
        if not news_df.empty:
            comp_news = news_df[news_df["Company"] == company_choice].sort_values("Date Archived", ascending=False)
            if comp_news.empty:
                st.caption("No news archived for this company yet.")
            else:
                for _, n in comp_news.iterrows():
                    st.markdown(f"**{n.get('Date Archived')}** · {n.get('Sentiment')} · {n.get('Strategy')}  \n{n.get('News')}")


# =========================
# PAGE: BACKTEST & ACCURACY
# =========================

elif page == "🧪 Backtest & Accuracy":
    st.header("🧪 Backtest Results")
    backtest_path = config.BACKTEST_REPORT
    if os.path.exists(backtest_path):
        st.dataframe(pd.read_csv(backtest_path), width="stretch", hide_index=True)
    else:
        st.info("No backtest report yet. Run `backtest.py` (see README.md) to generate one.")

    st.subheader("Live Accuracy (real predictions vs. actual)")
    summary = data["accuracy_summary"]
    if summary.empty:
        st.info("Run `python track_accuracy.py` after a few days of daily runs to see this.")
    else:
        st.dataframe(summary, width="stretch", hide_index=True)


# =========================
# PAGE: PORTFOLIO (PAPER TRADING)
# =========================

elif page == "💼 Portfolio (Paper Trading)":
    st.header("💼 Portfolio (Paper Trading)")
    st.caption("Simulated only. No live orders are ever placed by this dashboard or the pipeline.")
    trades = data["paper_trades"]
    if trades.empty:
        st.info("No paper trades logged yet.")
    else:
        open_trades = trades[trades["Status"] == "OPEN"]
        closed_trades = trades[trades["Status"] == "CLOSED"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Open Positions", len(open_trades))
        c2.metric("Closed Trades", len(closed_trades))
        if len(closed_trades):
            win_rate = (closed_trades["Realized PnL"] > 0).mean() * 100
            c3.metric("Win Rate / Realized P&L", f"{win_rate:.1f}%", f"₹{closed_trades['Realized PnL'].sum():,.0f}")
        st.markdown("**Open Positions**")
        st.dataframe(open_trades, width="stretch", hide_index=True)
        st.markdown("**Closed Positions**")
        st.dataframe(closed_trades, width="stretch", hide_index=True)


# =========================
# PAGE: INSTITUTION ACTIVITY
# =========================

elif page == "🏦 Institution Activity":
    st.header("🏦 Institution Activity")
    st.info("Coming soon -- needs a new data source (FII/DII flows, bulk/block deals). "
            "Not built yet; ask if you want this added next.")


st.divider()
st.caption(
    f"Data source: {db.DB_PATH} (a file on this computer). Read-only -- no trades are placed here. "
    f"Predictions are model outputs, not financial advice."
)
