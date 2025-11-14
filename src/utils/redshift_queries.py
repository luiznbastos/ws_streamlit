"""
Redshift query utilities for fetching match, team, player, and event data.

This module provides functions to query various data from Redshift tables
including matches, teams, players, events, possession chains, and zones.
"""

import pandas as pd
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

def _handle_query_error(error: Exception, table_name: str = None) -> pd.DataFrame:
    """Handle query errors and return empty DataFrame."""
    error_msg = str(error)
    if table_name and ('does not exist' in error_msg.lower() or '42p01' in error_msg.lower()):
        logger.error(f"Table {table_name} does not exist. Run: dbt run --select {table_name}")
    else:
        logger.error(f"Query failed: {error}")
    return pd.DataFrame()

def _build_event_type_filter(event_type: Optional[str]) -> str:
    """Build SQL filter for event type based on main_type."""
    if event_type == 'pass':
        return "AND LOWER(main_type) = 'pass'"
    elif event_type == 'shot':
        return "AND (main_type ILIKE '%shot%' OR main_type ILIKE 'goal')"
    elif event_type == 'tackle':
        return "AND (main_type ILIKE '%tackle%' OR main_type ILIKE '%challenge%')"
    elif event_type == 'interception':
        return "AND main_type ILIKE '%interception%'"
    else:
        return ""

def get_match_list(db_client, limit: int = 50) -> pd.DataFrame:
    """
    Get a list of available matches from dim_matches.
    
    Args:
        db_client: Database client instance
        limit: Maximum number of matches to return
    
    Returns:
        DataFrame with columns: match_id, home_team_id, away_team_id
    """
    if db_client is None:
        logger.error("Database client is None")
        return pd.DataFrame()
    
    query = f"""
    SELECT 
        match_id,
        home_team_id,
        away_team_id
    FROM public.dim_matches
    ORDER BY match_id DESC
    LIMIT {limit}
    """
    
    try:
        results = db_client.query(query)
        if results is None:
            logger.error("Query returned None")
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        if df.empty:
            logger.warning("Query returned empty results. Table might be empty or not exist.")
        return df
    except Exception as e:
        logger.error(f"Failed to fetch match list: {e}")
        return pd.DataFrame()

def get_team_names(db_client) -> pd.DataFrame:
    """
    Get team names from dim_teams.
    
    Args:
        db_client: Database client instance
    
    Returns:
        DataFrame with columns: team_id, team_name
    """
    query = """
    SELECT 
        team_id,
        team_name
    FROM public.dim_teams
    ORDER BY team_name
    """
    
    try:
        results = db_client.query(query)
        return pd.DataFrame(results)
    except Exception as e:
        logger.error(f"Failed to fetch team names: {e}")
        return pd.DataFrame()

def get_match_summary(db_client, match_id: int) -> dict:
    """
    Get a summary of a match including team names and basic info.
    
    Args:
        db_client: Database client instance
        match_id: Match ID to query
    
    Returns:
        Dictionary with match information
    """
    query = f"""
    SELECT 
        dm.match_id,
        dm.home_team_id,
        dm.away_team_id,
        ht.team_name as home_team_name,
        at.team_name as away_team_name
    FROM public.dim_matches dm
    LEFT JOIN public.dim_teams ht ON dm.home_team_id = ht.team_id
    LEFT JOIN public.dim_teams at ON dm.away_team_id = at.team_id
    WHERE dm.match_id = {match_id}
    """
    
    try:
        results = db_client.query(query)
        return results[0] if results else {}
    except Exception as e:
        logger.error(f"Failed to fetch match summary: {e}")
        return {}

