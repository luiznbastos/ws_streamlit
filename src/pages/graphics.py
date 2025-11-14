import sys
from pathlib import Path
import traceback

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
import logging

from src.database import db_client
from src.utils.redshift_queries import (
    get_match_list,
    get_match_overview_data,
    get_team_names,
    get_possession_chains,
    get_chain_summary,
    get_zone_event_counts,
    get_zone_event_totals,
    get_match_players,
    get_player_passes,
    get_player_shots
)
from src.utils.chart_helpers import (
    create_match_overview_chart,
    create_possession_chains_pitch,
    create_zone_heatmap,
    create_player_passes_pitch,
    create_player_shots_pitch
)

logger = logging.getLogger(__name__)

# ============================================================================
# Helper Functions
# ============================================================================

def create_team_options(home_team_id: int, away_team_id: int, 
                       home_team_name: str, away_team_name: str) -> dict:
    """Create team options dictionary for selectboxes."""
    return {
        f"{home_team_name} (Home)": home_team_id,
        f"{away_team_name} (Away)": away_team_id
    }

def get_selected_team_name(selected_team_id: int, home_team_id: int, 
                          home_team_name: str, away_team_name: str) -> str:
    """Get team name based on selected team ID."""
    return home_team_name if selected_team_id == home_team_id else away_team_name

def display_error(error_message: str, error: Exception, show_traceback: bool = True):
    """Display error message with optional traceback."""
    st.error(error_message)
    if show_traceback:
        with st.expander("🔍 Error Details"):
            st.code(traceback.format_exc())

def display_possession_chain_stats(chains_df: pd.DataFrame, selected_chain_id: int = None):
    """Display possession chain statistics in the left column."""
    st.markdown("### 📈 Possession Chains Statistics")
    st.markdown("---")
    
    if selected_chain_id is None:
        total_chains = chains_df['possession_chain'].nunique()
        total_passes = len(chains_df)
        avg_passes = total_passes / total_chains if total_chains > 0 else 0
        
        st.metric("Total Chains", total_chains)
        st.metric("Total Passes", total_passes)
        st.metric("Average Passes per Chain", f"{avg_passes:.1f}")
        
        st.markdown("---")
        st.markdown("**Chain Breakdown:**")
        chain_counts = chains_df.groupby('possession_chain').size().sort_values(ascending=False)
        for chain_id, count in chain_counts.head(10).items():
            st.write(f"- Chain {int(chain_id)}: {int(count)} passes")
        if len(chain_counts) > 10:
            st.write(f"... and {len(chain_counts) - 10} more chains")
    else:
        st.metric("Chain ID", selected_chain_id)
        st.metric("Total Passes in Chain", len(chains_df))
        
        st.markdown("---")
        st.markdown("**Pass Details:**")
        successful_passes = len(chains_df[chains_df['outcome_type'].str.lower() == 'successful'])
        unsuccessful_passes = len(chains_df) - successful_passes
        st.write(f"- Successful: {successful_passes}")
        st.write(f"- Unsuccessful: {unsuccessful_passes}")
        if len(chains_df) > 0:
            success_rate = (successful_passes / len(chains_df)) * 100
            st.write(f"- Success Rate: {success_rate:.1f}%")

def display_pass_stats(passes_df: pd.DataFrame):
    """Display pass statistics in the left column."""
    st.markdown("### 📊 Pass Statistics")
    st.markdown("---")
    
    successful = passes_df[passes_df['outcome_type'].str.lower() == 'successful']
    total = len(passes_df)
    successful_count = len(successful)
    unsuccessful_count = total - successful_count
    success_rate = (successful_count / total * 100) if total > 0 else 0
    
    st.metric("Total Passes", total)
    st.metric("Successful", successful_count)
    st.metric("Unsuccessful", unsuccessful_count)
    st.metric("Success Rate", f"{success_rate:.1f}%")
    
    passes_with_coords = passes_df[
        passes_df[['x', 'y', 'end_x', 'end_y']].notna().all(axis=1)
    ]
    if not passes_with_coords.empty:
        pass_lengths = (
            ((passes_with_coords['end_x'] - passes_with_coords['x'])**2 + 
             (passes_with_coords['end_y'] - passes_with_coords['y'])**2)**0.5
        )
        avg_length = pass_lengths.mean()
        st.markdown("---")
        st.metric("Average Pass Length", f"{avg_length:.1f} units")
    else:
        st.markdown("---")
        st.write("_No coordinate data for pass length calculation_")

