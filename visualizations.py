# visualizations.py
"""Visualization functions for creating charts and graphs"""

import plotly.graph_objects as go
import pandas as pd
from config import (
    CHART_COLORS, CHART_MIN_HEIGHT, CHART_ROW_HEIGHT, 
    CHART_FONT_SIZE, CHART_BAR_GAP, CHART_TEXT_THRESHOLD,
    PLOTLY_CONFIG, VAR_CHART_MIN_HEIGHT, VAR_CHART_ROW_HEIGHT
)
from formatters import format_percentage, format_card_label

def create_usage_bar_chart(type_cards, card_type):
    """Create horizontal stacked bar chart for card usage"""
    if type_cards.empty:
        return None
    
    # Create stacked bar chart data
    fig_data = []
    
    for _, card in type_cards.iterrows():
        # Format card label based on type
        if card_type == 'Pokemon':
            card_label = format_card_label(card['card_name'], card['set'], card['num'])
        else:
            card_label = card['card_name']
        
        fig_data.append({
            'Card': card_label,
            '1 Copy': card['pct_1'],
            '2 Copies': card['pct_2'],
            'Total': card['pct_total']
        })
    
    # Create DataFrame for plotting
    plot_df = pd.DataFrame(fig_data)
    
    # Create figure
    fig = go.Figure()
    
    # Add bars for each count type
    fig.add_trace(go.Bar(
        name='1 Copy',
        y=plot_df['Card'],
        x=plot_df['1 Copy'],
        orientation='h',
        marker_color=CHART_COLORS[f'{card_type.lower()}_1'],
        text=plot_df['1 Copy'].apply(
            lambda x: f" {format_percentage(x)}   <b><span style='font-size: 22px; '>🂠</span></b>" if x >= 20 else (f" {format_percentage(x)} " if x > CHART_TEXT_THRESHOLD else '')
        ),
        textposition='inside',
        textfont=dict(size=CHART_FONT_SIZE),
        insidetextanchor='start'
    ))
    
    fig.add_trace(go.Bar(
        name='2 Copies',
        y=plot_df['Card'],
        x=plot_df['2 Copies'],
        orientation='h',
        marker_color=CHART_COLORS[f'{card_type.lower()}_2'],
        text=plot_df['2 Copies'].apply(
            lambda x: f" {format_percentage(x)}   <b><span style='font-size: 22px;'>🂠🂠</span></b>" if x >= 20 else (f" {format_percentage(x)} " if x > CHART_TEXT_THRESHOLD else '')
        ),
        textposition='inside',
        textfont=dict(size=CHART_FONT_SIZE),
        insidetextanchor='start'
    ))
    
    # Update layout
    fig.update_layout(
        barmode='stack',
        height=max(CHART_MIN_HEIGHT, len(type_cards) * CHART_ROW_HEIGHT),
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis_title="",
        xaxis=dict(
            range=[0, 100],
            showticklabels=False,
        ),
        showlegend=False,
        legend=dict(
            orientation="h", 
            yanchor="top", 
            y=-0.06, 
            xanchor="right", 
            x=1
        ),
        font=dict(size=CHART_FONT_SIZE),
        yaxis=dict(tickfont=dict(size=CHART_FONT_SIZE)),
        bargap=CHART_BAR_GAP,
        uniformtext=dict(minsize=12, mode='show')
    )
    
    # Reverse the order to show highest usage at top
    fig.update_yaxes(autorange='reversed')
    
    return fig

