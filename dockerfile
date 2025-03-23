FROM python:3.9

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

ENV MONGO_URI=mongodb://mongo:27017/chatdb

CMD ["python", "main.py"]