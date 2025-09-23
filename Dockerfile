# Use a specific version of Ubuntu for reproducibility
FROM ubuntu:22.04

# Set frontend to noninteractive to avoid prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
# - python3 and pip for the application
# - xvfb, fluxbox for the virtual display and window management
# - firefox-esr for a stable browser to test against
# - git for cloning or any git operations if needed
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
    && rm -rf /var/lib/apt/lists/*

# Add Mozilla PPA and install Firefox ESR
RUN apt-get update && apt-get install -y software-properties-common && \
    add-apt-repository ppa:mozillateam/ppa && \
    apt-get update && \
    apt-get install -y firefox-esr

# Set up a working directory
WORKDIR /app

# Copy the project files into the container
COPY . .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Expose the port the API will run on
EXPOSE 8000

# Set the entrypoint script to be executed when the container starts
ENTRYPOINT ["./entrypoint.sh"]

