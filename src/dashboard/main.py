"""
AutoTrader Pro - Enhanced Dashboard with Broker Selection
"""

import os
import sys

# Add the src directory to Python path to ensure proper imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)


def get_api_base_url():
    """Get API base URL from environment or default"""
    return os.getenv("AUTOTRADER_API_BASE_URL", "http://localhost:8080")


def fetch_broker_status(api_base_url):
    """Fetch broker status from API"""
    try:
        import requests

        response = requests.get(f"{api_base_url}/api/brokers/status", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        return {"error": str(e)}


def connect_to_broker(api_base_url, broker_name):
    """Connect to a specific broker"""
    try:
        import requests

        response = requests.post(f"{api_base_url}/api/brokers/connect/{broker_name}", timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            return {"success": False, "message": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def fetch_account_info(api_base_url):
    """Fetch account information from active broker"""
    try:
        import requests

        response = requests.get(f"{api_base_url}/api/trading/account", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        return {"error": str(e)}


def fetch_positions(api_base_url):
    """Fetch positions from active broker"""
    try:
        import requests

        response = requests.get(f"{api_base_url}/api/trading/positions", timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        return []


def main() -> None:
    """Main dashboard function"""
    try:
        import streamlit as st

        st.set_page_config(page_title="AutoTrader Pro Dashboard", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

        # API Base URL
        API_BASE_URL = get_api_base_url()

        st.title("🚀 AutoTrader Pro Dashboard")

        # Sidebar for broker selection
        st.sidebar.header("🔧 Broker Management")

        # Fetch broker status
        broker_status = fetch_broker_status(API_BASE_URL)

        if broker_status and "error" not in broker_status:
            available_brokers = broker_status.get("available_brokers", [])
            connected_brokers = broker_status.get("connected_brokers", [])

            # Current active broker
            if connected_brokers:
                current_broker = connected_brokers[0]
            else:
                current_broker = None

            # 1. Select broker dropdown (on top)
            broker_names = [broker["name"] for broker in available_brokers]
            broker_display_names = [f"{broker['display_name']} ({'📄' if broker['paper_trading'] else '💰'})" for broker in available_brokers]

            if broker_names:
                # Get current selection index
                current_index = 0
                if current_broker and current_broker in broker_names:
                    current_index = broker_names.index(current_broker)

                selected_display = st.sidebar.selectbox("Select Broker:", broker_display_names, index=current_index, key="broker_selector")

                # Get the actual broker name from selection
                selected_index = broker_display_names.index(selected_display)
                selected_broker = broker_names[selected_index]

                # 2. Connect button
                if st.sidebar.button("🔌 Connect to Broker", type="primary"):
                    if selected_broker != current_broker:
                        with st.spinner(f"Connecting to {selected_broker}..."):
                            connection_result = connect_to_broker(API_BASE_URL, selected_broker)

                            if connection_result.get("success", False):
                                st.sidebar.success(f"✅ Connected to {selected_broker}")
                                st.rerun()
                            else:
                                st.sidebar.error(f"❌ Failed to connect: {connection_result.get('message', 'Unknown error')}")
                    else:
                        st.sidebar.info("Already connected to this broker")

                # 3. Status and Clear buttons
                col1, col2 = st.sidebar.columns(2)
                with col1:
                    if st.button("📊 Refresh", key="status_refresh", use_container_width=True):
                        st.rerun()

                with col2:
                    if st.button("🔄 Clear State", key="clear_state", use_container_width=True, help="Clear cached state"):
                        st.success("State cleared!")
                        st.rerun()

                # 4. Broker info box
                if current_broker:
                    # Find the current broker info
                    current_broker_info = next((broker for broker in available_brokers if broker["name"] == current_broker), None)
                    if current_broker_info:
                        st.sidebar.subheader("📋 Active Broker Info")
                        with st.sidebar.container():
                            st.write(f"**Broker:** {current_broker_info['display_name']}")
                            st.write("**Status:** 🟢 Connected")
                            st.write(f"**Mode:** {'📄 Paper Trading' if current_broker_info['paper_trading'] else '� Live Trading'}")
                else:
                    st.sidebar.subheader("� Broker Info")
                    with st.sidebar.container():
                        st.write("**Status:** 🔴 No broker connected")
                        st.write("Please select and connect to a broker above")
            else:
                st.sidebar.warning("No brokers available")
        else:
            st.sidebar.error("❌ Failed to fetch broker status")
            if broker_status and "error" in broker_status:
                st.sidebar.error(f"Error: {broker_status['error']}")

        # Main content area
        col1, col2 = st.columns([2, 1])

        with col1:
            st.header("📊 System Status")

            # API Connection test
            try:
                import requests

                response = requests.get(f"{API_BASE_URL}/health", timeout=5)

                if response.status_code == 200:
                    st.success("🟢 API Connection: Healthy")
                else:
                    st.error(f"🔴 API Connection: Error {response.status_code}")
            except Exception as e:
                st.error(f"🔴 API Connection: Failed - {e}")
                st.info("Make sure the API server is running on http://localhost:8080")

        with col2:
            st.header("🔗 Quick Links")
            st.markdown(f"""
            - [API Docs]({API_BASE_URL}/docs)
            - [System Health]({API_BASE_URL}/health)
            """)

        # Account Information Section
        if broker_status and broker_status.get("connected_brokers"):
            st.header("� Account Information")

            account_info = fetch_account_info(API_BASE_URL)
            if account_info and "error" not in account_info:
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Portfolio Value", f"${account_info.get('portfolio_value', 0):,.2f}")
                with col2:
                    st.metric("Cash Available", f"${account_info.get('cash', 0):,.2f}")
                with col3:
                    st.metric("Buying Power", f"${account_info.get('buying_power', 0):,.2f}")
                with col4:
                    account_status = account_info.get("account_status", "Unknown")
                    st.metric("Account Status", account_status)

                # Additional account details
                with st.expander("📋 Account Details"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Account ID:** {account_info.get('account_id', 'N/A')}")
                        st.write(f"**Currency:** {account_info.get('currency', 'USD')}")
                    with col2:
                        st.write(f"**Day Trade Count:** {account_info.get('day_trade_count', 0)}")
                        pdt_status = "Yes" if account_info.get("pattern_day_trader", False) else "No"
                        st.write(f"**Pattern Day Trader:** {pdt_status}")
            else:
                st.warning("⚠️ Unable to fetch account information")

            # Positions Section
            st.header("📈 Current Positions")

            positions = fetch_positions(API_BASE_URL)
            if positions:
                import pandas as pd

                # Convert to DataFrame for better display
                df = pd.DataFrame(positions)

                # Format numeric columns
                numeric_columns = ["quantity", "market_value", "cost_basis", "average_entry_price", "unrealized_pl", "unrealized_plpc", "current_price"]

                for col in numeric_columns:
                    if col in df.columns:
                        if col in ["market_value", "cost_basis", "average_entry_price", "unrealized_pl", "current_price"]:
                            df[col] = df[col].apply(lambda x: f"${x:,.2f}")
                        elif col == "unrealized_plpc":
                            df[col] = df[col].apply(lambda x: f"{x:.2f}%")
                        elif col == "quantity":
                            df[col] = df[col].apply(lambda x: f"{x:.0f}")

                st.dataframe(df, use_container_width=True)
            else:
                st.info("📭 No positions found")
        else:
            st.info("🔌 Please connect to a broker to view account information and positions")

    except ImportError:
        st.error("❌ Streamlit not available")
        sys.exit(1)
    except Exception as e:
        st.error(f"❌ Dashboard Error: {e}")
        import traceback

        st.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
