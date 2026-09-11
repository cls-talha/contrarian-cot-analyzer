import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import INSTRUMENT_CONFIG, GROUPS
from data_manager import get_processed_data, load_data_from_db, calculate_metrics, update_cache

st.set_page_config(page_title="CFTC COT Positioning Dashboard", layout="wide", initial_sidebar_state="expanded")

# Main Title
st.title("CFTC COT Positioning Dashboard")
st.markdown("Track Commitment of Traders (COT) data for major commodities, forex, metals, and indices.")

def draw_main_chart(df: pd.DataFrame, instrument_name: str, key_suffix: str = ""):
    if df.empty:
        st.warning("No data available for this instrument.")
        return

    # Create subplots: main chart for Net Position, lower for Open Interest
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.1, 
                        row_heights=[0.7, 0.3])

    # Plot Commercials (Dealers)
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Comm_Net'],
        mode='lines', name='Commercials (Dealers) Net',
        line=dict(color='#2E7D32', width=2),
        fill='tozeroy', fillcolor='rgba(46, 125, 50, 0.1)'
    ), row=1, col=1)

    # Plot Large Specs (Leveraged)
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Large_Spec_Net'],
        mode='lines', name='Large Specs (Lev) Net',
        line=dict(color='#1565C0', width=2),
        fill='tozeroy', fillcolor='rgba(21, 101, 192, 0.1)'
    ), row=1, col=1)

    # Plot Small Specs (Non-Reportable)
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Small_Spec_Net'],
        mode='lines', name='Small Specs Net',
        line=dict(color='#F57F17', width=2)
    ), row=1, col=1)

    # Add Zero Line
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(0,0,0,0.3)", row=1, col=1)

    # Plot Open Interest on lower subplot
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Open_Interest'],
        mode='lines', name='Open Interest',
        line=dict(color='#757575', width=1),
        fill='tozeroy', fillcolor='rgba(117, 117, 117, 0.1)'
    ), row=2, col=1)

    # Styling for light theme
    fig.update_layout(
        title=f"{instrument_name} COT Net Positioning",
        height=600,
        plot_bgcolor='rgba(255,255,255,1)',
        paper_bgcolor='rgba(255,255,255,1)',
        font=dict(color='#212121'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#E0E0E0')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#E0E0E0', zeroline=False)

    st.plotly_chart(fig, use_container_width=True, key=f"chart_{instrument_name}_{key_suffix}")


def instrument_feed_view():
    st.sidebar.header("Filters")
    
    # Asset Class Filter
    selected_group = st.sidebar.selectbox("Asset Class", ["All"] + GROUPS)
    
    # Date Range Filter
    years = st.sidebar.slider("Lookback Years", min_value=1, max_value=20, value=5)
    
    if st.sidebar.button("Refresh Data"):
        with st.spinner("Fetching latest data from CFTC..."):
            update_cache()
            st.cache_data.clear()
            st.sidebar.success("Data refreshed!")
            
    st.header(f"Markets Feed: {selected_group}")
    
    # Filter instruments by selected group
    if selected_group == "All":
        instruments_to_show = [name for name, config in INSTRUMENT_CONFIG.items() if config["cot_available"]]
    else:
        instruments_to_show = [name for name, config in INSTRUMENT_CONFIG.items() 
                               if config["group"] == selected_group and config["cot_available"]]
    
    if not instruments_to_show:
        st.info("No instruments found.")
        return
        
    for instrument in instruments_to_show:
        contract_code = INSTRUMENT_CONFIG[instrument]["code"]
        df = get_processed_data(contract_code)
            
        if df.empty:
            continue
            
        # Filter by date
        min_date = df['Date'].max() - pd.DateOffset(years=years)
        df_filtered = df[df['Date'] >= min_date]
        
        if df_filtered.empty:
            continue
            
        latest = df_filtered.iloc[0]
        
        st.subheader(f"{instrument}")
        st.caption(f"Latest Report Date: {latest['Date'].strftime('%Y-%m-%d')} | Source: CFTC")
        
        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Commercials Net", 
                      f"{latest['Comm_Net']:,.0f}", 
                      f"{latest.get('Comm_Net_WoW', 0):,.0f} WoW")
                      
        with col2:
            st.metric("Large Specs Net", 
                      f"{latest['Large_Spec_Net']:,.0f}", 
                      f"{latest.get('Large_Spec_Net_WoW', 0):,.0f} WoW")
                      
        with col3:
            # Avoid zero division
            oi = latest['Open_Interest'] if latest['Open_Interest'] else 1
            st.metric("Comm Net % of OI", 
                      f"{(latest['Comm_Net']/oi*100):.1f}%")
                      
        with col4:
            zscore = latest.get('Comm_Net_ZScore_3Y', float('nan'))
            st.metric("Comm 3Y Z-Score", 
                      f"{zscore:.2f}" if not pd.isna(zscore) else "N/A")

        # Main Chart
        draw_main_chart(df_filtered, instrument, key_suffix="feed")
        st.divider()


def draw_zscore_chart(df: pd.DataFrame):
    # Filter out missing values
    df = df.dropna(subset=['Comm_Net_ZScore_3Y', 'Large_Spec_Net_ZScore_3Y'])
    
    # Sort by absolute sigma so highest magnitude is at the top
    # (Plotly draws horizontal bars from bottom up, so we sort ascending)
    df = df.copy()
    df['abs_sigma'] = df['Comm_Net_ZScore_3Y'].abs()
    df = df.sort_values('abs_sigma', ascending=True)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=df['Instrument'],
        x=df['Comm_Net_ZScore_3Y'],
        name='Commercial Z-score',
        orientation='h',
        marker_color='#7BAAF7', # Light Blue
    ))
    
    fig.add_trace(go.Bar(
        y=df['Instrument'],
        x=df['Large_Spec_Net_ZScore_3Y'],
        name='Large Spec Z-score',
        orientation='h',
        marker_color='#81C995', # Soft Green
    ))
    
    fig.update_layout(
        title='Commercial vs Large Speculator Positioning (3-Year Z-Scores)',
        barmode='group',
        height=max(300, len(df) * 25), # Made chart smaller per row
        bargap=0.4, # Added larger gaps between instruments
        bargroupgap=0.1, # Slight gap between Commercial and Spec bars
        plot_bgcolor='rgba(255,255,255,1)',
        paper_bgcolor='rgba(255,255,255,1)',
        font=dict(color='#212121'),
        margin=dict(l=150, r=20, t=60, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
    )
    
    # Set x-axis range and gridlines
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#E0E0E0', range=[-4, 4], tick0=-4, dtick=1)
    
    # Ensure all y-axis labels show and add faint horizontal lines to guide the eye
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.05)', tickmode='linear')
    
    # Add dotted lines at +2 and -2
    fig.add_vline(x=2, line_dash="dot", line_color="rgba(0,0,0,0.5)", line_width=2)
    fig.add_vline(x=-2, line_dash="dot", line_color="rgba(0,0,0,0.5)", line_width=2)
    fig.add_vline(x=0, line_color="rgba(0,0,0,0.2)", line_width=1)
    
    st.plotly_chart(fig, use_container_width=True, key="zscore_bar_chart")


