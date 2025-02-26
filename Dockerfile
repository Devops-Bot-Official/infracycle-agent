FROM python:3.12-slim

# Install required dependencies including Docker
RUN apt-get update && apt-get install -y \
    docker.io \
    git \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Build Agent script
COPY build_agent.py /app/build_agent.py

# Set default entrypoint
ENTRYPOINT ["python", "/app/build_agent.py"]

