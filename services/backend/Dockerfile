# One image, three roles: api | worker | beat (see entrypoint.sh).
FROM mcr.microsoft.com/playwright/python:v1.65.2-noble
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 BACKEND_PORT=8000
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
USER pwuser
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["api"]
