from google.cloud.sql.connector import Connector
import pdb


# # initialize parameters
# cloudsql_config = {
#     "unix_socket": "/cloudsql/{}".format("ergtracker:us-east1:ergtrack-gc-db"),
#     "user": "ergtrack23-api",
#     "password": "api-pw-05102023",
#     "database": "ergtrack05102023"
#     # DB_USER = "chef"
#     # DB_PASS = "food"
#     # DB_NAME = "sandwiches"
# }

# function to return the database connection object
# def getconn():
#     conn = connector.connect(**cloudsql_config)
#     return conn

# initialize parameters
INSTANCE_CONNECTION_NAME = "ergtracker:us-east1:ergtrack-gc-db"
DB_USER = "ergtrack23-api"
DB_PASS = "api-pw-05102023"
DB_NAME = "ergtrack05102023"

# initialize Connector object
connector = Connector()


def getconn():
    conn = connector.connect(
        INSTANCE_CONNECTION_NAME, "pg8000", user=DB_USER, password=DB_PASS, db=DB_NAME
    )
    pdb.set_trace()
    return conn
