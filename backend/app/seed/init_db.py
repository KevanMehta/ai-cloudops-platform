"""Database initialization entry point."""

import logging
import sys

from app.database import SessionLocal
from app.logging_config import setup_logging
from app.seed.seed_data import init_database

logging.basicConfig(level=logging.INFO)
setup_logging("INFO")
logger = logging.getLogger(__name__)


def main():
    db = SessionLocal()
    try:
        init_database(db)
        logger.info("Seed completed successfully")
    except Exception as e:
        logger.exception("Seed failed: %s", e)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
