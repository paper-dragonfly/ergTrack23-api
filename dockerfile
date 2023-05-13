FROM python:3.9 

# set container working directory 
WORKDIR /ergtrack23api

# install packages
COPY ./requirements.txt /ergtrack23api/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /ergtrack23api/requirements.txt

# add files
RUN mkdir -p ./src
RUN mkdir -p ./config
COPY config/key_gcloud_ergtrack23_api_sa2.json config
COPY config/config.yaml config 
# comment out ^ in prod
COPY README.md .
COPY src src 

# AWS keys ->  move to secure location
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY

ENV AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
ENV AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}

ENV GOOGLE_APPLICATION_CREDENTIALS=./config/key_gcloud_ergtrack23_api_sa2.json
ENV AWS_DEFAULT_REGION=us-east-1
ENV PORT=8080

EXPOSE $PORT
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "80"]