def scanner_view():
    # Use columns to add left and right padding/margins so it's centered
    left_margin, center_col, right_margin = st.columns([1, 6, 1])
    
    with center_col:
        st.header("COT Scanner Overview")
        st.write("Compare net positioning across all configured instruments to spot extremes.")
        
        # Load all latest data for the scanner
        all_latest = []
        
        for name, config in INSTRUMENT_CONFIG.items():
            if not config["cot_available"]:
                continue
                
            df = get_processed_data(config["code"])
            if not df.empty:
                latest = df.iloc[0].to_dict()
                latest['Instrument'] = name
                latest['Asset Class'] = config['group']
                all_latest.append(latest)
                
        if not all_latest:
            st.warning("No data available in the local database. Please run the updater.")
            return
            
        scanner_df = pd.DataFrame(all_latest)
        
        # 1. TABLE
        st.subheader("Current Positioning Data")
        display_df = scanner_df[[
            'Instrument', 'Asset Class', 'Date', 
            'Comm_Net', 'Comm_Net_WoW', 'Comm_Net_ZScore_3Y',
            'Large_Spec_Net', 'Large_Spec_Net_ZScore_3Y'
        ]].copy()
        display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
        st.dataframe(
            display_df.style.format({
                'Comm_Net': "{:,.0f}",
                'Comm_Net_WoW': "{:,.0f}",
                'Comm_Net_ZScore_3Y': "{:.2f}",
                'Large_Spec_Net': "{:,.0f}",
                'Large_Spec_Net_ZScore_3Y': "{:.2f}"
            }).background_gradient(subset=['Comm_Net_ZScore_3Y'], cmap='RdYlGn'),
            use_container_width=True
        )
        
        # 2. GRAPH OF TABLE
        st.subheader("Z-Score Comparison")
        draw_zscore_chart(scanner_df)
        
        st.divider()
        
        # 3. SINGLE INSTRUMENT GRAPH WITH SELECTION MENU
        st.subheader("Detailed Instrument View")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            selected_instrument = st.selectbox("Select Instrument to view details", sorted(display_df['Instrument'].tolist()))
            years = st.slider("Lookback Years", min_value=1, max_value=20, value=5, key="scanner_years")
            
        if selected_instrument:
            contract_code = INSTRUMENT_CONFIG[selected_instrument]["code"]
            df_single = get_processed_data(contract_code)
                
            if not df_single.empty:
                min_date = df_single['Date'].max() - pd.DateOffset(years=years)
                df_filtered = df_single[df_single['Date'] >= min_date]
                
                latest_single = df_filtered.iloc[0]
                st.caption(f"Latest Report Date: {latest_single['Date'].strftime('%Y-%m-%d')} | Source: CFTC")
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Commercials Net", f"{latest_single['Comm_Net']:,.0f}", f"{latest_single.get('Comm_Net_WoW', 0):,.0f} WoW")
                m2.metric("Large Specs Net", f"{latest_single['Large_Spec_Net']:,.0f}", f"{latest_single.get('Large_Spec_Net_WoW', 0):,.0f} WoW")
                oi = latest_single['Open_Interest'] if latest_single['Open_Interest'] else 1
                m3.metric("Comm Net % of OI", f"{(latest_single['Comm_Net']/oi*100):.1f}%")
                zscore = latest_single.get('Comm_Net_ZScore_3Y', float('nan'))
                m4.metric("Comm 3Y Z-Score", f"{zscore:.2f}" if not pd.isna(zscore) else "N/A")
                
                draw_main_chart(df_filtered, selected_instrument, key_suffix="scanner")

# App Navigation
tab1, tab2 = st.tabs(["Markets Feed", "Scanner Overview"])

with tab1:
    instrument_feed_view()
    
with tab2:
    scanner_view()
