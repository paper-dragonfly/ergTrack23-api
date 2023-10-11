# ergTrack23-api

API for ergTrack app

## Setup for local development
1. Clone repo from GitHub
2. Create config folder with config.yaml file (secrets, not published on github)
3. Create venv and `pip install requirements2.txt`
4. Download Google Cloud SDK (https://cloud.google.com/sdk/docs/install)
    * Need to be authenticated and connected to ergtracker project. Your account must be given permissions to access the project. 
5. Set up auth proxy to connect to remote database: (https://cloud.google.com/sql/docs/postgres/connect-auth-proxy#macos-64-bit) 

### Command to run auth proxy

./cloud-sql-proxy --port 5432 ergtracker:us-east1:ergtrack-gc-db

Run this in command line to allow local conection to cloud sql db
Like starting the postgreSQL 14 server when running local db

### Version

May 24 : V7
