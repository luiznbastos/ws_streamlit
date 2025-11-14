# WS Analytics Streamlit Dashboard

Football match event analysis dashboard with interactive visualizations powered by AWS Redshift and Plotly.

## Features

- **Team Comparison View**: Compare team-level match statistics including shots, passes, defensive actions, and more
- **Player Statistics View**: Analyze individual player performance metrics
- **Interactive Filters**: Select matches and filter by team
- **16 Event Metrics**: Comprehensive coverage of all match events
  - Offensive: Shots, Passes, Dribbles, Touches
  - Defensive: Tackles, Interceptions, Clearances, Blocks
  - Discipline: Fouls, Offsides, Errors, Loss of Possession
  - Goalkeeper: Saves, Claims, Punches
  - Other: Aerial Duels

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│  Streamlit  │ ───> │   Redshift   │ ───> │ dbt Models  │
│   (EC2)     │ IAM  │   Cluster    │      │  (Tables)   │
└─────────────┘      └──────────────┘      └─────────────┘
```

## Project Structure

```
ws_streamlit/
├── src/
│   ├── app.py                      # Main dashboard home page
│   ├── database.py                 # Redshift connection with IAM auth
│   ├── settings.py                 # Configuration management
│   ├── pages/
│   │   └── graphics.py             # Graphics/visualizations page
│   └── utils/
│       └── redshift_queries.py     # Query helper functions
├── Dockerfile                      # Container configuration
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## Setup

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```bash
# Environment
ENVIRONMENT=development

# AWS Configuration
REGION=us-east-1

# Redshift Configuration
REDSHIFT_HOST=your-redshift-cluster.region.redshift.amazonaws.com
REDSHIFT_PORT=5439
REDSHIFT_DATABASE=your_database_name
REDSHIFT_USER=your_redshift_user
REDSHIFT_CLUSTER_ID=your-cluster-id

# Authentication Method (use IAM for EC2 deployment)
USE_IAM_AUTH=true

# Only required if USE_IAM_AUTH=false
REDSHIFT_PASSWORD=your_password_here
```

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   - Copy `.env.example` to `.env`
   - Update with your Redshift credentials

3. **Run the application:**
   ```bash
   streamlit run src/app.py
   ```

4. **Access the dashboard:**
   - Open browser at `http://localhost:8501`

### Docker Deployment

1. **Build the image:**
   ```bash
   docker build -t ws-streamlit .
   ```

2. **Run the container:**
   ```bash
   docker run -p 8501:8501 \
     -e REDSHIFT_HOST=your-host \
     -e REDSHIFT_DATABASE=your-db \
     -e REDSHIFT_USER=your-user \
     -e REDSHIFT_CLUSTER_ID=your-cluster \
     -e USE_IAM_AUTH=true \
     ws-streamlit
   ```

## AWS EC2 Deployment

### Prerequisites

1. **EC2 Instance Requirements:**
   - Amazon Linux 2 or Ubuntu
   - Minimum: t3.medium (2 vCPU, 4 GB RAM)
   - Security group allowing inbound traffic on port 8501

2. **IAM Role Configuration:**
   - Attach IAM role to EC2 instance with Redshift access
   - Required permissions:
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [
         {
           "Effect": "Allow",
           "Action": [
             "redshift:GetClusterCredentials",
             "redshift:DescribeClusters"
           ],
           "Resource": "*"
         }
       ]
     }
     ```

3. **Redshift Cluster Configuration:**
   - Ensure Redshift security group allows connections from EC2
   - Verify dbt models are deployed and tables exist

### Deployment Steps

1. **SSH into EC2 instance:**
   ```bash
   ssh -i your-key.pem ec2-user@your-ec2-ip
   ```

2. **Install Docker (if not installed):**
   ```bash
   sudo yum update -y
   sudo yum install docker -y
   sudo service docker start
   sudo usermod -a -G docker ec2-user
   ```

3. **Clone repository and build:**
   ```bash
   git clone your-repo-url
   cd ws_streamlit
   docker build -t ws-streamlit .
   ```

4. **Run the application:**
   ```bash
   docker run -d \
     --name ws-streamlit \
     --restart unless-stopped \
     -p 8501:8501 \
     -e REDSHIFT_HOST=your-redshift-host \
     -e REDSHIFT_DATABASE=your-database \
     -e REDSHIFT_USER=your-user \
     -e REDSHIFT_CLUSTER_ID=your-cluster-id \
     -e USE_IAM_AUTH=true \
     -e REGION=us-east-1 \
     ws-streamlit
   ```

5. **Access the dashboard:**
   - Navigate to `http://your-ec2-ip:8501`

### Production Considerations

- **Use Application Load Balancer** for HTTPS and custom domain
- **Enable CloudWatch logging** for monitoring
- **Set up auto-scaling** for high availability
- **Use secrets manager** for sensitive credentials
- **Configure VPC** for secure Redshift access

## Data Models

The dashboard queries the following dbt models from Redshift:

### gold_team_match_summary
Team-level aggregated match statistics:
- `shots_total`, `passes_attempted`, `tackles`, `interceptions`
- `clearances`, `blocks`, `offsides`, `fouls_committed`
- `aerials_attempted`, `touches`, `turnovers`, `errors`
- `saves`, `claims`, `punches`

### gold_player_match_summary
Player-level match statistics:
- Similar metrics as team summary
- Grouped by player_id within each team

### fct_events
Detailed event-level data with boolean flags:
- `is_shot`, `is_pass`, `is_tackle`, `is_interception`, etc.
- Used for time-series analysis and event filtering

## Troubleshooting

### Connection Issues

**Problem**: "Unable to connect to Redshift database"

**Solutions:**
1. Verify environment variables are set correctly
2. Check EC2 instance has IAM role attached
3. Confirm Redshift security group allows EC2 connection
4. Test network connectivity: `telnet redshift-host 5439`

### IAM Authentication Fails

**Problem**: IAM authentication errors

**Solutions:**
1. Verify IAM role has `redshift:GetClusterCredentials` permission
2. Check REDSHIFT_CLUSTER_ID matches actual cluster identifier
3. Ensure REDSHIFT_USER exists in Redshift cluster
4. Try setting `USE_IAM_AUTH=false` and use password temporarily

### No Data Displayed

**Problem**: Charts are empty or show "No data found"

**Solutions:**
1. Verify dbt models are deployed and populated
2. Check table names match: `gold_team_match_summary`, `gold_player_match_summary`
3. Query Redshift directly to confirm data exists
4. Review application logs for SQL errors

## Development

### Adding New Visualizations

1. Add query function to `src/utils/redshift_queries.py`
2. Create visualization in `src/pages/graphics.py`
3. Use Plotly Express or Graph Objects for charts
4. Add filters and interactivity with Streamlit widgets

### Testing Queries

Test queries directly in Redshift before adding to the app:

```sql
SELECT * FROM gold_team_match_summary LIMIT 10;
SELECT * FROM gold_player_match_summary WHERE match_id = 12345;
```

## Dependencies

- `streamlit`: Web framework
- `plotly`: Interactive visualizations
- `pandas`: Data manipulation
- `redshift-connector`: Redshift database driver
- `boto3`: AWS SDK for IAM authentication
- `pydantic`: Settings validation

## License

Part of the WS (WhoScored) Analytics project.

