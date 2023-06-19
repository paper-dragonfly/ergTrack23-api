import psycopg2

# PostgreSQL connection details
DB_HOST = 'db_container'
DB_PORT = '5432'
DB_USER = 'postgres-docker'
DB_PASSWORD = 'postgres-docker-pw'
DB_NAME = 'erg_track'

# PostgreSQL database connection parameters
conn_params = {
    'host': DB_HOST,
    'port': DB_PORT,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'dbname': 'postgres'
}

def create_database():
    try:
        # Connect to the 'postgres' database
        conn = psycopg2.connect(**conn_params)
        conn.autocommit = True
        cursor = conn.cursor()

        # Check if the database already exists
        cursor.execute("SELECT datname FROM pg_database WHERE datname = %s", (DB_NAME,))
        existing_databases = cursor.fetchall()
        if existing_databases:
            print(f"The database '{DB_NAME}' already exists.")
            return

        # Create the database
        cursor.execute(f"CREATE DATABASE {DB_NAME}")
        print(f"The database '{DB_NAME}' has been created successfully.")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    create_database()

########
# from sqlalchemy import create_engine, text
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.exc import ProgrammingError
# import yaml

# # PostgreSQL connection details
# DB_HOST = 'db_container'
# DB_PORT = '5432'
# DB_USER = 'postgres-docker'
# DB_PASSWORD = 'postgres-docker-pw'
# DB_NAME = 'erg_track'

# # PostgreSQL database URL
# DB_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}'

# #OR
# # # Load config file values
# # with open("config/config.yaml", "r") as f:
# #     config_data = yaml.load(f, Loader=yaml.FullLoader)

# # # set db connection string based on run environment
# # DB_URL = config_data["db_conn_str"]['docker_compose']


# def create_database():
#     # Create a PostgreSQL engine
#     engine = create_engine(DB_URL)

#     # Create a session
#     Session = sessionmaker(bind=engine)
#     session = Session()

#     try:
#         # Check if the database already exists
#         existing_databases = session.execute(text("SELECT datname FROM pg_database;"))
#         if (DB_NAME,) in existing_databases:
#             print(f"The database '{DB_NAME}' already exists.")
#             return

#         # Create the database
#         session.execute(text(f'CREATE DATABASE {DB_NAME}'))
#         session.commit()
#         print(f"The database '{DB_NAME}' has been created successfully.")

#     except Exception as e:
#         print(f"An error occurred: {str(e)}")
#         session.rollback()

#     finally:
#         session.close()

# def create_database2():
#     # Create a PostgreSQL engine
#     engine = create_engine(DB_URL)

#     try:
#         # Create a new connection without transaction
#         with engine.connect().execution_options(autocommit=True) as connection:
#             # Check if the database already exists
#             existing_databases = connection.execute(text("SELECT datname FROM pg_database;"))
#             if (DB_NAME,) in existing_databases:
#                 print(f"The database '{DB_NAME}' already exists.")
#                 return

#             # Create the database
#             connection.execute(text(f'CREATE DATABASE {DB_NAME}'))
#             print(f"The database '{DB_NAME}' has been created successfully.")

#     except Exception as e:
#         print(f"An error occurred: {str(e)}")

# if __name__ == '__main__':
#     create_database2()