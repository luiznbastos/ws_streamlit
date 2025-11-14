"""
Streamlit Dashboard
Data visualization for analytics pipeline
"""
import streamlit as st

st.set_page_config(
    page_title="WS Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("⚽ WS Analytics Dashboard")
st.markdown("### Football Match Event Analysis")

st.markdown("---")

st.markdown("""
Welcome to the WS Analytics Dashboard! This application provides comprehensive football match analytics 
powered by data from AWS Redshift.

### Available Pages:

#### 📊 Graphics
Interactive visualizations displaying match event metrics including:
- Shots, Passes, Dribbles
- Tackles, Interceptions, Clearances, Blocks
- Offsides, Fouls, Aerial Duels
- Touches, Loss of Possession, Errors
- Saves, Claims, Punches (Goalkeeper actions)

View team comparisons and player statistics with dynamic filtering.

### Getting Started:
1. Navigate to the **Graphics** page using the sidebar
2. Select a match from the dropdown
3. Choose between Team Comparison or Player Statistics view
4. Explore the interactive charts and data tables

### Data Source:
- **Database**: AWS Redshift
- **dbt Models**: `gold_team_match_summary`, `gold_player_match_summary`, `fct_events`
- **Authentication**: IAM-based authentication from EC2 instance role
""")

st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="📊 Available Pages", value="Graphics")

with col2:
    st.metric(label="🎯 Event Types", value="16")

with col3:
    st.metric(label="📈 Data Source", value="Redshift")

st.markdown("---")

st.info("👈 Use the sidebar navigation to access the Graphics page and start exploring match analytics!")

st.markdown("""
### Technical Stack:
- **Frontend**: Streamlit + Plotly
- **Database**: AWS Redshift
- **Data Pipeline**: dbt (data build tool)
- **Deployment**: AWS EC2
- **Authentication**: IAM Role-based
""")
