FROM python:3.11-slim-bookworm@sha256:389c808973913a68e42e5c3bc4d169ed1bf52b83a543be37a2dbe0ab034182ed
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY --chown=65534:65534 lab/ /work/lab/
COPY --chown=65534:65534 kit/ /work/kit/
RUN mkdir /work/demo && chown 65534:65534 /work/demo
USER 65534:65534
WORKDIR /work/lab
ENV PYTHONDONTWRITEBYTECODE=1 SKYLIT_AGENT_KIT=/work/kit
RUN --network=none python -X utf8 -I -B scripts/watchlist_desk.py --kit /work/kit --output /work/demo/default
RUN --network=none python -X utf8 -I -B experiments/watchlist-investigator/run.py --kit /work/kit --output /work/demo/default/baseline.md
RUN --network=none python -m unittest discover -s tests -p test_watchlist_desk.py -v
CMD ["python", "-I", "-B", "-m", "http.server", "8080", "--bind", "0.0.0.0", "--directory", "/work/demo/default"]
