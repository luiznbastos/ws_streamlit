"""
Chart and visualization helpers for football match analytics.

This module provides functions to create various visualizations including
match overview charts, possession chain visualizations, zone heatmaps,
and player performance charts.
"""

import plotly.graph_objects as go
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import Pitch
import numpy as np
from typing import Dict

PITCH_COLOR = '#1a1a1a'
LINE_COLOR = '#ffffff'
FIG_BG_COLOR = '#0a0a0a'
HOME_COLOR = '#4ade80'
AWAY_COLOR = '#818cf8'
GRAY_COLOR = '#2a2a2a'
HOME_COLOR_DIM = '#2d7a4d'
AWAY_COLOR_DIM = '#4a5299'

def _create_empty_figure(message: str = 'No data available') -> plt.Figure:
    """Create an empty figure with a message."""
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.text(0.5, 0.5, message, ha='center', va='center', 
           fontsize=16, color='gray')
    ax.axis('off')
    return fig

def _scale_coordinates(x: float, y: float) -> tuple:
    """Scale coordinates from 0-100 to pitch dimensions."""
    return (x * 1.2, y * 0.8)


def create_match_overview_chart(match_data: dict, home_team_name: str, 
                                away_team_name: str, home_score: int = 0, 
                                away_score: int = 0) -> go.Figure:
    """
    Create a horizontal bar chart for match overview statistics.
    
    Args:
        match_data: Dictionary with metrics like {'shots': {'home': 10, 'away': 5}, ...}
        home_team_name: Name of home team
        away_team_name: Name of away team
        home_score: Home team score
        away_score: Away team score
    
    Returns:
        Plotly Figure object
    """
    metrics_config = [
        {'key': 'shots', 'label': 'Shots'},
        {'key': 'passes', 'label': 'Passes'},
        {'key': 'dribbles', 'label': 'Dribbles'},
        {'key': 'tackles_attempted', 'label': 'Tackles Attempted'},
        {'key': 'interceptions', 'label': 'Interceptions'},
        {'key': 'clearances', 'label': 'Clearances'},
        {'key': 'blocks', 'label': 'Blocks'},
        {'key': 'offsides', 'label': 'Offsides'},
        {'key': 'fouls', 'label': 'Fouls'},
        {'key': 'aerial_duels', 'label': 'Aerial Duels'},
        {'key': 'touches', 'label': 'Touches'},
        {'key': 'loss_of_possession', 'label': 'Loss of Possession'},
        {'key': 'errors', 'label': 'Errors'},
        {'key': 'saves', 'label': 'Saves'},
        {'key': 'claims', 'label': 'Claims'},
        {'key': 'punches', 'label': 'Punches'}
    ]
    
    fig = go.Figure()
    y_position = len(metrics_config) - 1
    
    for metric in metrics_config:
        key = metric['key']
        home_val = match_data[key]['home']
        away_val = match_data[key]['away']
        
        total = home_val + away_val
        if total > 0:
            home_pct = (home_val / total) * 50
            away_pct = (away_val / total) * 50
        else:
            home_pct = 25
            away_pct = 25
        
        home_wins = home_val > away_val
        away_wins = away_val > home_val
        
        home_bar_color = HOME_COLOR if home_wins else HOME_COLOR_DIM
        away_bar_color = AWAY_COLOR if away_wins else AWAY_COLOR_DIM
        
        # Home team bar (left side)
        fig.add_trace(go.Bar(
            x=[home_pct], y=[y_position], orientation='h',
            marker=dict(color=home_bar_color, line=dict(width=0)),
            showlegend=False, hovertemplate=f'Home: {home_val}<extra></extra>',
            base=50-home_pct, width=0.25
        ))
        
        # Gray bar on left
        fig.add_trace(go.Bar(
            x=[50-home_pct], y=[y_position], orientation='h',
            marker=dict(color=GRAY_COLOR, line=dict(width=0)),
            showlegend=False, hoverinfo='skip', base=0, width=0.25
        ))
        
        # Away team bar (right side)
        fig.add_trace(go.Bar(
            x=[away_pct], y=[y_position], orientation='h',
            marker=dict(color=away_bar_color, line=dict(width=0)),
            showlegend=False, hovertemplate=f'Away: {away_val}<extra></extra>',
            base=50, width=0.25
        ))
        
        # Gray bar on right
        fig.add_trace(go.Bar(
            x=[50-away_pct], y=[y_position], orientation='h',
            marker=dict(color=GRAY_COLOR, line=dict(width=0)),
            showlegend=False, hoverinfo='skip', base=50+away_pct, width=0.25
        ))
        
        # Metric label
        fig.add_annotation(
            x=50, y=y_position + 0.3, text=metric['label'],
            showarrow=False, font=dict(size=16, color='#a0a0a0', family='Arial'),
            xanchor='center', yanchor='bottom'
        )
        
        # Value labels
        fig.add_annotation(
            x=2, y=y_position + 0.3, text=str(home_val),
            showarrow=False, font=dict(size=20, color='white', family='Arial'),
            xanchor='left', yanchor='bottom'
        )
        fig.add_annotation(
            x=98, y=y_position + 0.3, text=str(away_val),
            showarrow=False, font=dict(size=20, color='white', family='Arial'),
            xanchor='right', yanchor='bottom'
        )
        
        y_position -= 1
    
    # Center separator lines
    for i in range(len(metrics_config)):
        fig.add_shape(
            type="line", x0=50, y0=i-0.4, x1=50, y1=i+0.4,
            line=dict(color="#0a0a0a", width=3), layer="above"
        )
    
    # Update layout
    fig.update_layout(
        height=1000, width=1000,
        plot_bgcolor='#1a1a1a', paper_bgcolor='#0a0a0a',
        font=dict(color='white', family='Arial'),
        barmode='overlay',
        title=dict(
            text=f'{home_team_name} {home_score} - {away_score} {away_team_name}',
            font=dict(size=28, color='white', family='Arial'),
            x=0.5, xanchor='center', y=0.98, yanchor='top'
        ),
        margin=dict(l=100, r=100, t=100, b=40),
        showlegend=False,
        xaxis=dict(range=[0, 100], showticklabels=False, 
                  showgrid=False, zeroline=False),
        yaxis=dict(range=[-0.5, len(metrics_config) - 0.5], 
                  showticklabels=False, showgrid=False, zeroline=False)
    )
    
    return fig

