# Jyothisha Insight report pipeline
#   docker build -t jyotisha .
#   docker run --rm jyotisha selftest
#   docker run --rm -v "$PWD/out:/out" jyotisha report --report A1 --name Sample --date 1990-05-15 \
#       --time 10:30 --lat 6.93 --lon 79.85 --place Colombo --out /out/sample_A1.pdf --qa

# ---- build stage: compile wheels (pyswisseph has no prebuilt wheel for every Python) ----
FROM python:3.13-slim-trixie AS build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements-web.txt /tmp/
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r /tmp/requirements.txt -r /tmp/requirements-web.txt
# Swiss Ephemeris data (1800-2400 AD), pinned to one upstream commit and SHA-256 checked;
# the build fails if a file doesn't match
COPY fetch_ephe.py /tmp/
RUN python /tmp/fetch_ephe.py /ephe

# ---- runtime stage ----
FROM python:3.13-slim-trixie
# Debian trixie: Pango 1.56 / HarfBuzz 10, new enough for Noto Sans Sinhala v3
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

WORKDIR /app
COPY --from=build /ephe ephe/
COPY fonts/ fonts/
COPY jyotisha_*.py prices.json notes_sample.json docker-entrypoint.sh ./
COPY web/ web/
COPY docs/accuracy_jpl.json docs/

RUN useradd --create-home --uid 1000 jyotisha && mkdir /out && chown jyotisha /out && chmod a+r ephe/* \
    && chmod +x docker-entrypoint.sh
USER jyotisha
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["web"]
