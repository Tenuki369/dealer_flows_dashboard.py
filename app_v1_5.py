import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from io import StringIO
from datetime import datetime
import os

st.set_page_config(layout="wide", page_title="Options Dashboard v1.5")
st.title("🧠 Options Dealer Flow Dashboard")

# ------------------------------------------------------------------
# 1) OneDrive links for your data files
#    Replace these placeholders with your actual direct download URLs
# ------------------------------------------------------------------
PARSED_XLSX_URL = "https://1drv.ms/x/c/7c01f62799376338/ESqn9Byg1zxBsPPAe2uGZAoB1hZSfLPVEiKJIYkgUY4kpA?e=DNTlNp"
GAMMA_CSV_URL   = "https://1drv.ms/x/c/7c01f62799376338/Efu7qf21l8dMvomNtN0zN6gBDleVxQQdvHLXo-MWDUdb7g?e=nqNhBm"

# ------------------------------------------------------------------
# Attempt to fetch parsed_opsdash.xlsx from OneDrive
# If that fails, fallback to a manual uploader
# ------------------------------------------------------------------
try:
    st.info("Fetching parsed_opsdash.xlsx from OneDrive...")
    parsed_response = requests.get(PARSED_XLSX_URL)
    parsed_response.raise_for_status()  # raise error if link is invalid

    # Save the downloaded file to a temporary local file
    with open("temp_parsed.xlsx", "wb") as f:
        f.write(parsed_response.content)

    # Load the file into a DataFrame
    df = pd.read_excel("temp_parsed.xlsx")
    st.success("Successfully loaded parsed_opsdash.xlsx from OneDrive!")
except Exception as e:
    st.warning("Could not fetch parsed_opsdash.xlsx from OneDrive. Please upload manually.")
    uploaded_file = st.file_uploader("Upload parsed_opsdash.xlsx", type=["xlsx"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.success("Successfully loaded parsed_opsdash.xlsx from manual upload!")
    else:
        st.error(f"Error loading data from OneDrive: {e}")
        st.stop()

# ------------------------------------------------------------------
# Now we have a DataFrame `df` with the parsed options data
# ------------------------------------------------------------------
df = df.dropna(subset=["Strike", "Gamma Exposure", "Delta Exposure", "Expiry", "Type"])
df["Strike"] = pd.to_numeric(df["Strike"], errors="coerce")
df["Expiry"] = pd.to_datetime(df["Expiry"])
df = df.sort_values("Strike")

symbol = df["Symbol"].dropna().unique()[0] if "Symbol" in df.columns else "Unknown"
st.markdown(f"### Underlying Asset: `{symbol}`")

# Expiry filter
expiries = df["Expiry"].dt.strftime("%Y-%m-%d").unique()
expiry_choice = st.selectbox("Select Expiry", ["All"] + list(expiries))
if expiry_choice != "All":
    expiry_dt = pd.to_datetime(expiry_choice)
    df = df[df["Expiry"] == expiry_dt]

# Compute grouped exposures and Gamma Flip Zone
grouped = df.groupby("Strike")[["Gamma Exposure", "Delta Exposure"]].sum().reset_index()
grouped["Gamma Sign"] = grouped["Gamma Exposure"].apply(lambda x: "Positive" if x >= 0 else "Negative")
flip_row = grouped[grouped["Gamma Sign"] != grouped["Gamma Sign"].shift(1)]
flip_zone = flip_row["Strike"].iloc[0] if not flip_row.empty else "N/A"

# Create tab layout
tab1, tab2, tab3, tab4 = st.tabs(["Gamma Heatmap", "Breakdown", "Charm View", "Gamma Terrain 3D"])

# ------------------------------------------------------------------
# Tab 1: Gamma Exposure Contour
# ------------------------------------------------------------------
with tab1:
    st.markdown("#### Gamma Exposure Contour")
    fig1 = px.density_contour(df, x="Strike", y="Gamma Exposure", color="Type")
    fig1.update_traces(contours_coloring="fill", line_width=0)
    st.plotly_chart(fig1, use_container_width=True)

# ------------------------------------------------------------------
# Tab 2: Breakdown by Strike (Calls vs Puts)
# ------------------------------------------------------------------
with tab2:
    st.markdown("#### Breakdown by Strike")
    call_data = df[df["Type"] == "Call"].groupby("Strike")["OI"].sum()
    put_data = df[df["Type"] == "Put"].groupby("Strike")["OI"].sum()
    strikes = sorted(set(call_data.index).union(set(put_data.index)))

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=call_data.loc[strikes], y=strikes, name="Calls", orientation='h', marker_color='green'))
    fig2.add_trace(go.Bar(x=-put_data.loc[strikes], y=strikes, name="Puts", orientation='h', marker_color='red'))
    fig2.update_layout(
        barmode='relative', height=600, title="Net OI by Strike",
        xaxis_title="Contracts (Calls positive, Puts negative)", yaxis_title="Strike"
    )
    st.plotly_chart(fig2, use_container_width=True)

# ------------------------------------------------------------------
# Tab 3: Charm View (Experimental)
# ------------------------------------------------------------------
with tab3:
    st.markdown("#### Charm View")
    df["Charm"] = df["Delta Exposure"] / df["Strike"]
    fig3 = px.density_heatmap(df, x="Strike", y="Charm", color_continuous_scale="RdBu", title="Charm Intensity")
    st.plotly_chart(fig3, use_container_width=True)

# ------------------------------------------------------------------
# Tab 4: Gamma Terrain (3D) from gamma_history.csv in OneDrive
# ------------------------------------------------------------------
with tab4:
    st.markdown("#### Gamma Terrain (3D)")
    try:
        st.info("Fetching gamma_history.csv from OneDrive...")
        response = requests.get(GAMMA_CSV_URL)
        response.raise_for_status()

        # Use a very flexible parser to handle any stray quotes or delimiters
        df_hist = pd.read_csv(
            StringIO(response.text),
            engine="python",
            sep=None,
            quotechar=None,
            on_bad_lines="skip",
            encoding_errors="ignore"
        )
        df_hist["Timestamp"] = pd.to_datetime(df_hist["Timestamp"])

        # Pivot to form a matrix: row=Timestamp, col=Strike, val=Gamma Exposure
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
        st.success("Gamma Terrain data loaded successfully!")
        st.plotly_chart(fig4, use_container_width=True)
    except Exception as e:
        st.error("Gamma terrain data not available or malformed.")
        st.code(str(e))

# ------------------------------------------------------------------
# Flow Commentary
# ------------------------------------------------------------------
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