# ============================================================================
# Possession Chain Visualization
# ============================================================================

def create_possession_chains_pitch(chains_df: pd.DataFrame, 
                                   team_name: str) -> plt.Figure:
    """
    Create a pitch visualization showing possession chains with pass lines.
    
    Args:
        chains_df: DataFrame with columns: possession_chain, x, y, end_x, end_y, minute, second
        team_name: Name of the team for title
    
    Returns:
        matplotlib Figure object
    """
    if chains_df.empty:
        return _create_empty_figure('No possession chain data available')
    
    pitch = Pitch(pitch_type='statsbomb', pitch_color=PITCH_COLOR, 
                 line_color=LINE_COLOR, line_zorder=2, linewidth=1.5)
    fig, ax = pitch.draw(figsize=(14, 10))
    
    unique_chains = chains_df['possession_chain'].unique()
    num_chains = len(unique_chains)
    
    if num_chains == 0:
        ax.text(60, 40, 'No possession chains found', 
               ha='center', va='center', fontsize=16, color='gray')
        return fig
    
    colors = plt.cm.viridis(np.linspace(0, 1, num_chains))
    
    for idx, chain_id in enumerate(unique_chains):
        chain_data = chains_df[chains_df['possession_chain'] == chain_id].copy()
        chain_data = chain_data.sort_values(['minute', 'second'])
        
        if chain_data.empty:
            continue
        
        color = colors[idx]
        first_pass = chain_data.iloc[0]
        last_pass = chain_data.iloc[-1]
        
        chain_start_x, chain_start_y = _scale_coordinates(
            first_pass['x'], first_pass['y']
        ) if pd.notna(first_pass['x']) else (None, None)
        chain_end_x, chain_end_y = _scale_coordinates(
            last_pass['end_x'], last_pass['end_y']
        ) if pd.notna(last_pass['end_x']) else (None, None)
        
        for pass_idx, (_, row) in enumerate(chain_data.iterrows()):
            if not all(pd.notna([row['x'], row['y'], row['end_x'], row['end_y']])):
                continue
            
            x_start, y_start = _scale_coordinates(row['x'], row['y'])
            x_end, y_end = _scale_coordinates(row['end_x'], row['end_y'])
            
            pitch.lines(x_start, y_start, x_end, y_end, ax=ax, 
                       color=color, alpha=0.6, linewidth=2, zorder=3)
            
            # Draw arrow in the middle
            x_mid = (x_start + x_end) / 2
            y_mid = (y_start + y_end) / 2
            dx = x_end - x_start
            dy = y_end - y_start
            length = np.sqrt(dx**2 + dy**2)
            
            if length > 0:
                dx_norm = dx / length
                dy_norm = dy / length
                arrow_length = min(length * 0.3, 5)
                
                arrow_start_x = x_mid - (arrow_length / 2) * dx_norm
                arrow_start_y = y_mid - (arrow_length / 2) * dy_norm
                arrow_end_x = x_mid + (arrow_length / 2) * dx_norm
                arrow_end_y = y_mid + (arrow_length / 2) * dy_norm
                
                pitch.arrows(arrow_start_x, arrow_start_y, arrow_end_x, arrow_end_y,
                           ax=ax, color=color, alpha=0.8, width=2,
                           headwidth=4, headlength=3, zorder=4)
            
            # Mark chain start and end
            if pass_idx == 0 and chain_start_x is not None:
                pitch.scatter(chain_start_x, chain_start_y, ax=ax, s=200,
                             marker='o', color=color, alpha=0.9,
                             edgecolors='white', linewidths=3, zorder=5)
            elif pass_idx == len(chain_data) - 1 and chain_end_x is not None:
                pitch.scatter(chain_end_x, chain_end_y, ax=ax, s=200,
                             marker='*', color=color, alpha=0.9,
                             edgecolors='white', linewidths=3, zorder=5)
            else:
                pitch.scatter(x_start, y_start, ax=ax, s=30, 
                             color=color, alpha=0.8, zorder=4)
                pitch.scatter(x_end, y_end, ax=ax, s=30, 
                             color=color, alpha=0.8, zorder=4)
        
        # Add legend (only once)
        if idx == 0:
            from matplotlib.lines import Line2D
            legend_elements = [
                Line2D([0], [0], marker='o', color='w', markerfacecolor='white',
                      markersize=12, label='Chain Start', linestyle='None', markeredgewidth=2),
                Line2D([0], [0], marker='*', color='w', markerfacecolor='white',
                      markersize=15, label='Chain End', linestyle='None', markeredgewidth=2)
            ]
            ax.legend(handles=legend_elements, loc='upper left', 
                     facecolor=PITCH_COLOR, edgecolor='white', 
                     labelcolor='white', fontsize=10)
    
    ax.set_title(f'{team_name} - Possession Chains\n'
                f'({num_chains} chains, {len(chains_df)} passes)',
                fontsize=16, color='white', pad=20)
    fig.patch.set_facecolor(FIG_BG_COLOR)
    
    return fig


