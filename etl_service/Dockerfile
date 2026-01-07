FROM python:3.14

WORKDIR /opt/etl_service

COPY requirements.txt requirements.txt

RUN  pip install --upgrade pip \
     && pip install -r requirements.txt

COPY . .

ENTRYPOINT ["python", "main.py"]