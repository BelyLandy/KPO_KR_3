FROM python:3.13

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN mkdir /app

WORKDIR /app

COPY pyproject.toml poetry.lock ./
COPY src ./app

RUN pip install poetry && poetry config virtualenvs.create false && poetry install --no-root

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000"]