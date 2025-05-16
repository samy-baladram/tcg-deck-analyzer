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
from image_processor import get_card_thumbnail  # Add this import at the top

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
    
    # Add custom images using annotations instead of HTML
    for i, (label, img) in enumerate(zip([var1, var2], [var1_img, var2_img])):
        if img:
            fig.add_layout_image(
                dict(
                    source=f"data:image/png;base64,{img}",
                    x=0,  # Position at left edge
                    y=i,  # Position at each tick value
                    xref="paper",
                    yref="y",
                    sizex=0.1,  # Width as percentage of plot
                    sizey=0.9,  # Height as percentage of row
                    xanchor="right",
                    yanchor="middle",
                    opacity=1
                )
            )
            
            # Add text label next to image
            fig.add_annotation(
                x=0.01,  # Slightly offset from left edge
                y=i,     # Position at each tick value
                text=label,
                showarrow=False,
                xref="paper",
                yref="y",
                xanchor="left",
                yanchor="middle"
            )
        else:
            # Just add text label if no image
            fig.add_annotation(
                x=0,     # At left edge
                y=i,     # Position at each tick value
                text=label,
                showarrow=False,
                xref="paper",
                yref="y",
                xanchor="left",
                yanchor="middle"
            )
    
    # If mixed is included
    if include_mixed:
        if var1_img and var2_img:
            # Add both images for mixed
            fig.add_layout_image(
                dict(
                    source=f"data:image/png;base64,{var1_img}",
                    x=0,
                    y=2,  # Third position
                    xref="paper",
                    yref="y",
                    sizex=0.05,  # Smaller width
                    sizey=0.9,
                    xanchor="right",
                    yanchor="middle",
                    opacity=1
                )
            )
            
            fig.add_layout_image(
                dict(
                    source=f"data:image/png;base64,{var2_img}",
                    x=0.05,  # Offset from first image
                    y=2,     # Third position
                    xref="paper",
                    yref="y",
                    sizex=0.05,  # Smaller width
                    sizey=0.9,
                    xanchor="right",
                    yanchor="middle",
                    opacity=1
                )
            )
            
            # Add mixed label
            fig.add_annotation(
                x=0.01,
                y=2,
                text="Mixed (1 of each)",
                showarrow=False,
                xref="paper",
                yref="y",
                xanchor="left",
                yanchor="middle"
            )
        else:
            # Just add text if no images
            fig.add_annotation(
                x=0,
                y=2,
                text="Mixed (1 of each)",
                showarrow=False,
                xref="paper",
                yref="y",
                xanchor="left",
                yanchor="middle"
            )
    
    # Hide the default y-axis labels
    fig.update_yaxes(showticklabels=False)
    
    return fig

