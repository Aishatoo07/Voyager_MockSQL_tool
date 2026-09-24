import streamlit as st
import sqlite3
import pandas as pd
from db_setup import build_database

# ---------- BUILD DATABASE IF NOT PRESENT ----------
build_database()

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Voyager-Style Property Dashboard",
    page_icon="🏢",
    layout="wide"
)

# ---------- CUSTOM STYLING (Yardi-style blue & white) ----------
st.markdown("""
    <style>
        .main { background-color: #FFFFFF; }
        h1, h2, h3 { color: #0B3D91; }
        .stMetric { background-color: #F0F4FA; padding: 10px; border-radius: 8px; }
        div[data-testid="stMetricValue"] { color: #0B3D91; }
        .stTabs [data-baseweb="tab"] { color: #0B3D91; font-weight: 600; }
        .stTabs [aria-selected="true"] { background-color: #E3ECFA; border-radius: 6px; }
    </style>
""", unsafe_allow_html=True)

# ---------- DATABASE CONNECTION ----------
conn = sqlite3.connect("voyager_mock.db", check_same_thread=False)

# ---------- HEADER ----------
st.title("🏢 Property Management Dashboard")
st.caption("Modeled on core Voyager entities — Properties, Units, Leases, Tenants, GL Transactions")

# ---------- PROPERTY FILTER ----------
property_list = pd.read_sql("SELECT property_id, property_name FROM properties ORDER BY property_name", conn)
property_options = ["All Properties"] + property_list["property_name"].tolist()
selected_property = st.selectbox("Filter by Property", property_options)

st.divider()

# ---------- TABS ----------
tab1, tab2, tab3, tab4 = st.tabs(["📊 Occupancy", "📅 Lease Expirations", "💰 Rent Roll Variance", "📈 NOI Trend"])

# ================= TAB 1: OCCUPANCY =================
with tab1:
    st.subheader("Occupancy Rate by Property")

    query1 = """
    SELECT
        p.property_name,
        p.total_units,
        SUM(CASE WHEN u.status = 'Occupied' THEN 1 ELSE 0 END) AS occupied_units,
        ROUND(100.0 * SUM(CASE WHEN u.status = 'Occupied' THEN 1 ELSE 0 END) / p.total_units, 1) AS occupancy_pct
    FROM properties p
    JOIN units u ON p.property_id = u.property_id
    GROUP BY p.property_id
    ORDER BY occupancy_pct DESC;
    """
    df1 = pd.read_sql(query1, conn)

    if selected_property != "All Properties":
        df1 = df1[df1["property_name"] == selected_property]

    col1, col2, col3 = st.columns(3)
    col1.metric("Avg Occupancy", f"{df1['occupancy_pct'].mean():.1f}%")
    col2.metric("Total Units", int(df1['total_units'].sum()))
    col3.metric("Occupied Units", int(df1['occupied_units'].sum()))

    st.bar_chart(df1.set_index("property_name")["occupancy_pct"])
    st.dataframe(df1, use_container_width=True)

# ================= TAB 2: LEASE EXPIRATIONS =================
with tab2:
    st.subheader("Leases Expiring Soon (Next 90 Days)")

    query2 = """
    SELECT
        p.property_name,
        u.unit_number,
        t.first_name || ' ' || t.last_name AS tenant_name,
        l.lease_end,
        l.monthly_rent,
        CASE
            WHEN julianday(l.lease_end) - julianday('now') <= 30 THEN '0-30 days'
            WHEN julianday(l.lease_end) - julianday('now') <= 60 THEN '31-60 days'
            WHEN julianday(l.lease_end) - julianday('now') <= 90 THEN '61-90 days'
            ELSE '90+ days'
        END AS expiration_window
    FROM leases l
    JOIN units u ON l.unit_id = u.unit_id
    JOIN properties p ON u.property_id = p.property_id
    JOIN tenants t ON l.tenant_id = t.tenant_id
    WHERE l.lease_status = 'Active'
      AND julianday(l.lease_end) - julianday('now') BETWEEN 0 AND 90
    ORDER BY l.lease_end ASC;
    """
    df2 = pd.read_sql(query2, conn)

    if selected_property != "All Properties":
        df2 = df2[df2["property_name"] == selected_property]

    if df2.empty:
        st.info("No leases expiring in the next 90 days for this selection.")
    else:
        st.metric("Leases Expiring Soon", len(df2))
        st.dataframe(df2, use_container_width=True)

# ================= TAB 3: RENT ROLL VARIANCE =================
with tab3:
    st.subheader("Rent Roll Variance (Actual vs. Market Rent)")

    query3 = """
    SELECT
        p.property_name,
        u.unit_number,
        u.unit_type,
        u.market_rent,
        l.monthly_rent AS actual_rent,
        ROUND(l.monthly_rent - u.market_rent, 2) AS variance_dollars,
        ROUND(100.0 * (l.monthly_rent - u.market_rent) / u.market_rent, 1) AS variance_pct
    FROM leases l
    JOIN units u ON l.unit_id = u.unit_id
    JOIN properties p ON u.property_id = p.property_id
    WHERE l.lease_status = 'Active'
    ORDER BY variance_pct DESC;
    """
    df3 = pd.read_sql(query3, conn)

    if selected_property != "All Properties":
        df3 = df3[df3["property_name"] == selected_property]

    col1, col2 = st.columns(2)
    col1.metric("Avg Variance %", f"{df3['variance_pct'].mean():.1f}%")
    col2.metric("Units Above Market", int((df3['variance_dollars'] > 0).sum()))

    st.dataframe(df3, use_container_width=True)

# ================= TAB 4: NOI TREND =================
with tab4:
    st.subheader("Net Operating Income — Month over Month")

    if selected_property != "All Properties":
        pid = property_list[property_list["property_name"] == selected_property]["property_id"].values[0]
        query5 = f"""
        WITH monthly_totals AS (
            SELECT
                strftime('%Y-%m', transaction_date) AS month,
                SUM(CASE WHEN account_category = 'Income' THEN amount ELSE 0 END) AS total_income,
                SUM(CASE WHEN account_category = 'Expense' THEN amount ELSE 0 END) AS total_expense
            FROM gl_transactions
            WHERE property_id = {pid}
            GROUP BY strftime('%Y-%m', transaction_date)
        )
        SELECT
            month, total_income, total_expense,
            ROUND(total_income - total_expense, 2) AS noi,
            ROUND((total_income - total_expense) - LAG(total_income - total_expense) OVER (ORDER BY month), 2) AS noi_change_vs_prior_month
        FROM monthly_totals
        ORDER BY month;
        """
    else:
        query5 = """
        WITH monthly_totals AS (
            SELECT
                strftime('%Y-%m', transaction_date) AS month,
                SUM(CASE WHEN account_category = 'Income' THEN amount ELSE 0 END) AS total_income,
                SUM(CASE WHEN account_category = 'Expense' THEN amount ELSE 0 END) AS total_expense
            FROM gl_transactions
            GROUP BY strftime('%Y-%m', transaction_date)
        )
        SELECT
            month, total_income, total_expense,
            ROUND(total_income - total_expense, 2) AS noi,
            ROUND((total_income - total_expense) - LAG(total_income - total_expense) OVER (ORDER BY month), 2) AS noi_change_vs_prior_month
        FROM monthly_totals
        ORDER BY month;
        """

    df5 = pd.read_sql(query5, conn)
    st.line_chart(df5.set_index("month")["noi"])
    st.dataframe(df5, use_container_width=True)

st.divider()
st.caption("Built with SQLite + Python + Streamlit — modeled on Yardi Voyager's core property management entities.")
