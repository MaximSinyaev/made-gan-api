from sqlalchemy import create_engine
from sqlalchemy.sql import text as sql_text
import pandas as pd
from typing import NoReturn, Union, Optional, Dict, List
from collections.abc import Mapping, Iterable


class PostgreSQLSession:
    """Сессия PostgreSQL"""

    def __init__(self, connection_string: str) -> NoReturn:
        self.engine = create_engine(connection_string)

    def select(self, query: str) -> pd.DataFrame:
        """Возвращает результат запроса"""
        con = self.engine.connect().execution_options(autocommit=True)
        query = sql_text(query)
        try:
            res = pd.read_sql(query, con=con)
        except Exception:
            raise
        finally:
            con.close()
        return res

    def get_queue_position(self, task_id: str) -> int:
        queue_position = self.select(
            f"select "
            f"  count(*) "
            f"from "
            f"  celery_taskmeta "
            f"where "
            f"  id <= ("
            f"      select "
            f"          id "
            f"      from "
            f"          celery_taskmeta "
            f"      where "
            f"          task_id = '{task_id}'"
            f"  ) "
            f"  and status not in ('SUCCESS', 'FAILURE')"
        ).squeeze().item()
        return queue_position
