"""Wait for the configured database before running migrations."""

import logging
import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings

ATTEMPTS = 30
DELAY_SECONDS = 2
logger = logging.getLogger(__name__)


def main() -> None:
    database_url = get_settings().database_url
    engine = create_engine(database_url, pool_pre_ping=True)
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            print("Database connection ready.", flush=True)
            return
        except OperationalError as exc:
            if attempt == ATTEMPTS:
                raise RuntimeError(
                    "Database remained unavailable for 60 seconds. When using Docker Compose, "
                    "start the complete stack so the 'postgres' service is attached to the app network."
                ) from exc
            logger.warning("Database unavailable (attempt %s/%s); retrying…", attempt, ATTEMPTS)
            time.sleep(DELAY_SECONDS)


if __name__ == "__main__":
    main()