def get_match_overview_data(db_client, match_id: int) -> dict:
    """
    Get match overview data for the horizontal bar chart visualization.
    Queries fct_events and aggregates event flags per team.
    
    Args:
        db_client: Database client instance
        match_id: Match ID to query
    
    Returns:
        Dictionary with team names, IDs, scores, and metrics
    """
    query = f"""
    WITH team_metrics AS (
        SELECT 
            fe.match_id,
            fe.team_id,
            COUNT(CASE WHEN fe.is_touch = True THEN 1 END) as touches,
            COUNT(CASE WHEN fe.is_shot THEN 1 END) as shots,
            COUNT(CASE WHEN fe.is_pass THEN 1 END) as passes,
            COUNT(CASE WHEN fe.is_dribble THEN 1 END) as dribbles,
            COUNT(CASE WHEN fe.is_tackle THEN 1 END) as tackles_attempted,
            COUNT(CASE WHEN fe.is_interception THEN 1 END) as interceptions,
            COUNT(CASE WHEN fe.is_clearance THEN 1 END) as clearances,
            COUNT(CASE WHEN fe.is_block THEN 1 END) as blocks,
            COUNT(CASE WHEN fe.is_offside THEN 1 END) as offsides,
            COUNT(CASE WHEN fe.is_foul THEN 1 END) as fouls,
            COUNT(CASE WHEN fe.is_aerial THEN 1 END) as aerial_duels,
            COUNT(CASE WHEN fe.is_loss_possession THEN 1 END) as loss_of_possession,
            COUNT(CASE WHEN fe.is_error THEN 1 END) as errors,
            COUNT(CASE WHEN fe.is_save THEN 1 END) as saves,
            COUNT(CASE WHEN fe.is_claim THEN 1 END) as claims,
            COUNT(CASE WHEN fe.is_punch THEN 1 END) as punches
        FROM public.fct_events fe
        WHERE fe.match_id = {match_id}
        GROUP BY fe.match_id, fe.team_id
    ),
    match_scores AS (
        SELECT 
            fe.match_id,
            COUNT(CASE WHEN fe.main_type ILIKE 'goal' AND fe.team_id = dm.home_team_id THEN 1 END) as home_score,
            COUNT(CASE WHEN fe.main_type ILIKE 'goal' AND fe.team_id = dm.away_team_id THEN 1 END) as away_score
        FROM public.fct_events fe
        INNER JOIN public.dim_matches dm ON fe.match_id = dm.match_id
        WHERE fe.match_id = {match_id}
        AND fe.main_type ILIKE 'goal'
        GROUP BY fe.match_id
    ),
    match_info AS (
        SELECT 
            dm.match_id,
            dm.home_team_id,
            dm.away_team_id,
            ht.team_name as home_team_name,
            at.team_name as away_team_name,
            COALESCE(ms.home_score, 0) as home_score,
            COALESCE(ms.away_score, 0) as away_score
        FROM public.dim_matches dm
        LEFT JOIN public.dim_teams ht ON dm.home_team_id = ht.team_id
        LEFT JOIN public.dim_teams at ON dm.away_team_id = at.team_id
        LEFT JOIN match_scores ms ON dm.match_id = ms.match_id
        WHERE dm.match_id = {match_id}
    )
    SELECT 
        mi.home_team_name,
        mi.away_team_name,
        mi.home_team_id,
        mi.away_team_id,
        mi.home_score,
        mi.away_score,
        ht.touches as home_touches,
        ht.shots as home_shots,
        ht.passes as home_passes,
        ht.dribbles as home_dribbles,
        ht.tackles_attempted as home_tackles_attempted,
        ht.interceptions as home_interceptions,
        ht.clearances as home_clearances,
        ht.blocks as home_blocks,
        ht.offsides as home_offsides,
        ht.fouls as home_fouls,
        ht.aerial_duels as home_aerial_duels,
        ht.loss_of_possession as home_loss_of_possession,
        ht.errors as home_errors,
        ht.saves as home_saves,
        ht.claims as home_claims,
        ht.punches as home_punches,
        at.touches as away_touches,
        at.shots as away_shots,
        at.passes as away_passes,
        at.dribbles as away_dribbles,
        at.tackles_attempted as away_tackles_attempted,
        at.interceptions as away_interceptions,
        at.clearances as away_clearances,
        at.blocks as away_blocks,
        at.offsides as away_offsides,
        at.fouls as away_fouls,
        at.aerial_duels as away_aerial_duels,
        at.loss_of_possession as away_loss_of_possession,
        at.errors as away_errors,
        at.saves as away_saves,
        at.claims as away_claims,
        at.punches as away_punches
    FROM match_info mi
    LEFT JOIN team_metrics ht ON mi.home_team_id = ht.team_id
    LEFT JOIN team_metrics at ON mi.away_team_id = at.team_id
    """
    
    try:
        results = db_client.query(query)
        if not results or len(results) == 0:
            logger.error(f"No data found for match_id {match_id}")
            return {}
        
        row = results[0]
        
        return {
            'home_team_name': row.get('home_team_name', 'Home'),
            'away_team_name': row.get('away_team_name', 'Away'),
            'home_team_id': row.get('home_team_id'),
            'away_team_id': row.get('away_team_id'),
            'home_score': row.get('home_score', 0) or 0,
            'away_score': row.get('away_score', 0) or 0,
            'metrics': {
                'shots': {'home': row.get('home_shots', 0) or 0, 'away': row.get('away_shots', 0) or 0},
                'passes': {'home': row.get('home_passes', 0) or 0, 'away': row.get('away_passes', 0) or 0},
                'dribbles': {'home': row.get('home_dribbles', 0) or 0, 'away': row.get('away_dribbles', 0) or 0},
                'tackles_attempted': {'home': row.get('home_tackles_attempted', 0) or 0, 'away': row.get('away_tackles_attempted', 0) or 0},
                'interceptions': {'home': row.get('home_interceptions', 0) or 0, 'away': row.get('away_interceptions', 0) or 0},
                'clearances': {'home': row.get('home_clearances', 0) or 0, 'away': row.get('away_clearances', 0) or 0},
                'blocks': {'home': row.get('home_blocks', 0) or 0, 'away': row.get('away_blocks', 0) or 0},
                'offsides': {'home': row.get('home_offsides', 0) or 0, 'away': row.get('away_offsides', 0) or 0},
                'fouls': {'home': row.get('home_fouls', 0) or 0, 'away': row.get('away_fouls', 0) or 0},
                'aerial_duels': {'home': row.get('home_aerial_duels', 0) or 0, 'away': row.get('away_aerial_duels', 0) or 0},
                'touches': {'home': row.get('home_touches', 0) or 0, 'away': row.get('away_touches', 0) or 0},
                'loss_of_possession': {'home': row.get('home_loss_of_possession', 0) or 0, 'away': row.get('away_loss_of_possession', 0) or 0},
                'errors': {'home': row.get('home_errors', 0) or 0, 'away': row.get('away_errors', 0) or 0},
                'saves': {'home': row.get('home_saves', 0) or 0, 'away': row.get('away_saves', 0) or 0},
                'claims': {'home': row.get('home_claims', 0) or 0, 'away': row.get('away_claims', 0) or 0},
                'punches': {'home': row.get('home_punches', 0) or 0, 'away': row.get('away_punches', 0) or 0}
            }
        }
    except Exception as e:
        logger.error(f"Error executing query for match_id {match_id}: {e}")
        raise