def display_shot_stats(shots_df: pd.DataFrame):
    """Display shot statistics in the left column."""
    st.markdown("### 📊 Shot Statistics")
    st.markdown("---")
    
    goals = shots_df[shots_df['main_type'].str.lower() == 'goal']
    total = len(shots_df)
    goals_count = len(goals)
    conversion_rate = (goals_count / total * 100) if total > 0 else 0
    
    on_target = shots_df[
        (shots_df['main_type'].str.lower() == 'goal') |
        (shots_df['outcome_type'].str.lower() == 'successful')
    ]
    on_target_count = len(on_target)
    off_target_count = total - on_target_count
    
    st.metric("Total Shots", total)
    st.metric("Goals", goals_count)
    st.metric("Shots on Target", on_target_count)
    st.metric("Shots off Target", off_target_count)
    st.metric("Conversion Rate", f"{conversion_rate:.1f}%")
    
    if total > 0:
        st.markdown("---")
        st.markdown("**Shot Types:**")
        shot_types = shots_df['main_type'].value_counts()
        for shot_type, count in shot_types.items():
            st.write(f"- {shot_type}: {count}")

# ============================================================================
# Page Configuration
# ============================================================================

st.set_page_config(page_title="WS Analytics - Graphics", layout="wide")
st.title("⚽ Football Match Analytics")
st.markdown("---")

# ============================================================================
# Database Connection Check
# ============================================================================

if db_client is None or db_client.connection is None:
    st.error("❌ Database connection not available. Please check your Redshift configuration.")
    st.info("💡 Make sure your `.env` file is configured with valid Redshift credentials.")
    st.stop()

# ============================================================================
# Match Selection (Sidebar)
# ============================================================================

st.sidebar.header("Match Selection")

try:
    matches_df = get_match_list(db_client, limit=50)
    
    if matches_df is None or matches_df.empty:
        st.warning("⚠️ No matches found in the database. This could mean:")
        st.markdown("""
        - The `public.dim_matches` table doesn't exist or is empty
        - There's a database connection issue
        - There's a permissions issue
        
        Please check the Streamlit logs for detailed error messages.
        """)
        with st.expander("🔍 Debug Information"):
            st.code("Try running: dbt run --select dim_matches")
        st.stop()
    
    team_name_by_id = {}
    try:
        teams_df = get_team_names(db_client)
        if not teams_df.empty:
            team_name_by_id = {
                int(row['team_id']): row['team_name'] 
                for _, row in teams_df.iterrows()
            }
    except Exception as team_error:
        st.warning(f"⚠️ Could not load team names (using IDs instead): {team_error}")

    def resolve_name(team_id: int) -> str:
        return team_name_by_id.get(int(team_id), f"Team {team_id}")

    match_options = {}
    for _, row in matches_df.iterrows():
        home_name = resolve_name(row['home_team_id'])
        away_name = resolve_name(row['away_team_id'])
        label = f"{home_name} x {away_name} (Match {row['match_id']})"
        match_options[label] = row['match_id']
    
    selected_match_label = st.sidebar.selectbox(
        "Select a match:",
        options=list(match_options.keys())
    )
    
    selected_match_id = match_options[selected_match_label]
    st.sidebar.markdown("---")
    st.sidebar.info(f"📊 **Selected Match ID**: {selected_match_id}")

except Exception as e:
    display_error(f"❌ Error fetching match list: {e}", e)
    st.markdown("""
    **Possible causes:**
    - The `public.dim_matches` table doesn't exist (run `dbt run --select dim_matches`)
    - Database permissions issue
    - Connection problem
    
    **Check the terminal logs for detailed error information.**
    """)
    st.stop()

# ============================================================================
# Match Overview Section
# ============================================================================

