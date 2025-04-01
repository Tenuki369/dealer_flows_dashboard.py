import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from datetime import datetime
import os

# === FILE LOCATIONS ===
base_path = r"C:\Users\GSB\OneDrive\OptionsData"
parsed_file = os.path.join(base_path, "parsed_opsdash.xlsx")
gamma_file = os.path.join(base_path, "gamma_history.csv")

# === PAGE CONFIG ===
st.set_page_config(layout="wide", page_title="Options Dashboard v1.5")
st.title("🧠 Options Dealer Flow Dashboard")

# === LOAD PARSED OPTIONS DATA ===
try:
    df = pd.read_excel(parsed_file)
    df = df.dropna(subset=["Strike", "Gamma_Exposure", "Delta_Exposure", "Expiry", "Type"])
    df["Strike"] = pd.to_numeric(df["Strike"], errors="coerce")
    df["Expiry"] = pd.to_datetime(df["Expiry"])
    df = df.sort_values("Strike")
    st.success("Parsed data loaded.")
except Exception as e:
    st.error("Failed to load parsed_opsdash.xlsx")
    st.code(str(e))
    st.stop()

# === Symbol Header ===
symbol = df["Symbol"].dropna().unique()[0] if "Symbol" in df.columns else "Unknown"
st.markdown(f"### Underlying Asset: `{symbol}`")

# === Expiry Selector ===
expiries = df["Expiry"].dt.strftime("%Y-%m-%d").unique()
expiry_choice = st.selectbox("Select Expiry", ["All"] + list(expiries))
if expiry_choice != "All":
    df = df[df["Expiry"].dt.strftime("%Y-%m-%d") == expiry_choice]

# === Compute Flip Zone ===
grouped = df.groupby("Strike")[["Gamma_Exposure", "Delta_Exposure"]].sum().reset_index()
grouped["Gamma_Sign"] = grouped["Gamma_Exposure"].apply(lambda x: "Positive" if x >= 0 else "Negative")
flip_row = grouped[grouped["Gamma_Sign"] != grouped["Gamma_Sign"].shift(1)]
flip_zone = flip_row["Strike"].iloc[0] if not flip_row.empty else "N/A"

# === Tabs ===
tab1, tab2, tab3, tab4 = st.tabs(["Gamma Heatmap", "Breakdown", "Charm View", "Gamma Terrain 3D"])

with tab1:
    st.markdown("#### Gamma Exposure Contour")
    fig1 = px.density_contour(df, x="Strike", y="Gamma_Exposure", color="Type")
    fig1.update_traces(contours_coloring="fill", line_width=0)
    st.plotly_chart(fig1, use_container_width=True)

with tab2:
    st.markdown("#### OI Breakdown by Strike")
    call_oi = df[df["Type"] == "Call"].groupby("Strike")["OI"].sum()
    put_oi = df[df["Type"] == "Put"].groupby("Strike")["OI"].sum()
    strikes = sorted(set(call_oi.index).union(put_oi.index))
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=call_oi.loc[strikes], y=strikes, name="Calls", orientation='h', marker_color='green'))
    fig2.add_trace(go.Bar(x=-put_oi.loc[strikes], y=strikes, name="Puts", orientation='h', marker_color='red'))
    fig2.update_layout(barmode='relative', height=600, title="Net OI by Strike",
                       xaxis_title="Contracts", yaxis_title="Strike")
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    st.markdown("#### Charm View (Experimental)")
    df["Charm"] = df["Delta_Exposure"] / df["Strike"]
    fig3 = px.density_heatmap(df, x="Strike", y="Charm", color_continuous_scale="RdBu", title="Charm Intensity")
    st.plotly_chart(fig3, use_container_width=True)

with tab4:
    st.markdown("#### Gamma Terrain (3D)")
    try:
        df_hist = pd.read_csv(gamma_file)
        df_hist["Timestamp"] = pd.to_datetime(df_hist["Timestamp"])
        pivoted = df_hist.pivot(index="Timestamp", columns="Strike", values="Gamma_Exposure")
        Z = pivoted.values
        X = pivoted.columns
        Y = pivoted.index.astype(str)
        fig4 = go.Figure(data=[go.Surface(z=Z, x=X, y=Y, colorscale="RdBu")])
        fig4.update_layout(title="Gamma Terrain Over Time",
                           scene=dict(xaxis_title="Strike", yaxis_title="Time", zaxis_title="Gamma"),
                           autosize=True, height=700)
        st.plotly_chart(fig4, use_container_width=True)
    except Exception as e:
        st.error("Could not render gamma terrain.")
        st.code(str(e))

# === Flow Commentary ===
st.markdown("---")
st.subheader("📌 Flow Commentary")
spot_price = st.number_input("Enter Spot Price", value=float(df["Strike"].median()))
if flip_zone != "N/A":
    if spot_price > flip_zone:
        st.success(f"Spot price `{spot_price}` is above Flip Zone `{flip_zone}` → Dealers may be short gamma.")
    elif spot_price < flip_zone:
        st.success(f"Spot price `{spot_price}` is below Flip Zone `{flip_zone}` → Dealers may be long gamma.")
    else:
        st.info(f"Spot price is near flip zone `{flip_zone}`.")
else:
    st.info("No Gamma Flip Zone detected.")

# === Data Table ===
with st.expander("📋 Full Data"):
    st.dataframe(df)