def get_chain_summary(db_client, match_id: int, team_id: int) -> pd.DataFrame:
    """
    Get a summary of all possession chains for a match and team.
    
    Args:
        db_client: Database client instance
        match_id: Match ID to filter by
        team_id: Team ID (possessing_team_id) to filter by
    
    Returns:
        DataFrame with columns: possession_chain, pass_count
    """
    query = f"""
    SELECT 
        possession_chain,
        COUNT(*) as pass_count
    FROM public.fct_events
    WHERE match_id = {match_id}
    AND possessing_team_id = {team_id}
    AND is_pass = True
    AND LOWER(outcome_type) = 'successful'
    AND end_x IS NOT NULL
    AND end_y IS NOT NULL
    GROUP BY possession_chain
    ORDER BY possession_chain
    """
    
    try:
        results = db_client.query(query)
        return pd.DataFrame(results)
    except Exception as e:
        logger.error(f"Failed to fetch chain summary: {e}")
        return pd.DataFrame()

def get_possession_chains(db_client, match_id: int, team_id: int, 
                         chain_id: Optional[int] = None) -> pd.DataFrame:
    """
    Query possession chains for a specific match and team from fct_events.
    
    Args:
        db_client: Database client instance
        match_id: Match ID to filter by
        team_id: Team ID (possessing_team_id) to filter by
        chain_id: Optional chain ID to filter by. If None, returns all chains.
    
    Returns:
        DataFrame with pass events and coordinates
    """
    chain_filter = f"AND possession_chain = {chain_id}" if chain_id is not None else ""
    
    query = f"""
    SELECT 
        possession_chain,
        x,
        y,
        end_x,
        end_y,
        main_type as type,
        outcome_type,
        minute,
        second,
        possessing_team_id
    FROM public.fct_events
    WHERE match_id = {match_id}
    AND possessing_team_id = {team_id}
    AND is_pass = True
    AND LOWER(outcome_type) = 'successful'
    AND end_x IS NOT NULL
    AND end_y IS NOT NULL
    {chain_filter}
    ORDER BY possession_chain, minute, second
    """
    
    try:
        results = db_client.query(query)
        df = pd.DataFrame(results)
        if df.empty:
            logger.warning(f"No possession chain data found for match_id={match_id}, team_id={team_id}")
        return df
    except Exception as e:
        _handle_query_error(e, 'public.fct_events')
        raise

