"""
AutoTrader Pro - Advanced Streamlit Dashboard
Real-time monitoring and control interface for automated trading system
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import time
from typing import Dict, List, Any

# Configure Streamlit page
st.set_page_config(
    page_title="AutoTrader Pro Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .status-running { color: #28a745; }
    .status-stopped { color: #dc3545; }
    .status-warning { color: #ffc107; }
    .control-button {
        margin: 0.25rem;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        border: none;
        cursor: pointer;
        font-weight: bold;
    }
    .emergency-stop {
        background-color: #dc3545;
        color: white;
    }
    .action-button {
        background-color: #007bff;
        color: white;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Configuration
API_BASE_URL = "http://localhost:8000"
REFRESH_INTERVAL = 5  # seconds


class DashboardAPI:
    """API client for communicating with AutoTrader Pro backend"""

    def __init__(self, base_url: str):
        self.base_url = base_url

    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=5)
            return response.json()
        except Exception as e:
            return {"error": str(e), "system_running": False}

    def get_tracked_symbols(self) -> List[Dict[str, Any]]:
        """Get currently tracked symbols"""
        try:
            response = requests.get(f"{self.base_url}/api/tracked-symbols", timeout=5)
            return response.json()
        except Exception:
            return []

    def get_strategy_results(self) -> List[Dict[str, Any]]:
        """Get recent strategy results"""
        try:
            response = requests.get(f"{self.base_url}/api/strategy-results", timeout=5)
            return response.json()
        except Exception:
            return []

    def get_signals(self) -> List[Dict[str, Any]]:
        """Get recent trading signals"""
        try:
            response = requests.get(f"{self.base_url}/api/signals", timeout=5)
            return response.json()
        except Exception:
            return []

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        try:
            response = requests.get(f"{self.base_url}/api/positions", timeout=5)
            return response.json()
        except Exception:
            return []

    def get_orders(self) -> List[Dict[str, Any]]:
        """Get recent orders"""
        try:
            response = requests.get(f"{self.base_url}/api/orders", timeout=5)
            return response.json()
        except Exception:
            return []

    def get_portfolio_metrics(self) -> Dict[str, Any]:
        """Get portfolio performance metrics"""
        try:
            response = requests.get(f"{self.base_url}/api/portfolio", timeout=5)
            return response.json()
        except Exception:
            return {}

    def emergency_stop(self) -> bool:
        """Emergency stop all trading"""
        try:
            response = requests.post(
                f"{self.base_url}/api/controls/emergency-stop", timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False

    def close_position(self, symbol: str) -> bool:
        """Close a specific position"""
        try:
            response = requests.post(
                f"{self.base_url}/api/controls/close-position",
                json={"symbol": symbol},
                timeout=10,
            )
            return response.status_code == 200
        except Exception:
            return False

    def close_all_positions(self) -> bool:
        """Close all positions"""
        try:
            response = requests.post(
                f"{self.base_url}/api/controls/close-all-positions", timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False

    def toggle_strategy(self, strategy_name: str, enabled: bool) -> bool:
        """Enable/disable a specific strategy"""
        try:
            response = requests.post(
                f"{self.base_url}/api/controls/toggle-strategy",
                json={"strategy_name": strategy_name, "enabled": enabled},
                timeout=10,
            )
            return response.status_code == 200
        except Exception:
            return False


# Initialize API client
api = DashboardAPI(API_BASE_URL)


def render_header():
    """Render dashboard header"""
    st.markdown(
        '<h1 class="main-header">🚀 AutoTrader Pro Dashboard</h1>',
        unsafe_allow_html=True,
    )
    st.markdown("---")


def render_system_status():
    """Render system status section"""
    st.subheader("🔧 System Status")

    status = api.get_system_status()

    # Create metrics columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        status_text = (
            "🟢 Running" if status.get("system_running", False) else "🔴 Stopped"
        )
        st.metric("System Status", status_text)

    with col2:
        active_positions = status.get("active_positions", 0)
        max_positions = status.get("max_positions", 0)
        st.metric("Positions", f"{active_positions}/{max_positions}")

    with col3:
        portfolio_value = status.get("portfolio_value", 0)
        st.metric("Portfolio Value", f"${portfolio_value:,.2f}")

    with col4:
        pending_signals = status.get("pending_signals", 0)
        st.metric("Pending Signals", pending_signals)

    # Emergency Controls
    st.subheader("🚨 Emergency Controls")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🛑 EMERGENCY STOP", type="primary", use_container_width=True):
            if api.emergency_stop():
                st.success("✅ Emergency stop activated!")
            else:
                st.error("❌ Failed to activate emergency stop")

    with col2:
        if st.button("🔄 Close All Positions", use_container_width=True):
            if api.close_all_positions():
                st.success("✅ All positions closed!")
            else:
                st.error("❌ Failed to close positions")

    with col3:
        if st.button("♻️ Restart System", use_container_width=True):
            st.info("🔄 System restart functionality coming soon...")


def render_tracked_symbols():
    """Render tracked symbols section"""
    st.subheader("🎯 Tracked Symbols")

    symbols = api.get_tracked_symbols()

    if symbols:
        df = pd.DataFrame(symbols)

        # Format dataframe for display
        if not df.empty:
            df["added_at"] = pd.to_datetime(df["added_at"]).dt.strftime(
                "%Y-%m-%d %H:%M"
            )
            df["last_updated"] = pd.to_datetime(df["last_updated"]).dt.strftime(
                "%Y-%m-%d %H:%M"
            )

            # Add action buttons
            df["Actions"] = df["symbol"].apply(lambda x: "🗑️ Remove | 📊 Details")

            # Display table
            st.dataframe(
                df[["symbol", "added_at", "last_updated", "reason_added", "is_active"]],
                use_container_width=True,
            )
        else:
            st.info("No symbols currently being tracked")
    else:
        st.warning("⚠️ Unable to fetch tracked symbols")


def render_strategy_performance():
    """Render strategy performance section"""
    st.subheader("⚡ Strategy Performance")

    strategy_results = api.get_strategy_results()

    if strategy_results:
        df = pd.DataFrame(strategy_results)

        # Strategy performance summary
        if not df.empty:
            col1, col2 = st.columns(2)

            with col1:
                # Strategy win rates
                strategy_stats = (
                    df.groupby("strategy_name")
                    .agg(
                        {
                            "signal": lambda x: (x == "buy").sum(),
                            "strength": "mean",
                            "confidence": "mean",
                        }
                    )
                    .round(3)
                )
                strategy_stats.columns = [
                    "Buy Signals",
                    "Avg Strength",
                    "Avg Confidence",
                ]

                st.write("**Strategy Statistics**")
                st.dataframe(strategy_stats, use_container_width=True)

            with col2:
                # Strategy signal distribution
                signal_dist = df["strategy_name"].value_counts()
                fig = px.pie(
                    values=signal_dist.values,
                    names=signal_dist.index,
                    title="Strategy Signal Distribution",
                )
                st.plotly_chart(fig, use_container_width=True)

            # Strategy controls
            st.write("**Strategy Controls**")
            strategies = df["strategy_name"].unique()

            for strategy in strategies:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{strategy}**")
                with col2:
                    if st.button(f"Toggle {strategy}", key=f"toggle_{strategy}"):
                        # Toggle strategy (implement based on current state)
                        st.info(f"Toggling {strategy}...")
        else:
            st.info("No strategy results available")
    else:
        st.warning("⚠️ Unable to fetch strategy results")


def render_signals_pipeline():
    """Render trading signals pipeline"""
    st.subheader("📡 Trading Signals Pipeline")

    signals = api.get_signals()

    if signals:
        df = pd.DataFrame(signals)

        if not df.empty:
            # Format timestamps
            df["generated_at"] = pd.to_datetime(df["generated_at"]).dt.strftime(
                "%H:%M:%S"
            )

            # Add signal strength indicators
            df["Signal Strength"] = df["confidence_score"].apply(
                lambda x: "🔥"
                if x > 0.8
                else "⚡"
                if x > 0.6
                else "💡"
                if x > 0.4
                else "💭"
            )

            # Color code by direction
            def color_direction(val):
                if val == "buy":
                    return "background-color: #d4edda; color: #155724"
                elif val == "sell":
                    return "background-color: #f8d7da; color: #721c24"
                return ""

            # Display signals table
            styled_df = df[
                [
                    "symbol",
                    "direction",
                    "confidence_score",
                    "generated_at",
                    "Signal Strength",
                ]
            ].style.applymap(color_direction, subset=["direction"])

            st.dataframe(styled_df, use_container_width=True)

            # Signal statistics
            col1, col2, col3 = st.columns(3)

            with col1:
                buy_signals = len(df[df["direction"] == "buy"])
                st.metric("Buy Signals", buy_signals)

            with col2:
                sell_signals = len(df[df["direction"] == "sell"])
                st.metric("Sell Signals", sell_signals)

            with col3:
                avg_confidence = df["confidence_score"].mean()
                st.metric("Avg Confidence", f"{avg_confidence:.2f}")
        else:
            st.info("No recent signals generated")
    else:
        st.warning("⚠️ Unable to fetch trading signals")


def render_positions_monitor():
    """Render positions monitoring section"""
    st.subheader("💼 Position Monitor")

    positions = api.get_positions()

    if positions:
        df = pd.DataFrame(positions)

        if not df.empty:
            # Calculate P&L and format
            df["P&L $"] = df["unrealized_pnl"].round(2)
            df["P&L %"] = (
                (df["unrealized_pnl"] / (df["quantity"] * df["avg_entry_price"])) * 100
            ).round(2)

            # Add action buttons
            for idx, row in df.iterrows():
                col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 1, 1, 2])

                with col1:
                    st.write(f"**{row['symbol']}**")
                with col2:
                    st.write(f"{row['quantity']}")
                with col3:
                    st.write(f"${row['avg_entry_price']:.2f}")
                with col4:
                    pnl_color = "green" if row["P&L $"] >= 0 else "red"
                    st.markdown(
                        f"<span style='color: {pnl_color}'>${row['P&L $']:.2f}</span>",
                        unsafe_allow_html=True,
                    )
                with col5:
                    pnl_color = "green" if row["P&L %"] >= 0 else "red"
                    st.markdown(
                        f"<span style='color: {pnl_color}'>{row['P&L %']:.1f}%</span>",
                        unsafe_allow_html=True,
                    )
                with col6:
                    if st.button(
                        f"Close {row['symbol']}", key=f"close_{row['symbol']}"
                    ):
                        if api.close_position(row["symbol"]):
                            st.success(f"✅ Position {row['symbol']} closed!")
                        else:
                            st.error(f"❌ Failed to close {row['symbol']}")
        else:
            st.info("No open positions")
    else:
        st.warning("⚠️ Unable to fetch positions")


def render_portfolio_performance():
    """Render portfolio performance charts"""
    st.subheader("📈 Portfolio Performance")

    portfolio_metrics = api.get_portfolio_metrics()

    if portfolio_metrics:
        col1, col2 = st.columns(2)

        with col1:
            # Portfolio value over time (mock data for now)
            dates = pd.date_range(start="2024-01-01", end="2024-12-31", freq="D")
            values = [100000 + i * 50 + (i % 30) * 100 for i in range(len(dates))]

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=values,
                    mode="lines",
                    name="Portfolio Value",
                    line=dict(color="#1f77b4", width=2),
                )
            )

            fig.update_layout(
                title="Portfolio Value Over Time",
                xaxis_title="Date",
                yaxis_title="Value ($)",
                hovermode="x unified",
            )

            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Risk metrics
            risk_metrics = {
                "Portfolio Value": portfolio_metrics.get("total_equity", 0),
                "Available Cash": portfolio_metrics.get("available_cash", 0),
                "Daily P&L": portfolio_metrics.get("daily_pnl", 0),
                "Max Drawdown": portfolio_metrics.get("max_drawdown", 0),
            }

            for metric, value in risk_metrics.items():
                st.metric(metric, f"${value:,.2f}")
    else:
        st.warning("⚠️ Unable to fetch portfolio metrics")


def render_sidebar():
    """Render sidebar with controls and settings"""
    st.sidebar.title("⚙️ Controls")

    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("🔄 Auto Refresh", value=True)

    if auto_refresh:
        refresh_rate = st.sidebar.slider("Refresh Rate (seconds)", 5, 60, 10)
        st.sidebar.info(f"Dashboard updates every {refresh_rate} seconds")

    # Manual refresh button
    if st.sidebar.button("🔄 Refresh Now"):
        st.rerun()

    # Settings
    st.sidebar.subheader("📊 Display Settings")
    show_debug = st.sidebar.checkbox("Show Debug Info", value=False)

    if show_debug:
        st.sidebar.json(api.get_system_status())

    # Quick actions
    st.sidebar.subheader("⚡ Quick Actions")

    if st.sidebar.button("📊 Download Report"):
        st.sidebar.info("Report download coming soon...")

    if st.sidebar.button("🔧 System Logs"):
        st.sidebar.info("Log viewer coming soon...")


def main():
    """Main dashboard function"""
    render_header()
    render_sidebar()

    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["🏠 Overview", "📊 Strategies", "🎯 Signals", "💼 Positions", "📈 Performance"]
    )

    with tab1:
        render_system_status()
        render_tracked_symbols()

    with tab2:
        render_strategy_performance()

    with tab3:
        render_signals_pipeline()

    with tab4:
        render_positions_monitor()

    with tab5:
        render_portfolio_performance()

    # Auto-refresh functionality
    if st.sidebar.checkbox("🔄 Auto Refresh", value=True):
        time.sleep(10)  # Wait 10 seconds
        st.rerun()


if __name__ == "__main__":
    main()
