# syntax=docker/dockerfile:1

FROM python:3.9-bullseye
WORKDIR /app
# ADD requirements.txt .
# ADD app.py .

#Optional
#ENV https_proxy=http://[proxy]:[port]
#ENV http_proxy=http://[proxy]:[port]

# install FreeTDS and dependencies
RUN apt-get update \
 && apt-get install unixodbc -y \
 && apt-get install unixodbc-dev -y \
 && apt-get install freetds-dev -y \
 && apt-get install freetds-bin -y \
 && apt-get install tdsodbc -y \
 && apt-get install --reinstall build-essential -y

# populate "ocbcinst.ini" as this is where ODBC driver config sits
RUN echo "[FreeTDS]\n\
Description = FreeTDS Driver\n\
Driver = /usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so\n\
Setup = /usr/lib/x86_64-linux-gnu/odbc/libtdsS.so" >> /etc/odbcinst.ini

COPY requirements.txt requirements.txt

RUN pip install --upgrade pip

#Pip command without proxy setting
RUN pip install -r requirements.txt

#Use this one if you have proxy setting
#RUN pip --proxy http://[proxy:port] install -r requirements.txtCMD ["python","-i","main.py"]

COPY . .

# ENTRYPOINT [ "python" ]

# CMD ["app.py", "--host=0.0.0.0"]

RUN chmod +x ./entrypoint.sh
ENTRYPOINT ["sh", "entrypoint.sh"]
