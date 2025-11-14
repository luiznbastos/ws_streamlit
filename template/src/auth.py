import bcrypt
from zdk.models.users import User
from src.database import db_client
from src.utils import logger

def hash_password(password: str) -> str:
    """
    Util. Use it to save the first user.
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def authenticate(email, password):
    """
    Authenticate the user by checking the password against a stored hash.
    """
    # Load User
    logger.info(f"Getting {email} information...")
    users = db_client.get(
        entity=User,
        where_clause=(User.email == email)
    )

    if not users or len(users) == 0:
        logger.warning(f"User {email} not found.")
        return {"success": False, "error": "User not found."}

    
    for user in users:
        logger.info(f"User {email} found.")
        # Check password
        logger.info(f"Checking password for {email}...")
        # Check if the password matches the stored hash
        logger.info(password.encode("utf-8"))
        logger.info(user.password.encode("utf-8"))
        if bcrypt.checkpw(password.encode("utf-8"), user.password.encode("utf-8")):
            return {"success": True, "error": None}
    
    return {"success": False, "error": "Wrong password."}
