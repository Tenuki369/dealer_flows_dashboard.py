import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from io import StringIO
from datetime import datetime

st.set_page_config(layout="wide", page_title="Options Dashboard v1.5")
st.title("🧠 Options Dealer Flow Dashboard")

uploaded_file = st.file_uploader("Upload parsed_opsdash.xlsx", type=["xlsx"])

# ✅ Plug in your OneDrive direct CSV link here
GAMMA_CSV_URL = "https://1drv.ms/x/c/7c01f62799376338/Efu7qf21l8dMvomNtN0zN6gBDleVxQQdvHLXo-MWDUdb7g?e=mc2Po2"

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df = df.dropna(subset=["Strike", "Gamma Exposure", "Delta Exposure", "Expiry", "Type"])
    df["Strike"] = pd.to_numeric(df["Strike"], errors="coerce")
    df["Expiry"] = pd.to_datetime(df["Expiry"])
    df = df.sort_values("Strike")

    symbol = df["Symbol"].dropna().unique()[0] if "Symbol" in df.columns else "Unknown"
    st.markdown(f"### Underlying Asset: `{symbol}`")

    expiries = df["Expiry"].dt.strftime("%Y-%m-%d").unique()
    expiry_choice = st.selectbox("Select Expiry", ["All"] + list(expiries))

    if expiry_choice != "All":
        expiry_dt = pd.to_datetime(expiry_choice)
        df = df[df["Expiry"] == expiry_dt]

    grouped = df.groupby("Strike")[["Gamma Exposure", "Delta Exposure"]].sum().reset_index()
    grouped["Gamma Sign"] = grouped["Gamma Exposure"].apply(lambda x: "Positive" if x >= 0 else "Negative")
    flip_row = grouped[grouped["Gamma Sign"] != grouped["Gamma Sign"].shift(1)]
    flip_zone = flip_row["Strike"].iloc[0] if not flip_row.empty else "N/A"

    tab1, tab2, tab3, tab4 = st.tabs(["Gamma Heatmap", "Breakdown", "Charm View", "Gamma Terrain 3D"])

    with tab1:
        st.markdown("#### Gamma Exposure Contour")
        fig1 = px.density_contour(df, x="Strike", y="Gamma Exposure", color="Type")
        fig1.update_traces(contours_coloring="fill", line_width=0)
        st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        st.markdown("#### Breakdown by Strike")
        call_data = df[df["Type"] == "Call"].groupby("Strike")["OI"].sum()
        put_data = df[df["Type"] == "Put"].groupby("Strike")["OI"].sum()
        strikes = sorted(set(call_data.index).union(set(put_data.index)))

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=call_data.loc[strikes], y=strikes, name="Calls", orientation='h', marker_color='green'))
        fig2.add_trace(go.Bar(x=-put_data.loc[strikes], y=strikes, name="Puts", orientation='h', marker_color='red'))
        fig2.update_layout(barmode='relative', height=600, title="Net OI by Strike")
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.markdown("#### Charm View")
        df["Charm"] = df["Delta Exposure"] / df["Strike"]
        fig3 = px.density_heatmap(df, x="Strike", y="Charm", color_continuous_scale="RdBu", title="Charm Intensity")
        st.plotly_chart(fig3, use_container_width=True)

    with tab4:
        st.markdown("#### Gamma Terrain (3D)")
        try:
            response = requests.get(GAMMA_CSV_URL)
            response.raise_for_status()

            # 🔧 Fix: Use python engine for robust parsing
            df_hist = pd.read_csv(StringIO(response.text), engine="python")
            df_hist["Timestamp"] = pd.to_datetime(df_hist["Timestamp"])

            pivoted = df_hist.pivot(index="Timestamp", columns="Strike", values="Gamma Exposure")
            Z = pivoted.values
            X = pivoted.columns
            Y = pivoted.index.astype(str)

            fig4 = go.Figure(data=[go.Surface(z=Z, x=X, y=Y, colorscale="RdBu")])
            fig4.update_layout(
                title="Gamma Terrain Over Time",
                scene=dict(
                    xaxis_title="Strike",
                    yaxis_title="Time",
                    zaxis_title="Gamma Exposure"
                ),
                autosize=True,
                height=700
            )
            st.plotly_chart(fig4, use_container_width=True)
        except Exception as e:
            st.error("Gamma terrain data not available or malformed.")
            st.code(str(e))

    st.markdown("---")
    st.subheader("📌 Flow Commentary")
    spot_price = st.number_input("Enter Spot Price", value=float(df["Strike"].median()))

    if flip_zone != "N/A":
        if spot_price > flip_zone:
            st.success(f"Spot price `{spot_price}` is above Gamma Flip Zone `{flip_zone}` → Dealers may be short gamma.")
        elif spot_price < flip_zone:
            st.success(f"Spot price `{spot_price}` is below Gamma Flip Zone `{flip_zone}` → Dealers may be long gamma.")
        else:
            st.warning(f"Spot price is near the flip zone `{flip_zone}`.")
    else:
        st.info("No Gamma Flip Zone detected.")

    with st.expander("📋 View Full Options Data Table"):
        st.dataframe(df)

else:
    st.info("Upload the `parsed_opsdash.xlsx` file to begin.")
