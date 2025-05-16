# visualizations.py
"""Visualization functions for creating charts and graphs"""

import plotly.graph_objects as go
import pandas as pd
from config import (
    CHART_COLORS, CHART_MIN_HEIGHT, CHART_ROW_HEIGHT, 
    CHART_FONT_SIZE, CHART_BAR_GAP, CHART_TEXT_THRESHOLD,
    PLOTLY_CONFIG
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
            lambda x: f" {format_percentage(x)}  🂠" if x >= 20 else (f" {format_percentage(x)} " if x > CHART_TEXT_THRESHOLD else '')
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
            lambda x: f" {format_percentage(x)}  🂠 🂠" if x >= 20 else (f" {format_percentage(x)} " if x > CHART_TEXT_THRESHOLD else '')
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
    """Create horizontal bar chart for variant usage patterns"""
    
    # Extract data
    card_name = variant_data['Card Name']
    variant_list = variant_data['Variants'].split(', ')
    
    # Prepare data for chart
    var1_count = variant_data['Both Var1']
    var2_count = variant_data['Both Var2']
    mixed_count = variant_data['Mixed']
    
    # Total count for percentage calculation
    total_decks = variant_data['Total Decks']
    
    # Calculate percentages
    var1_pct = int((var1_count / total_decks * 100) if total_decks > 0 else 0)
    var2_pct = int((var2_count / total_decks * 100) if total_decks > 0 else 0)
    mixed_pct = int((mixed_count / total_decks * 100) if total_decks > 0 else 0)
    
    # Create figure
    fig = go.Figure()
    
    # Format variant labels
    var1_label = f"{variant_list[0]}" if len(variant_list) > 0 else "Variant 1"
    var2_label = f"{variant_list[1]}" if len(variant_list) > 1 else "Variant 2"
    
    # Add bars for each variant pattern
    # Var1 - Both copies
    fig.add_trace(go.Bar(
        name='Both copies of Variant 1',
        y=[var1_label],
        x=[var1_pct],
        orientation='h',
        marker_color=CHART_COLORS['pokemon_1'],
        text=[f"  🂠 🂠 {var1_pct}%  " if var1_pct >= 20 else (f"  {var1_pct}%  " if var1_pct > CHART_TEXT_THRESHOLD else "")],
        textposition='inside',
        insidetextanchor='start',
        textfont=dict(size=CHART_FONT_SIZE),
    ))
    
    # Var2 - Both copies
    fig.add_trace(go.Bar(
        name='Both copies of Variant 2',
        y=[var2_label],
        x=[var2_pct],
        orientation='h',
        marker_color=CHART_COLORS['pokemon_2'],
        text=[f"  🂠 🂠 {var2_pct}%  " if var2_pct >= 20 else (f"  {var2_pct}%  " if var2_pct > CHART_TEXT_THRESHOLD else "")],
        textposition='inside',
        insidetextanchor='start',
        textfont=dict(size=CHART_FONT_SIZE),
    ))
    
    # Mixed - One of each
    fig.add_trace(go.Bar(
        name='Mixed (1 of each)',
        y=["Mixed (1 of each)"],
        x=[mixed_pct],
        orientation='h',
        marker_color="#A378FF",  # Purple for mixed
        text=[f"  🂠 + 🂠 {mixed_pct}%  " if mixed_pct >= 20 else (f"  {mixed_pct}%  " if mixed_pct > CHART_TEXT_THRESHOLD else "")],
        textposition='inside',
        insidetextanchor='start',
        textfont=dict(size=CHART_FONT_SIZE),
    ))
    
    # Update layout
    fig.update_layout(
        height=150,  # Smaller height for expander
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="",
        xaxis=dict(
            range=[0, 105],  # Extend range beyond 100 to add padding
            showticklabels=False,
        ),
        showlegend=False,
        bargap=0.3,
        uniformtext=dict(minsize=12, mode='show'),
        paper_bgcolor='rgba(0,0,0,0)',  # Transparent background
        plot_bgcolor='rgba(0,0,0,0)',   # Transparent plot area
    )
    
    return fig

def display_chart(fig, use_container_width=True):
    """Display a plotly chart with standard config"""
    import streamlit as st
    st.plotly_chart(fig, use_container_width=use_container_width, config=PLOTLY_CONFIG)