try:
    match_data = get_match_overview_data(db_client, selected_match_id)
    
    if not match_data or 'metrics' not in match_data:
        st.warning(f"⚠️ No data found for match {selected_match_id}")
        st.stop()
    
    home_team_name = match_data.get('home_team_name', 'Home')
    away_team_name = match_data.get('away_team_name', 'Away')
    home_score = match_data.get('home_score', 0)
    away_score = match_data.get('away_score', 0)
    home_team_id = match_data.get('home_team_id')
    away_team_id = match_data.get('away_team_id')
    
    # Display match header with score
    col1, col2, col3 = st.columns([2, 1, 2])
    with col1:
        st.markdown(f"### {home_team_name}")
        st.markdown("**Home**")
    with col2:
        st.markdown(f"### {home_score} - {away_score}")
        st.markdown("**Score**")
    with col3:
        st.markdown(f"### {away_team_name}")
        st.markdown("**Away**")
    
    st.markdown("---")
    
    # Create and display the match overview chart
    fig = create_match_overview_chart(
        match_data['metrics'],
        home_team_name,
        away_team_name,
        home_score,
        away_score
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Optional: Show raw data table
    with st.expander("📋 View Raw Data"):
        metrics_dict = {
            key: {
                home_team_name: values['home'],
                away_team_name: values['away']
            }
            for key, values in match_data['metrics'].items()
        }
        metrics_df = pd.DataFrame(metrics_dict).T
        st.dataframe(metrics_df, use_container_width=True)
    
    st.markdown("---")
    st.markdown("*Data sourced from Redshift fct_events table*")
    
    # ========================================================================
    # Possession Chains Visualization Section
    # ========================================================================
    
    st.markdown("---")
    st.header("📊 Possession Chains Visualization")
    
    try:
        if home_team_id and away_team_id:
            team_options = create_team_options(
                home_team_id, away_team_id, home_team_name, away_team_name
            )
            
            selected_team_label = st.selectbox(
                "Select team to visualize possession chains:",
                options=list(team_options.keys()),
                key="team_selector"
            )
            
            selected_team_id = team_options[selected_team_label]
            selected_team_name = get_selected_team_name(
                selected_team_id, home_team_id, home_team_name, away_team_name
            )
            
            chain_summary = get_chain_summary(db_client, selected_match_id, selected_team_id)
            
            if not chain_summary.empty:
                chain_options = {}
                for _, row in chain_summary.iterrows():
                    chain_id = int(row['possession_chain'])
                    pass_count = int(row['pass_count'])
                    label = f"Chain {chain_id} ({pass_count} Pass{'es' if pass_count != 1 else ''})"
                    chain_options[label] = chain_id
                
                all_chains_label = (
                    f"All Chains ({len(chain_summary)} chain{'s' if len(chain_summary) != 1 else ''}, "
                    f"{chain_summary['pass_count'].sum()} total passes)"
                )
                chain_options = {all_chains_label: None, **chain_options}
                
                selected_chain_label = st.selectbox(
                    "Select chain to visualize:",
                    options=list(chain_options.keys()),
                    key="chain_selector"
                )
                
                selected_chain_id = chain_options[selected_chain_label]
                chains_df = get_possession_chains(
                    db_client, selected_match_id, selected_team_id, chain_id=selected_chain_id
                )
                
                if not chains_df.empty:
                    title = (
                        f"{selected_team_name} - All Possession Chains"
                        if selected_chain_id is None
                        else f"{selected_team_name} - Chain {selected_chain_id}"
                    )
                    
                    col_left, col_right = st.columns([1, 1.5])
                    
                    with col_left:
                        display_possession_chain_stats(chains_df, selected_chain_id)
                    
                    with col_right:
                        st.markdown("### ⚽ Pitch Visualization")
                        fig = create_possession_chains_pitch(chains_df, title)
                        st.pyplot(fig, use_container_width=True)
                else:
                    st.info(f"⚠️ No possession chain data found for {selected_team_name} in this match.")
            else:
                st.info(f"⚠️ No possession chain data found for {selected_team_name} in this match.")
        else:
            st.warning("⚠️ Team IDs not available for possession chain visualization.")
    
    except Exception as e:
        display_error(f"❌ Error loading possession chains: {e}", e)
    
    # ========================================================================
    # Zone Heatmap Visualization Section
    # ========================================================================
    
    st.markdown("---")
    st.header("🗺️ Zone Heatmap Visualization")
    
    try:
        if home_team_id and away_team_id:
            team_options_zones = create_team_options(
                home_team_id, away_team_id, home_team_name, away_team_name
            )
            
            selected_team_label_zones = st.selectbox(
                "Select team for zone heatmap:",
                options=list(team_options_zones.keys()),
                key="team_selector_zones"
            )
            
            selected_team_id_zones = team_options_zones[selected_team_label_zones]
            selected_team_name_zones = get_selected_team_name(
                selected_team_id_zones, home_team_id, home_team_name, away_team_name
            )
            
            event_type_options = {
                "All Events": None,
                "Passes": "pass",
                "Shots": "shot",
                "Tackles": "tackle",
                "Interceptions": "interception"
            }
            
            selected_event_type_label = st.selectbox(
                "Select event type:",
                options=list(event_type_options.keys()),
                key="event_type_selector"
            )
            
            selected_event_type = event_type_options[selected_event_type_label]
            zones_df = get_zone_event_counts(
                db_client, selected_match_id, 
                team_id=selected_team_id_zones, 
                event_type=selected_event_type
            )
            
            if not zones_df.empty:
                fig_zones = create_zone_heatmap(
                    zones_df, selected_team_name_zones, selected_event_type_label
                )
                st.pyplot(fig_zones, use_container_width=True)
                
                with st.expander("📊 Zone Distribution Statistics"):
                    st.write(f"**Total Zones with Events**: {len(zones_df)}")
                    st.write(f"**Total Events**: {zones_df['event_count'].sum()}")
                    st.write(f"**Average Events per Zone**: {zones_df['event_count'].mean():.1f}")
                    st.write(f"**Max Events in a Zone**: {zones_df['event_count'].max()}")
                    st.write(f"**Min Events in a Zone**: {zones_df['event_count'].min()}")
                    
                    event_totals = get_zone_event_totals(
                        db_client, selected_match_id, team_id=selected_team_id_zones
                    )
                    st.markdown("---")
                    st.markdown("**Event Type Totals:**")
                    st.write(f"- **Passes**: {event_totals['passes']}")
                    st.write(f"- **Shots**: {event_totals['shots']}")
                    st.write(f"- **Tackles**: {event_totals['tackles']}")
                    st.write(f"- **Interceptions**: {event_totals['interceptions']}")
                    
                    top_zones = zones_df.nlargest(5, 'event_count')
                    st.markdown("---")
                    st.markdown("**Top 5 Zones by Event Count:**")
                    for _, row in top_zones.iterrows():
                        st.write(
                            f"- Zone {row['start_zone_id']} "
                            f"(Bin {row['start_bin_x']},{row['start_bin_y']}): "
                            f"{int(row['event_count'])} events"
                        )
            else:
                st.info(
                    f"⚠️ No zone data found for {selected_team_name_zones} "
                    f"in this match with event type '{selected_event_type_label}'."
                )
        else:
            st.warning("⚠️ Team IDs not available for zone heatmap visualization.")
    
    except Exception as e:
        display_error(f"❌ Error loading zone heatmap: {e}", e)
    
    # ========================================================================
    # Player Performance Visualization Section
    # ========================================================================
    
    st.markdown("---")
    st.header("👤 Player Performance Visualization")
    
    try:
        if home_team_id and away_team_id:
            team_options_player = create_team_options(
                home_team_id, away_team_id, home_team_name, away_team_name
            )
            
            selected_team_label_player = st.selectbox(
                "Select team:",
                options=list(team_options_player.keys()),
                key="team_selector_player"
            )
            
            selected_team_id_player = team_options_player[selected_team_label_player]
            selected_team_name_player = get_selected_team_name(
                selected_team_id_player, home_team_id, home_team_name, away_team_name
            )
            
            players_df = get_match_players(
                db_client, selected_match_id, selected_team_id_player
            )
            
            if not players_df.empty:
                player_options = {
                    row['player_name']: int(row['player_id'])
                    for _, row in players_df.iterrows()
                }
                
                selected_player_name = st.selectbox(
                    "Select player:",
                    options=list(player_options.keys()),
                    key="player_selector"
                )
                
                selected_player_id = player_options[selected_player_name]
                
                view_type = st.radio(
                    "View:",
                    options=["Passes", "Shots"],
                    key="player_view_type",
                    horizontal=True
                )
                
                if view_type == "Passes":
                    passes_df = get_player_passes(
                        db_client, selected_match_id, 
                        selected_team_id_player, selected_player_id
                    )
                    
                    if not passes_df.empty:
                        col_left, col_right = st.columns([1, 1.5])
                        
                        with col_left:
                            display_pass_stats(passes_df)
                        
                        with col_right:
                            st.markdown("### ⚽ Pass Visualization")
                            fig_passes = create_player_passes_pitch(
                                passes_df, selected_player_name
                            )
                            st.pyplot(fig_passes, use_container_width=True)
                    else:
                        st.info(f"⚠️ No pass data found for {selected_player_name} in this match.")
                
                else:  # Shots
                    shots_df = get_player_shots(
                        db_client, selected_match_id, 
                        selected_team_id_player, selected_player_id
                    )
                    
                    if not shots_df.empty:
                        col_left, col_right = st.columns([1, 1.5])
                        
                        with col_left:
                            display_shot_stats(shots_df)
                        
                        with col_right:
                            st.markdown("### ⚽ Shot Visualization")
                            fig_shots = create_player_shots_pitch(
                                shots_df, selected_player_name
                            )
                            st.pyplot(fig_shots, use_container_width=True)
                    else:
                        st.info(f"⚠️ No shot data found for {selected_player_name} in this match.")
            else:
                st.info(f"⚠️ No players found for {selected_team_name_player} in this match.")
        else:
            st.warning("⚠️ Team IDs not available for player visualization.")
    
    except Exception as e:
        display_error(f"❌ Error loading player visualization: {e}", e)

except Exception as e:
    display_error(f"❌ Error loading match data: {e}", e)
