# Use the lightweight and compatible Debian Slim as the base image
FROM debian:12-slim

# Set frontend to noninteractive to avoid prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies in a single RUN command to reduce layers
# - Debian includes firefox-esr in its main repository, so no PPA is needed
# - Clean up apt cache in the same layer to reduce image size
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    xvfb \
    fluxbox \
    git \
    xauth \
    python3-tk \
    python3-dev \
    libpci3 \
    libegl1-mesa \
    firefox-esr \
    xterm \
    && rm -rf /var/lib/apt/lists/*

# Set up a working directory
WORKDIR /app

# Copy only the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies using pip
# We use --break-system-packages because Debian 12 protects its global Python environment
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

# Copy the rest of the project files
COPY . .

# Create distribution directory for Firefox policies and copy the file
# This is done after the main COPY so changes to policies don't break the pip cache
RUN mkdir -p /usr/lib/firefox-esr/distribution
COPY policies.json /usr/lib/firefox-esr/distribution/

# Expose the port the API will run on
EXPOSE 8000

# Set the entrypoint script to be executed when the container starts
ENTRYPOINT ["./entrypoint.sh"]
