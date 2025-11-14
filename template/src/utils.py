from src.settings import settings
import logging 

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)
logger = logging.getLogger(__name__)

def set_schema_name(schema_name):
    custom_schema_name = schema_name + settings.storage_suffix
    return custom_schema_name