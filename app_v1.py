import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide", page_title="Dealer Gamma/Delta Exposure")

st.title("📊 SPX Dealer Gamma & Delta Exposure Dashboard")

# Upload or read live-updated file
uploaded_file = st.file_uploader("Upload or drop parsed_opsdash.xlsx", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Filter and clean
    df = df.dropna(subset=["Strike", "Gamma Exposure", "Delta Exposure"])
    df["Strike"] = pd.to_numeric(df["Strike"], errors="coerce")
    df = df.sort_values("Strike")

    # Group exposures by strike
    exposure = df.groupby("Strike")[["Gamma Exposure", "Delta Exposure"]].sum().reset_index()

    # Detect gamma flip zone
    exposure["Gamma Sign"] = exposure["Gamma Exposure"].apply(lambda x: "Positive" if x >= 0 else "Negative")
    flip_rows = exposure[exposure["Gamma Sign"] != exposure["Gamma Sign"].shift(1)]
    gamma_flip_zone = flip_rows["Strike"].iloc[0] if not flip_rows.empty else "N/A"

    # Charts
    st.subheader("Gamma Exposure by Strike")
    fig1 = px.bar(exposure, x="Strike", y="Gamma Exposure", color="Gamma Sign", title="Gamma Exposure")
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("Dealer Delta Exposure by Strike")
    fig2 = px.area(exposure, x="Strike", y="Delta Exposure", title="Delta Exposure")
    st.plotly_chart(fig2, use_container_width=True)

    # Commentary section
    st.subheader("🧠 Flow Commentary")
    spot_price = st.number_input("Enter current SPX spot price", value=float(exposure["Strike"].median()))
    if gamma_flip_zone != "N/A":
        if spot_price > gamma_flip_zone:
            st.info(f"SPX is above the gamma flip zone ({gamma_flip_zone}) → Dealers may be short gamma. Volatility could increase.")
        elif spot_price < gamma_flip_zone:
            st.info(f"SPX is below the gamma flip zone ({gamma_flip_zone}) → Dealers may be long gamma. Moves may be dampened.")
        else:
            st.info(f"SPX is near the gamma flip zone ({gamma_flip_zone}) → Watch for pivots or reversals.")
    else:
        st.warning("Gamma flip zone not detected in current data.")
else:
    st.info("Please upload your parsed_opsdash.xlsx file to begin.")