def create_zone_heatmap(zones_df: pd.DataFrame, team_name: str, 
                       event_type: str = "All Events") -> plt.Figure:
    """
    Create a zone heatmap visualization showing event distribution.
    
    Args:
        zones_df: DataFrame with columns: start_zone_id, start_bin_x, start_bin_y, event_count
        team_name: Name of the team for title
        event_type: Type of events being visualized
    
    Returns:
        matplotlib Figure object
    """
    if zones_df.empty:
        return _create_empty_figure('No zone data available')
    
    pitch = Pitch(pitch_type='statsbomb', pitch_color=PITCH_COLOR,
                 line_color=LINE_COLOR, line_zorder=2, linewidth=1.5)
    fig, ax = pitch.draw(figsize=(14, 10))
    
    pitch_length = 120
    pitch_width = 80
    num_zones_x = 6
    num_zones_y = 5
    
    zone_width = pitch_length / num_zones_x
    zone_height = pitch_width / num_zones_y
    
    max_count = zones_df['event_count'].max() if not zones_df.empty else 1
    min_count = zones_df['event_count'].min() if not zones_df.empty else 0
    
    norm = plt.Normalize(vmin=min_count, vmax=max_count)
    cmap = plt.cm.viridis
    
    for _, row in zones_df.iterrows():
        bin_x = int(row['start_bin_x'])
        bin_y = int(row['start_bin_y'])
        count = int(row['event_count'])
        
        x_center = (bin_x - 0.5) * zone_width
        y_center = (bin_y - 0.5) * zone_height
        
        x_left = x_center - zone_width / 2
        x_right = x_center + zone_width / 2
        y_bottom = y_center - zone_height / 2
        y_top = y_center + zone_height / 2
        
        color = cmap(norm(count))
        
        rect = plt.Rectangle((x_left, y_bottom), zone_width, zone_height,
                            facecolor=color, alpha=0.7, edgecolor='white',
                            linewidth=1, zorder=1)
        ax.add_patch(rect)
        
        ax.text(x_center, y_center, str(count), ha='center', va='center',
               fontsize=10, color='white', weight='bold', zorder=3)
    
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, pad=0.02)
    cbar.set_label('Event Count', rotation=270, labelpad=20, color='white')
    cbar.ax.yaxis.set_tick_params(color='white')
    cbar.ax.tick_params(colors='white')
    
    ax.set_title(f'{team_name} - Zone Heatmap ({event_type})\n'
                f'({len(zones_df)} zones with events)',
                fontsize=16, color='white', pad=20)
    fig.patch.set_facecolor(FIG_BG_COLOR)
    
    return fig


