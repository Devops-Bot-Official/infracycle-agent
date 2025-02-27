FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install required dependencies
RUN apt-get update && apt-get install -y \
    docker.io \
    git \
    bash \
    unzip \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy and Run Installation Script
COPY install_dependencies.sh /install_dependencies.sh
RUN chmod +x /install_dependencies.sh && /install_dependencies.sh

# Copy Build Agent script
COPY build_agent.py /app/build_agent.py

# Set default entrypoint
ENTRYPOINT ["python", "/app/build_agent.py"]




