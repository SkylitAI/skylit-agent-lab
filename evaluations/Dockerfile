FROM python:3.11-slim-bookworm@sha256:389c808973913a68e42e5c3bc4d169ed1bf52b83a543be37a2dbe0ab034182ed

# Dependency setup has network access; the later evaluation container does not.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
COPY --chown=65534:65534 lab/ /work/lab/
COPY --chown=65534:65534 kit/ /work/kit/
USER 65534:65534
WORKDIR /work/lab
ENTRYPOINT ["python", "-X", "utf8", "-I", "-B", "evaluations/isolation_probe.py"]
