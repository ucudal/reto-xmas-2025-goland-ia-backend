FROM python:3.12-slim

# Accept a build arg for the Guardrails API key
ARG GUARDRAILS_API_KEY

WORKDIR /app

# Install curl (for healthcheck) and git (needed for guardrails hub install)
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    mv /root/.local/bin/uvx /usr/local/bin/uvx

COPY pyproject.toml uv.lock* ./

RUN uv sync --no-dev --no-cache

# Run the Guardrails configure command to create a .guardrailsrc file
# Only configure if GUARDRAILS_API_KEY is provided
RUN uv run guardrails configure --enable-metrics --enable-remote-inferencing --token "$GUARDRAILS_API_KEY"

# Install required guardrails validators
RUN uv run guardrails hub install hub://guardrails/detect_jailbreak --no-install-local-models
RUN uv run guardrails hub install hub://guardrails/detect_pii --no-install-local-models
RUN uv run guardrails hub install hub://guardrails/toxic_language>=0.0.2 --no-install-local-models

# The ToxicLanguage Validator uses the punkt tokenizer, so we need to download that to a known directory
# Set the directory for nltk data
ENV NLTK_DATA=/opt/nltk_data

# Download punkt data
RUN uv run python -m nltk.downloader -d /opt/nltk_data punkt_tab

COPY . .

# Ensure dependencies are synced after copying files
RUN uv sync --no-dev --no-cache

# Note: Skipping Guardrails Hub validator installation due to API token scope limitations
# The guards will work with basic pattern matching fallback in the code
# For ML-based validation, validators need to be configured post-deployment or with proper token scopes

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uv", "run", "--no-sync", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]