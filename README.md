# ergTrack23-api

API for ergTrack app

## Setup for local development
1. Clone repo from GitHub
2. Create config folder with config.yaml file (secrets, not published on github)
3. Create venv `$python3 -m venv path/to/venv` and activate `$source path/to/venv/bin/activate`
4. Install required packages  `$pip install -r requirements.txt`
4. Download Google Cloud SDK (https://cloud.google.com/sdk/docs/install)
    * Need to be authenticated and connected to ergtracker project. Your account must be given permissions to access the project. 
5. Set up auth proxy to connect to remote database: (https://cloud.google.com/sql/docs/postgres/connect-auth-proxy#macos-64-bit) 

### Command to run auth proxy

```./cloud-sql-proxy --port 5432 ergtracker:us-east1:ergtrack-gc-db```

Run this in command line to allow local conection to cloud sql db
Like starting the postgreSQL 14 server when running local db

### Updating Requirements 
1. Inside your virtual environment install pip-tools
    ```source /path/to/venv/bin/activate```
    ```python -m pip install pip-tools```
2. List required packages in `requirements.in` 
3. Run `pip-compile requirements.in -o requirements.txt` to create requirements.txt file


### Version

May 24 : V7


### Building Docker images on M1 Mac
If you encounter the error 
```An error occurred: SCRAM authentication requires libpq version 10 or above```
You need to rebuild your image with this env var
```export DOCKER_DEFAULT_PLATFORM=linux/amd64```