from src.settings import settings
import logging
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

# Lazy initialization - only create connection when needed
_db_client = None

class SimpleDBClient:
    """Simple database client that works without zdk dependency"""
    
    def __init__(self):
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Establish database connection"""
        try:
            user = settings.rds_user
            password = settings.rds_password
            host = settings.rds_host
            port = 5432
            dbname = settings.rds_db
            
            if not all([user, password, host, dbname]):
                logger.warning("Database credentials not fully configured")
                return
                
            self.connection = psycopg2.connect(
                host=host,
                port=port,
                database=dbname,
                user=user,
                password=password
            )
            logger.info("Database connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            self.connection = None
    
    def query(self, sql_query):
        """Execute a SQL query and return results"""
        if not self.connection:
            raise Exception("Database connection not available")
        
        try:
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(sql_query)
                results = cursor.fetchall()
                # Convert RealDictRow to regular dict
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise e

def get_db_client():
    """Get database client with lazy initialization"""
    global _db_client
    if _db_client is None:
        try:
            _db_client = SimpleDBClient()
        except Exception as e:
            logger.error(f"Failed to initialize database client: {e}")
            return None
    return _db_client

# For backward compatibility
db_client = get_db_client()
