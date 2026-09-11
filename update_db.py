import logging
from data_manager import update_cache

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting database update process...")
    update_cache()
    logger.info("Database update completed.")
