import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Dealer Flow Dashboard")

st.title("📈 Options Gamma/Charm Dashboard")

uploaded_file = st.file_uploader("Upload parsed_opsdash.xlsx", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df = df.dropna(subset=["Strike", "Gamma Exposure", "Delta Exposure", "Expiry", "Type"])

    df["Strike"] = pd.to_numeric(df["Strike"], errors="coerce")
    df["Expiry"] = pd.to_datetime(df["Expiry"])
    df = df.sort_values("Strike")

    # Auto-detect asset symbol
    symbol = df["Symbol"].dropna().unique()[0] if "Symbol" in df.columns else "Unknown"

    st.markdown(f"### Underlying Asset: `{symbol}`")

    # Expiry filter
    expiries = df["Expiry"].dt.strftime("%Y-%m-%d").unique()
    expiry_choice = st.selectbox("Select Expiry", ["All"] + list(expiries))

    if expiry_choice != "All":
        expiry_dt = pd.to_datetime(expiry_choice)
        df = df[df["Expiry"] == expiry_dt]

    # Flip zone
    grouped = df.groupby("Strike")[["Gamma Exposure", "Delta Exposure"]].sum().reset_index()
    grouped["Gamma Sign"] = grouped["Gamma Exposure"].apply(lambda x: "Positive" if x >= 0 else "Negative")
    flip_row = grouped[grouped["Gamma Sign"] != grouped["Gamma Sign"].shift(1)]
    flip_zone = flip_row["Strike"].iloc[0] if not flip_row.empty else "N/A"

    # Panel Layout
    col1, col2, col3 = st.columns(3)

    # Gamma Exposure Heatmap
    with col1:
        st.markdown("#### Gamma Exposure Heatmap")
        fig = px.density_contour(
            df,
            x="Strike",
            y="Gamma Exposure",
            color="Type",
            title="Gamma Contour (Calls vs Puts)"
        )
        fig.update_traces(contours_coloring="fill", line_width=0)
        st.plotly_chart(fig, use_container_width=True)

    # Breakdown by Strike (Calls vs Puts)
    with col2:
        st.markdown("#### Breakdown by Strike")
        call_data = df[df["Type"] == "Call"].groupby("Strike")["OI"].sum()
        put_data = df[df["Type"] == "Put"].groupby("Strike")["OI"].sum()
        strikes = sorted(set(call_data.index).union(set(put_data.index)))

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=call_data.loc[strikes], y=strikes, name="Calls", orientation='h', marker_color='green'))
        fig2.add_trace(go.Bar(x=-put_data.loc[strikes], y=strikes, name="Puts", orientation='h', marker_color='red'))

        fig2.update_layout(
            barmode='relative',
            title="Net Customer Position by Strike",
            xaxis_title="Contracts (Calls +, Puts -)",
            yaxis_title="Strike",
            height=600
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Charm Placeholder (simplified view)
    with col3:
        st.markdown("#### Charm View (Experimental)")
        charm_df = df.copy()
        charm_df["Charm"] = charm_df["Delta Exposure"] / charm_df["Strike"]  # dummy proxy for visual
        fig3 = px.density_heatmap(charm_df, x="Strike", y="Charm", color_continuous_scale="RdBu", title="Charm by Strike")
        st.plotly_chart(fig3, use_container_width=True)

    # Commentary
    st.markdown("---")
    st.subheader("🧠 Dealer Flow Commentary")

    spot_price = st.number_input("Enter Spot Price", value=float(df["Strike"].median()))
    if flip_zone != "N/A":
        if spot_price > flip_zone:
            st.success(f"Spot price `{spot_price}` is above Gamma Flip Zone `{flip_zone}` → Dealers may be short gamma (higher volatility).")
        elif spot_price < flip_zone:
            st.success(f"Spot price `{spot_price}` is below Gamma Flip Zone `{flip_zone}` → Dealers may be long gamma (vol dampening).")
        else:
            st.warning(f"Spot price is near the flip zone `{flip_zone}` — pinning or reversal risk.")
    else:
        st.info("No Gamma Flip Zone detected.")

    with st.expander("📋 View Full Options Data Table"):
        st.dataframe(df)

else:
    st.info("Upload the `parsed_opsdash.xlsx` file to begin.")