def get_zone_event_counts(db_client, match_id: int, 
                         team_id: Optional[int] = None, 
                         event_type: Optional[str] = None) -> pd.DataFrame:
    """
    Query event counts per zone from fct_event_zones.
    
    Args:
        db_client: Database client instance
        match_id: Match ID to filter by
        team_id: Optional team ID to filter by
        event_type: Optional event type filter ('pass', 'shot', 'tackle', 'interception')
    
    Returns:
        DataFrame with columns: start_zone_id, start_bin_x, start_bin_y, event_count
    """
    team_filter = f"AND team_id = {team_id}" if team_id is not None else ""
    event_filter = _build_event_type_filter(event_type)
    
    query = f"""
    SELECT 
        start_zone_id,
        start_bin_x,
        start_bin_y,
        COUNT(*) as event_count
    FROM public.fct_event_zones
    WHERE match_id = {match_id}
    {team_filter}
    {event_filter}
    GROUP BY start_zone_id, start_bin_x, start_bin_y
    ORDER BY start_bin_x, start_bin_y
    """
    
    try:
        results = db_client.query(query)
        return pd.DataFrame(results)
    except Exception as e:
        return _handle_query_error(e, 'public.fct_event_zones')

def get_zone_event_totals(db_client, match_id: int, 
                          team_id: Optional[int] = None) -> dict:
    """
    Get total counts for passes, shots, tackles, and interceptions.
    
    Args:
        db_client: Database client instance
        match_id: Match ID to filter by
        team_id: Optional team ID to filter by
    
    Returns:
        Dictionary with keys: passes, shots, tackles, interceptions
    """
    team_filter = f"AND team_id = {team_id}" if team_id is not None else ""
    
    query = f"""
    SELECT 
        COUNT(CASE WHEN is_pass THEN 1 END) as passes,
        COUNT(CASE WHEN is_shot THEN 1 END) as shots,
        COUNT(CASE WHEN is_tackle THEN 1 END) as tackles,
        COUNT(CASE WHEN is_interception THEN 1 END) as interceptions
    FROM public.fct_events
    WHERE match_id = {match_id}
    {team_filter}
    """
    
    try:
        results = db_client.query(query)
        if results and len(results) > 0:
            return {
                'passes': results[0].get('passes', 0) or 0,
                'shots': results[0].get('shots', 0) or 0,
                'tackles': results[0].get('tackles', 0) or 0,
                'interceptions': results[0].get('interceptions', 0) or 0
            }
        return {'passes': 0, 'shots': 0, 'tackles': 0, 'interceptions': 0}
    except Exception as e:
        logger.error(f"Failed to fetch zone event totals: {e}")
        return {'passes': 0, 'shots': 0, 'tackles': 0, 'interceptions': 0}

def get_match_players(db_client, match_id: int, team_id: int) -> pd.DataFrame:
    """
    Get list of players who have events in a specific match and team.
    
    Args:
        db_client: Database client instance
        match_id: Match ID to filter by
        team_id: Team ID to filter by
    
    Returns:
        DataFrame with columns: player_id, player_name
    """
    query = f"""
    SELECT DISTINCT
        player_id,
        player_name
    FROM public.fct_events
    WHERE match_id = {match_id}
    AND team_id = {team_id}
    AND player_id IS NOT NULL
    AND player_name IS NOT NULL
    ORDER BY player_name
    """
    
    try:
        results = db_client.query(query)
        return pd.DataFrame(results)
    except Exception as e:
        _handle_query_error(e, 'public.fct_events')
        raise

def get_player_passes(db_client, match_id: int, team_id: int, 
                     player_id: int) -> pd.DataFrame:
    """
    Get all passes for a specific player in a match.
    
    Args:
        db_client: Database client instance
        match_id: Match ID to filter by
        team_id: Team ID to filter by
        player_id: Player ID to filter by
    
    Returns:
        DataFrame with columns: x, y, end_x, end_y, outcome_type, minute, second
    """
    query = f"""
    SELECT 
        x,
        y,
        end_x,
        end_y,
        outcome_type,
        minute,
        second
    FROM public.fct_events
    WHERE match_id = {match_id}
    AND team_id = {team_id}
    AND player_id = {player_id}
    AND LOWER(main_type) = 'pass'
    AND x IS NOT NULL
    AND y IS NOT NULL
    ORDER BY minute, second
    """
    
    try:
        results = db_client.query(query)
        return pd.DataFrame(results)
    except Exception as e:
        _handle_query_error(e, 'public.fct_events')
        raise

