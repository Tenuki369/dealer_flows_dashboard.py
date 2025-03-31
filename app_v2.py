import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide", page_title="Options Dealer Flow Dashboard")

st.title("🔍 Dealer Gamma & Delta Exposure Dashboard")

uploaded_file = st.file_uploader("Upload parsed_opsdash.xlsx", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    df = df.dropna(subset=["Strike", "Gamma Exposure", "Delta Exposure", "Expiry"])
    df["Strike"] = pd.to_numeric(df["Strike"], errors="coerce")
    df["Expiry"] = pd.to_datetime(df["Expiry"])
    df = df.sort_values("Strike")

    symbol = df["Symbol"].dropna().unique()[0] if "Symbol" in df.columns else "N/A"
    st.markdown(f"**Asset:** `{symbol}`")

    # Expiry filter
    unique_expiries = df["Expiry"].dropna().sort_values().dt.strftime("%Y-%m-%d").unique()
    expiry_choice = st.selectbox("Filter by Expiry", options=["All"] + list(unique_expiries))

    if expiry_choice != "All":
        expiry_dt = pd.to_datetime(expiry_choice)
        df = df[df["Expiry"] == expiry_dt]

    grouped = df.groupby("Strike")[["Gamma Exposure", "Delta Exposure"]].sum().reset_index()
    grouped["Gamma Sign"] = grouped["Gamma Exposure"].apply(lambda x: "Positive" if x >= 0 else "Negative")

    # Gamma flip zone
    flip_row = grouped[grouped["Gamma Sign"] != grouped["Gamma Sign"].shift(1)]
    gamma_flip = flip_row["Strike"].iloc[0] if not flip_row.empty else "N/A"

    # Gamma Exposure Chart
    st.subheader("Gamma Exposure by Strike")
    fig1 = px.bar(grouped, x="Strike", y="Gamma Exposure", color="Gamma Sign", title="Gamma Exposure")
    st.plotly_chart(fig1, use_container_width=True)

    # Delta Exposure Chart
    st.subheader("Delta Exposure by Strike")
    fig2 = px.area(grouped, x="Strike", y="Delta Exposure", title="Delta Exposure")
    st.plotly_chart(fig2, use_container_width=True)

    # Flow Commentary
    st.subheader("🧠 Flow Commentary")
    spot_price = st.number_input("Enter Spot Price", value=float(grouped["Strike"].median()))

    if gamma_flip != "N/A":
        if spot_price > gamma_flip:
            st.info(f"Price is above the gamma flip zone ({gamma_flip}). Dealers may be **short gamma** — watch for volatility.")
        elif spot_price < gamma_flip:
            st.info(f"Price is below the gamma flip zone ({gamma_flip}). Dealers likely **long gamma** — moves may be absorbed.")
        else:
            st.info(f"Price is near the gamma flip zone ({gamma_flip}). Stay alert for pivots or pinning.")
    else:
        st.warning("No gamma flip zone detected in this range.")

    # Optional: full table view
    with st.expander("📋 View Raw Options Table"):
        st.dataframe(df)

else:
    st.info("Please upload your latest `parsed_opsdash.xlsx` file to begin.")