def create_player_passes_pitch(passes_df: pd.DataFrame, 
                               player_name: str) -> plt.Figure:
    """
    Create a pitch visualization showing a player's passes.
    
    Args:
        passes_df: DataFrame with columns: x, y, end_x, end_y, outcome_type
        player_name: Name of the player for title
    
    Returns:
        matplotlib Figure object
    """
    if passes_df.empty:
        return _create_empty_figure('No pass data available')
    
    pitch = Pitch(pitch_type='statsbomb', pitch_color=PITCH_COLOR,
                 line_color=LINE_COLOR, line_zorder=2, linewidth=1.5)
    fig, ax = pitch.draw(figsize=(14, 10))
    
    successful_passes = passes_df[passes_df['outcome_type'].str.lower() == 'successful']
    unsuccessful_passes = passes_df[passes_df['outcome_type'].str.lower() != 'successful']
    
    # Draw successful passes in green
    for _, row in successful_passes.iterrows():
        if all(pd.notna([row['x'], row['y'], row['end_x'], row['end_y']])):
            x_start, y_start = _scale_coordinates(row['x'], row['y'])
            x_end, y_end = _scale_coordinates(row['end_x'], row['end_y'])
            
            pitch.arrows(x_start, y_start, x_end, y_end, ax=ax,
                        color='#2ecc71', alpha=0.6, width=2,
                        headwidth=3, headlength=2, zorder=3)
    
    # Draw unsuccessful passes in red
    for _, row in unsuccessful_passes.iterrows():
        if all(pd.notna([row['x'], row['y'], row['end_x'], row['end_y']])):
            x_start, y_start = _scale_coordinates(row['x'], row['y'])
            x_end, y_end = _scale_coordinates(row['end_x'], row['end_y'])
            
            pitch.arrows(x_start, y_start, x_end, y_end, ax=ax,
                        color='#e74c3c', alpha=0.6, width=2,
                        headwidth=3, headlength=2, zorder=3, linestyle='--')
    
    # Add legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='#2ecc71', lw=3, label='Successful Passes'),
        Line2D([0], [0], color='#e74c3c', lw=3, linestyle='--', label='Unsuccessful Passes')
    ]
    ax.legend(handles=legend_elements, loc='upper right',
             facecolor=PITCH_COLOR, edgecolor='white',
             labelcolor='white', fontsize=10)
    
    success_count = len(successful_passes)
    total_count = len(passes_df)
    success_rate = (success_count / total_count * 100) if total_count > 0 else 0
    
    ax.set_title(f'{player_name} - Passes\n'
                f'({total_count} total, {success_count} successful, {success_rate:.1f}% success rate)',
                fontsize=16, color='white', pad=20)
    fig.patch.set_facecolor(FIG_BG_COLOR)
    
    return fig

