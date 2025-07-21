"""
AutoTrader Pro - Simple Dashboard
"""

import os
import sys

# Add the src directory to Python path to ensure proper imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)


def main() -> None:
    """Main dashboard function"""
    try:
        import streamlit as st

        st.set_page_config(
            page_title="AutoTrader Pro Dashboard",
            page_icon="🚀",
            layout="wide",
        )

        st.title("🚀 AutoTrader Pro Dashboard")
        st.success("Dashboard is working!")
        st.info("System is running with demo broker connected.")

        # Simple API test
        try:
            import os

            import requests

            API_BASE_URL = os.getenv("AUTOTRADER_API_BASE_URL", "http://localhost:8080")
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)

            if response.status_code == 200:
                st.success("[OK] API Connection Successful")
                st.json(response.json())
            else:
                st.error(f"[ERROR] API Connection Failed: {response.status_code}")

        except Exception as e:
            st.error(f"[ERROR] API Connection Error: {e}")
            st.info("Make sure the API server is running on http://localhost:8080")

        # Add some basic dashboard content
        st.header("📊 System Status")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Active Broker", "Demo Broker", "Connected")
        with col2:
            st.metric("Portfolio Value", "$100,000", "0%")
        with col3:
            st.metric("Positions", "0", "0")

        st.header("🔗 Quick Links")
        st.markdown("""
        - [API Documentation](http://localhost:8080/docs)
        - [System Status](http://localhost:8080/api/status)
        - [Portfolio](http://localhost:8080/api/portfolio)
        """)

    except ImportError:
        sys.exit(1)
    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
