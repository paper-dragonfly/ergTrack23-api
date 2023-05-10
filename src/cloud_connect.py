from google.cloud.sql.connector import Connector


# initialize parameters
INSTANCE_CONNECTION_NAME = "ergtracker:us-east1:ergtrack-gc-db"
# DB_USER = "ergtrack-api"
# DB_PASS = "api-pw-05102023"
# DB_NAME = "ergtrack-05102023"

DB_USER = "chef"
DB_PASS = "food"
DB_NAME = "sandwiches"

# initialize Connector object
connector = Connector()


# function to return the database connection object
def getconn():
    conn = connector.connect(
        INSTANCE_CONNECTION_NAME, "pg8000", user=DB_USER, password=DB_PASS, db=DB_NAME
    )
    return conn