def create_player_shots_pitch(shots_df: pd.DataFrame, 
                              player_name: str) -> plt.Figure:
    """
    Create a pitch visualization showing a player's shots.
    
    Args:
        shots_df: DataFrame with columns: x, y, main_type, outcome_type
        player_name: Name of the player for title
    
    Returns:
        matplotlib Figure object
    """
    if shots_df.empty:
        return _create_empty_figure('No shot data available')
    
    pitch = Pitch(pitch_type='statsbomb', pitch_color=PITCH_COLOR,
                 line_color=LINE_COLOR, line_zorder=2, linewidth=1.5)
    fig, ax = pitch.draw(figsize=(14, 10))
    
    goals = shots_df[shots_df['main_type'].str.lower() == 'goal']
    other_shots = shots_df[shots_df['main_type'].str.lower() != 'goal']
    
    # Draw goals with gold stars
    for _, row in goals.iterrows():
        if pd.notna(row['x']) and pd.notna(row['y']):
            x_scaled, y_scaled = _scale_coordinates(row['x'], row['y'])
            pitch.scatter(x_scaled, y_scaled, ax=ax, s=400, marker='*',
                         color='#f1c40f', alpha=0.9, edgecolors='white',
                         linewidths=2, zorder=4)
    
    # Draw other shots with red circles
    for _, row in other_shots.iterrows():
        if pd.notna(row['x']) and pd.notna(row['y']):
            x_scaled, y_scaled = _scale_coordinates(row['x'], row['y'])
            pitch.scatter(x_scaled, y_scaled, ax=ax, s=150, marker='o',
                         color='#e74c3c', alpha=0.7, edgecolors='white',
                         linewidths=1.5, zorder=3)
    
    # Add legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='*', color='w', markerfacecolor='#f1c40f',
              markersize=15, label='Goals', linestyle='None'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#e74c3c',
              markersize=10, label='Shots', linestyle='None')
    ]
    ax.legend(handles=legend_elements, loc='upper right',
             facecolor=PITCH_COLOR, edgecolor='white',
             labelcolor='white', fontsize=10)
    
    goals_count = len(goals)
    total_count = len(shots_df)
    conversion_rate = (goals_count / total_count * 100) if total_count > 0 else 0
    
    ax.set_title(f'{player_name} - Shots\n'
                f'({total_count} total, {goals_count} goals, {conversion_rate:.1f}% conversion rate)',
                fontsize=16, color='white', pad=20)
    fig.patch.set_facecolor(FIG_BG_COLOR)
    
    return fig
