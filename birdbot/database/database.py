import os
from sqlalchemy import create_engine
import pandas as pd
from datetime import datetime, timedelta

class Database:
    def __init__(self):
        host = os.environ.get("MYSQL_HOST")
        database = os.environ.get("MYSQL_DATABASE")
        user = os.environ.get("MYSQL_USER")
        password = os.environ.get("MYSQL_PASSWORD")

        self.engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}/{database}", pool_pre_ping=True)

    def get_recent_observations(self, since: timedelta=timedelta(days=1)) -> pd.DataFrame:
        start_time = datetime.now() - since

        query = f"""
            SELECT
                id,
                source_node,
                date,
                time,
                begin_time,
                scientific_name,
                common_name,
                confidence
            FROM notes
            WHERE begin_time >= %s
        """

        with self.engine.connect() as conn:
            return pd.read_sql(query, conn, params=(start_time,))