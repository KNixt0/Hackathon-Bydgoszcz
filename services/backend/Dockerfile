# One image, three roles: api | worker | beat (see entrypoint.sh).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    BACKEND_PORT=8000

WORKDIR /srv
COPY requirements.txt .
# Chromium and its system libraries come from the pinned playwright package, so versions always match.
# DejaVu: openly licensed font with Polish glyphs for the PDF evidence package.
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 10001 pwuser

COPY app ./app
COPY entrypoint.sh /entrypoint.sh
RUN chmod 0755 /entrypoint.sh

USER pwuser
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["api"]