def create_variant_bar_chart(variant_data):
    """Create horizontal stacked bar chart for variant usage patterns"""
    
    # Extract data from the updated variant data structure
    var1 = variant_data['Var1']
    var2 = variant_data['Var2']
    
    # Determine if Mixed should be included
    include_mixed = variant_data['Mixed'] > 0
    
    # Prepare labels for the chart - conditionally include Mixed
    # Start with Mixed at the top, then var2, then var1 for inverted order
    labels = []
    if include_mixed:
        labels.append("1 of each")
    labels.extend([var2, var1])  # Add in reverse order
    
    # Get counts directly from the variant data
    total_decks = variant_data['Total Decks']
    
    # Calculate percentages
    var1_single_pct = int((variant_data['Single Var1'] / total_decks * 100) if total_decks > 0 else 0)
    var1_double_pct = int((variant_data['Both Var1'] / total_decks * 100) if total_decks > 0 else 0)
    var2_single_pct = int((variant_data['Single Var2'] / total_decks * 100) if total_decks > 0 else 0)
    var2_double_pct = int((variant_data['Both Var2'] / total_decks * 100) if total_decks > 0 else 0)
    mixed_pct = int((variant_data['Mixed'] / total_decks * 100) if total_decks > 0 else 0)
    
    # Prepare data arrays - arrange in the same order as labels
    single_data = []
    double_data = []
    text_single = []
    text_double = []
    
    # Add Mixed data first if needed
    if include_mixed:
        single_data.append(mixed_pct)
        double_data.append(0)  # Mixed has no "double" component
        text_single.append(f" {mixed_pct}% <b><span style='font-size: 22px;'>🂠+🂠</span></b>" if mixed_pct > 0 else "")
        text_double.append("")  # No double for mixed
    
    # Add var2 data
    single_data.append(var2_single_pct)
    double_data.append(var2_double_pct)
    text_single.append(f" {var2_single_pct}%  <b><span style='font-size: 22px;'>🂠</span></b>" if var2_single_pct > 0 else "")
    text_double.append(f" {var2_double_pct}%  <b><span style='font-size: 22px;'>🂠🂠</span></b>" if var2_double_pct > 0 else "")
    
    # Add var1 data
    single_data.append(var1_single_pct)
    double_data.append(var1_double_pct)
    # FIXED: These were incorrectly showing var2 values
    text_single.append(f" {var1_single_pct}%  <b><span style='font-size: 22px;'>🂠</span></b>" if var1_single_pct > 0 else "")  # Fixed
    text_double.append(f" {var1_double_pct}%  <b><span style='font-size: 22px;'>🂠🂠</span></b>" if var1_double_pct > 0 else "")  # Fixed
    
    # Create figure
    fig = go.Figure()
    
    # Add 1 Copy bars
    fig.add_trace(go.Bar(
        name='1 Copy',
        y=labels,
        x=single_data,
        orientation='h',
        marker_color=CHART_COLORS['pokemon_1'],
        text=text_single,
        textposition='auto',
        insidetextanchor='start',
        textfont=dict(size=CHART_FONT_SIZE),
    ))
    
    # Add 2 Copies bars
    fig.add_trace(go.Bar(
        name='2 Copies',
        y=labels,
        x=double_data,
        orientation='h',
        marker_color=CHART_COLORS['pokemon_2'],
        text=text_double,
        textposition='auto',
        insidetextanchor='start',
        textfont=dict(size=CHART_FONT_SIZE),
    ))
    
    # Update layout with fixed height and larger y-axis labels
    fig.update_layout(
        barmode='stack',
        height=max(VAR_CHART_MIN_HEIGHT, len(labels) * VAR_CHART_ROW_HEIGHT),
        #height=220,  # Fixed height to match images
        margin=dict(l=0, r=0, t=20, b=0),
        xaxis_title="",
        xaxis=dict(
            range=[0, 105],  # Extend range beyond 100 to add padding
            showticklabels=False,
        ),
        showlegend=False,
        bargap=CHART_BAR_GAP,
        uniformtext=dict(minsize=12, mode='show'),
        paper_bgcolor='rgba(0,0,0,0)',  # Transparent background
        plot_bgcolor='rgba(0,0,0,0)',   # Transparent plot area
    )
    
    # Increase y-axis label font size
    fig.update_yaxes(
        tickfont=dict(size=16)  # Larger font size for y-axis labels
    )
    
    return fig

def display_chart(fig, use_container_width=True):
    """Display a plotly chart with standard config"""
    import streamlit as st
    
    # Enable HTML in labels
    config = PLOTLY_CONFIG.copy()
    config['displayModeBar'] = False
    
    st.plotly_chart(fig, use_container_width=use_container_width, config=config)
