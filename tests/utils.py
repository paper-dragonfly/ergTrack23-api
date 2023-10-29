from src import utils as u
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import MetaData

import sys
sys.path.append(".")
from src.utils import CONN_STR


def generate_token(uid: str) -> str:
    token = u.create_encrypted_token(uid)
    return "Bearer " + str(token, "utf-8")


def reset_postgres():
    """
    Truncate all tables in a postgres database .
    Useful for resetting the postgres db before or after running tests.
    """
    engine = create_engine(CONN_STR, echo=False)
    Session = sessionmaker(bind=engine)
    
    session = Session()

    metadata = MetaData()
    metadata.reflect(bind=session.bind)

    try:
        for table in reversed(metadata.sorted_tables):
                session.execute(table.delete())
        session.commit()

    except Exception as e:
        session.rollback()
        raise e

    session.close()
