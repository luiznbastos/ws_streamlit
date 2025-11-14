"""
Redshift database client for IAM-authenticated connections.

This module provides a RedshiftClient class for connecting to Redshift
using IAM authentication, with support for both serverless and cluster-based
Redshift instances.
"""

import logging
import redshift_connector
import boto3
from typing import List, Dict, Any, Optional

from src.settings import settings

logger = logging.getLogger(__name__)


_db_client = None

class RedshiftClient:
    """Client for connecting to and querying Redshift databases."""
    
    def __init__(self):
        """Initialize the Redshift client and establish connection."""
        self.connection = None
        self._connect()
    
    def _connect(self):
        """
        Establish connection to Redshift using IAM or password authentication.
        
        Tries multiple connection methods in order:
        1. Redshift Serverless (if cluster_id is provided)
        2. Regular Redshift cluster with IAM
        3. Direct IAM connection
        4. Password authentication (if IAM is disabled)
        """
        try:
            host = settings.redshift_host
            port = settings.redshift_port
            database = settings.redshift_database
            user = settings.redshift_user
            cluster_id = settings.redshift_cluster_id
            region = settings.region
            
            if not all([host, database, user]):
                logger.warning("Redshift credentials not fully configured")
                return
            
            if settings.use_iam_auth:
                self._connect_with_iam(host, port, database, user, cluster_id, region)
            else:
                self._connect_with_password(host, port, database, user)
                
        except Exception as e:
            logger.error(f"Failed to connect to Redshift: {e}")
            self.connection = None
    
    def _connect_with_iam(self, host: str, port: int, database: str, 
                         user: str, cluster_id: str, region: str):
        """Connect to Redshift using IAM authentication."""
        logger.info("Attempting IAM authentication to Redshift")
        
        try:
            if cluster_id:
                if self._try_serverless_connection(host, port, database, cluster_id, region):
                    return
            
            self._try_cluster_connection(host, port, database, user, cluster_id, region)
            
        except Exception as iam_error:
            logger.error(f"IAM authentication failed: {iam_error}")
            logger.info("Falling back to direct connection")
            self._try_direct_iam_connection(host, port, database, user, region)
    
    def _try_serverless_connection(self, host: str, port: int, database: str,
                                   cluster_id: str, region: str) -> bool:
        """Try connecting to Redshift Serverless."""
        try:
            serverless_client = boto3.client('redshift-serverless', region_name=region)
            response = serverless_client.get_credentials(
                workgroupName=cluster_id,
                dbName=database
            )
            
            self.connection = redshift_connector.connect(
                host=host,
                port=port,
                database=database,
                user=response['dbUser'],
                password=response['dbPassword'],
                ssl=True,
                sslmode='verify-ca'
            )
            logger.info("Redshift Serverless connection established with IAM authentication")
            return True
        except Exception as serverless_error:
            logger.debug(f"Redshift Serverless failed: {serverless_error}, trying regular Redshift")
            return False
    
    def _try_cluster_connection(self, host: str, port: int, database: str,
                               user: str, cluster_id: str, region: str):
        """Try connecting to regular Redshift cluster."""
        client = boto3.client('redshift', region_name=region)
        
        response = client.get_cluster_credentials(
            DbUser=user,
            DbName=database,
            ClusterIdentifier=cluster_id,
            AutoCreate=False,
            DurationSeconds=3600
        )
        
        self.connection = redshift_connector.connect(
            host=host,
            port=port,
            database=database,
            user=response['DbUser'],
            password=response['DbPassword'],
            ssl=True,
            sslmode='verify-ca'
        )
        logger.info("Redshift connection established with IAM authentication")
    
    def _try_direct_iam_connection(self, host: str, port: int, database: str,
                                   user: str, region: str):
        """Try direct IAM connection."""
        self.connection = redshift_connector.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            iam=True,
            ssl=True,
            region=region
        )
        logger.info("Redshift connection established with direct IAM")
    
    def _connect_with_password(self, host: str, port: int, database: str, user: str):
        """Connect to Redshift using password authentication."""
        logger.info("Using standard authentication")
        password = settings.redshift_password
        if not password:
            logger.error("Password required for non-IAM authentication")
            return
        
        self.connection = redshift_connector.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        logger.info("Redshift connection established with password authentication")
    
    def _reset_transaction(self):
        """
        Reset the transaction state by rolling back any aborted transaction.
        
        If rollback fails, attempts to reconnect to ensure a clean state.
        """
        if not self.connection:
            return
        
        try:
            self.connection.rollback()
            logger.debug("Transaction rolled back successfully")
        except Exception as rollback_error:
            logger.warning(f"Rollback failed: {rollback_error}")
            try:
                self.connection.close()
                self._connect()
                logger.info("Reconnected to reset transaction state")
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect after rollback error: {reconnect_error}")
    
    def query(self, sql_query: str) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results as a list of dictionaries.
        
        Args:
            sql_query: SQL query string to execute
        
        Returns:
            List of dictionaries, where each dictionary represents a row
            with column names as keys
        
        Raises:
            Exception: If connection is not available or query execution fails
        """
        if not self.connection:
            raise Exception("Redshift connection not available")
        
        self._reset_transaction()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql_query)
                columns = [desc[0] for desc in cursor.description]
                results = cursor.fetchall()
                return [dict(zip(columns, row)) for row in results]
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            self._reset_transaction()
            raise e
    
    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Redshift connection closed")

def get_db_client() -> Optional[RedshiftClient]:
    """
    Get or create the global database client instance.
    
    Returns:
        RedshiftClient instance or None if initialization fails
    """
    global _db_client
    if _db_client is None:
        try:
            _db_client = RedshiftClient()
        except Exception as e:
            logger.error(f"Failed to initialize Redshift client: {e}")
            return None
    return _db_client

db_client = get_db_client()
