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
            lambda x: f" {format_percentage(x)}  🂠" if x >= 15 else (format_percentage(x) if x > CHART_TEXT_THRESHOLD else '')
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
            lambda x: f" {format_percentage(x)}  🂠 🂠" if x >= 15 else (format_percentage(x) if x > CHART_TEXT_THRESHOLD else '')
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

def create_variant_bar_chart(variant_df):
    """Create bar chart for variant usage patterns"""
    if variant_df.empty:
        return None
    
    # Prepare data for chart
    chart_data = variant_df[['Card Name', 'Both Var1', 'Both Var2', 'Mixed']]
    chart_data = chart_data.set_index('Card Name')
    
    # Create figure
    fig = go.Figure()
    
    # Add traces for each variant pattern
    fig.add_trace(go.Bar(
        name='Both Var1',
        x=chart_data.index,
        y=chart_data['Both Var1'],
        marker_color='lightblue'
    ))
    
    fig.add_trace(go.Bar(
        name='Both Var2',
        x=chart_data.index,
        y=chart_data['Both Var2'],
        marker_color='darkblue'
    ))
    
    fig.add_trace(go.Bar(
        name='Mixed',
        x=chart_data.index,
        y=chart_data['Mixed'],
        marker_color='purple'
    ))
    
    # Update layout
    fig.update_layout(
        barmode='stack',
        height=400,
        xaxis_title="Card Name",
        yaxis_title="Number of Decks",
        showlegend=True,
        font=dict(size=14)
    )
    
    return fig

def display_chart(fig, use_container_width=True):
    """Display a plotly chart with standard config"""
    import streamlit as st
    st.plotly_chart(fig, use_container_width=use_container_width, config=PLOTLY_CONFIG)
