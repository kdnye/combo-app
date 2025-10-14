FROM mcr.microsoft.com/devcontainers/python:3.11

WORKDIR /workspace

# Install Python dependencies
COPY requirements.txt scripts/install_dependencies.py /tmp/pip-tmp/
RUN python /tmp/pip-tmp/install_dependencies.py \
        --requirements /tmp/pip-tmp/requirements.txt \
        --no-cache \
    && rm -rf /tmp/pip-tmp