def create_variant_bar_chart(variant_data):
    """Create horizontal stacked bar chart for variant usage patterns with card images"""
    
    # Extract data from the updated variant data structure
    var1 = variant_data['Var1']
    var2 = variant_data['Var2']
    
    # Determine if Mixed should be included
    include_mixed = variant_data['Mixed'] > 0
    
    # Extract set codes and numbers from variant IDs
    var1_parts = var1.split('-')
    var2_parts = var2.split('-')
    
    var1_set = var1_parts[0] if len(var1_parts) > 0 else ""
    var1_num = var1_parts[1] if len(var1_parts) > 1 else ""
    var2_set = var2_parts[0] if len(var2_parts) > 0 else ""
    var2_num = var2_parts[1] if len(var2_parts) > 1 else ""
    
    # Fetch thumbnails
    var1_img = get_card_thumbnail(var1_set, var1_num) if var1_set and var1_num else None
    var2_img = get_card_thumbnail(var2_set, var2_num) if var2_set and var2_num else None
    
    # Prepare labels for the chart - conditionally include Mixed
    labels = [var1, var2]
    if include_mixed:
        labels.append("Mixed (1 of each)")
    
    # Create tick values and HTML text labels
    tick_vals = list(range(len(labels)))
    tick_text = []
    
    # Create HTML for var1 with image
    if var1_img:
        tick_text.append(f'<img src="data:image/png;base64,{var1_img}" height="40" style="vertical-align:middle; margin-right:10px"> {var1}')
    else:
        tick_text.append(var1)
        
    # Create HTML for var2 with image
    if var2_img:
        tick_text.append(f'<img src="data:image/png;base64,{var2_img}" height="40" style="vertical-align:middle; margin-right:10px"> {var2}')
    else:
        tick_text.append(var2)
    
    # Add Mixed label if needed
    if include_mixed:
        # For mixed, we can show both images side by side
        if var1_img and var2_img:
            tick_text.append(f'<img src="data:image/png;base64,{var1_img}" height="40" style="vertical-align:middle; margin-right:5px"><img src="data:image/png;base64,{var2_img}" height="40" style="vertical-align:middle; margin-right:10px"> Mixed')
        else:
            tick_text.append("Mixed (1 of each)")
    
    # Get counts directly from the variant data
    total_decks = variant_data['Total Decks']
    
    # Calculate percentages
    var1_single_pct = int((variant_data['Single Var1'] / total_decks * 100) if total_decks > 0 else 0)
    var1_double_pct = int((variant_data['Both Var1'] / total_decks * 100) if total_decks > 0 else 0)
    var2_single_pct = int((variant_data['Single Var2'] / total_decks * 100) if total_decks > 0 else 0)
    var2_double_pct = int((variant_data['Both Var2'] / total_decks * 100) if total_decks > 0 else 0)
    mixed_pct = int((variant_data['Mixed'] / total_decks * 100) if total_decks > 0 else 0)
    
    # Prepare data arrays - conditionally include Mixed
    single_data = [var1_single_pct, var2_single_pct]
    double_data = [var1_double_pct, var2_double_pct]
    
    if include_mixed:
        single_data.append(mixed_pct)
        double_data.append(0)  # Mixed has no "double" component
    
    # Format text labels with card symbols
    text_single = [
        f"  🂠 {var1_single_pct}%  " if var1_single_pct >= 20 else (f"  {var1_single_pct}%  " if var1_single_pct > CHART_TEXT_THRESHOLD else ""),
        f"  🂠 {var2_single_pct}%  " if var2_single_pct >= 20 else (f"  {var2_single_pct}%  " if var2_single_pct > CHART_TEXT_THRESHOLD else "")
    ]
    
    text_double = [
        f"  🂠 🂠 {var1_double_pct}%  " if var1_double_pct >= 20 else (f"  {var1_double_pct}%  " if var1_double_pct > CHART_TEXT_THRESHOLD else ""),
        f"  🂠 🂠 {var2_double_pct}%  " if var2_double_pct >= 20 else (f"  {var2_double_pct}%  " if var2_double_pct > CHART_TEXT_THRESHOLD else "")
    ]
    
    # Add Mixed text if included
    if include_mixed:
        text_single.append(f"  🂠 + 🂠 {mixed_pct}%  " if mixed_pct >= 20 else (f"  {mixed_pct}%  " if mixed_pct > CHART_TEXT_THRESHOLD else ""))
        text_double.append("")  # No double for mixed
    
    # Calculate dynamic height based on number of bars
    row_count = len(labels)
    chart_height = max(150, row_count * 60)  # Minimum 150px, 60px per row
    
    # Create figure with numeric y values (we'll replace them with custom labels)
    fig = go.Figure()
    
    # Add 1 Copy bars
    fig.add_trace(go.Bar(
        name='1 Copy',
        y=tick_vals,  # Use numeric values
        x=single_data,
        orientation='h',
        marker_color=CHART_COLORS['pokemon_1'],
        text=text_single,
        textposition='inside',
        insidetextanchor='start',
        textfont=dict(size=CHART_FONT_SIZE),
    ))
    
    # Add 2 Copies bars
    fig.add_trace(go.Bar(
        name='2 Copies',
        y=tick_vals,  # Use numeric values
        x=double_data,
        orientation='h',
        marker_color=CHART_COLORS['pokemon_2'],
        text=text_double,
        textposition='inside',
        insidetextanchor='start',
        textfont=dict(size=CHART_FONT_SIZE),
    ))
    
    # Update layout
    fig.update_layout(
        barmode='stack',
        height=chart_height,  # Dynamic height based on number of bars
        margin=dict(l=0, r=10, t=10, b=10),  # Slightly increased left margin for images
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
    
    # Set custom y-axis tick labels with HTML images
    fig.update_yaxes(
        tickmode='array',
        tickvals=tick_vals,
        ticktext=tick_text,
        tickfont=dict(size=14),
        tickangle=0,  # Ensure labels are horizontal
        side='left',  # Position labels on the left
        showline=False,  # Remove axis line
        showticklabels=True,  # Ensure labels are visible
        rendermode='svg'  # Ensure HTML renders properly
    )
    
    return fig

def display_chart(fig, use_container_width=True):
    """Display a plotly chart with standard config"""
    import streamlit as st
    
    # Create config that enables HTML
    config = {
        'displayModeBar': False,
        'staticPlot': False,  # Allow HTML to render
        'displaylogo': False,
        'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'zoom2d', 'zoomIn2d', 
                                  'zoomOut2d', 'autoScale2d', 'resetScale2d'],
        'doubleClick': False,
        'showTips': False
    }
    
    st.plotly_chart(fig, use_container_width=use_container_width, config=config)
