# One image, three roles: api | worker | beat (see entrypoint.sh).
# Base: official Playwright image (Apache-2.0) = Ubuntu 24.04 + Python 3.12 + Chromium + its system libraries.
# The tag must match the playwright version pinned in requirements.txt.
FROM mcr.microsoft.com/playwright/python:v1.65.2-noble

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    PIP_ROOT_USER_ACTION=ignore \
    BACKEND_PORT=8000

# DejaVu: openly licensed font with full Polish glyph coverage for the PDF evidence package.
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir --retries 10 --timeout 60 -r requirements.txt

COPY app ./app
COPY entrypoint.sh /entrypoint.sh
RUN chmod 0755 /entrypoint.sh

# non-root user shipped with the Playwright image
USER pwuser
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["api"]