def get_player_shots(db_client, match_id: int, team_id: int, 
                    player_id: int) -> pd.DataFrame:
    """
    Get all shots for a specific player in a match.
    
    Args:
        db_client: Database client instance
        match_id: Match ID to filter by
        team_id: Team ID to filter by
        player_id: Player ID to filter by
    
    Returns:
        DataFrame with columns: x, y, main_type, outcome_type, minute, second
    """
    query = f"""
    SELECT 
        x,
        y,
        main_type,
        outcome_type,
        minute,
        second
    FROM public.fct_events
    WHERE match_id = {match_id}
    AND team_id = {team_id}
    AND player_id = {player_id}
    AND (main_type ILIKE '%shot%' OR main_type ILIKE 'goal')
    AND x IS NOT NULL
    AND y IS NOT NULL
    ORDER BY minute, second
    """
    
    try:
        results = db_client.query(query)
        return pd.DataFrame(results)
    except Exception as e:
        _handle_query_error(e, 'public.fct_events')
        raise

# ============================================================================
# Legacy Functions (kept for backward compatibility)
# ============================================================================

def get_team_match_metrics(db_client, match_id: Optional[int] = None) -> pd.DataFrame:
    """
    Query team-level match metrics from gold_team_match_summary.
    Legacy function - kept for backward compatibility.
    """
    query = """
    SELECT 
        match_id,
        team_id,
        shots_total as shots,
        passes_attempted as passes,
        tackles,
        interceptions,
        clearances,
        blocks,
        offsides,
        fouls_committed as fouls,
        aerials_attempted as aerial_duels,
        touches,
        turnovers as loss_of_possession,
        errors,
        saves,
        claims,
        punches
    FROM gold_team_match_summary
    """
    
    if match_id:
        query += f" WHERE match_id = {match_id}"
    
    query += " ORDER BY match_id DESC, team_id"
    
    try:
        results = db_client.query(query)
        return pd.DataFrame(results)
    except Exception as e:
        logger.error(f"Failed to fetch team match metrics: {e}")
        return pd.DataFrame()

def get_player_match_metrics(db_client, match_id: Optional[int] = None, 
                             team_id: Optional[int] = None) -> pd.DataFrame:
    """
    Query player-level match metrics from gold_player_match_summary.
    Legacy function - kept for backward compatibility.
    """
    query = """
    SELECT 
        match_id,
        team_id,
        player_id,
        shots_total as shots,
        passes_attempted as passes,
        dribbles_attempted as dribbles,
        tackles,
        interceptions,
        clearances,
        blocks,
        fouls_committed as fouls,
        aerials_attempted as aerial_duels,
        touches,
        turnovers as loss_of_possession,
        errors
    FROM gold_player_match_summary
    WHERE 1=1
    """
    
    if match_id:
        query += f" AND match_id = {match_id}"
    if team_id:
        query += f" AND team_id = {team_id}"
    
    query += " ORDER BY match_id DESC, team_id, touches DESC"
    
    try:
        results = db_client.query(query)
        return pd.DataFrame(results)
    except Exception as e:
        logger.error(f"Failed to fetch player match metrics: {e}")
        return pd.DataFrame()

def get_event_time_series(db_client, match_id: int, 
                          event_types: List[str]) -> pd.DataFrame:
    """
    Query events over time for a specific match.
    Legacy function - kept for backward compatibility.
    
    Args:
        db_client: Database client instance
        match_id: Match ID to query
        event_types: List of event flags like ['is_shot', 'is_pass', 'is_tackle']
    """
    event_conditions = " OR ".join([f"{event_type} = true" for event_type in event_types])
    
    query = f"""
    SELECT 
        match_id,
        team_id,
        minute,
        COUNT(*) as event_count
    FROM fct_events
    WHERE match_id = {match_id}
    AND ({event_conditions})
    GROUP BY match_id, team_id, minute
    ORDER BY minute
    """
    
    try:
        results = db_client.query(query)
        return pd.DataFrame(results)
    except Exception as e:
        logger.error(f"Failed to fetch event time series: {e}")
        return pd.DataFrame()
