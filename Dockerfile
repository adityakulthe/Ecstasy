# Ecstasy - Formally Verified AI Compiler Pipeline
# Production Docker Container with LLVM, Clang, Z3, and Streamlit IDE

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH"

# Install system dependencies, Clang, LLVM, Z3, Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    clang \
    llvm \
    z3 \
    libz3-dev \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy dependency specifications first for Docker layer caching
COPY requirements.txt pyproject.toml ./

# Install Python dependencies in a venv
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy source tree
COPY . .

# Install Ecstasy in editable mode
RUN pip install --no-cache-dir -e .

# Expose Streamlit port
EXPOSE 8501

# Healthcheck for web UI
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Default entrypoint starts the interactive Streamlit Dark Terminal IDE
CMD ["ecstasy", "ui", "--port", "8501"]
