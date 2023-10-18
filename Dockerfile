FROM python:3.9 

# set container working directory 
WORKDIR /ergtrack23api

# install packages
COPY ./requirements.txt /ergtrack23api/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /ergtrack23api/requirements.txt

# add files
RUN mkdir -p ./src
RUN mkdir -p ./alembic
COPY alembic alembic
COPY alembic.ini .
COPY db_init_docker.py .
COPY README.md .
COPY src src 
# TODO mount this stuff
COPY config config
COPY tests tests


#  this DEV_ENV is over-written in docker compose
ENV DEV_ENV=prod  
ENV AWS_DEFAULT_REGION=us-east-1
ENV PORT=8080

EXPOSE $PORT
# over riding in docker compose
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]

