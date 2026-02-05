# Use Python 3.12 on Alpine Linux for smaller image size and fewer vulnerabilities
FROM python:3.12-alpine

# Install system dependencies required for building and running the application
# - ca-certificates: SSL/TLS certificate authorities for HTTPS connections
# - openssl: SSL/TLS toolkit for secure communications
# - gcc: C compiler needed to build Python packages with C extensions
# - musl-dev: Development files for musl C library (Alpine's libc)
# - libffi-dev: Development files for Foreign Function Interface library
RUN apk add --no-cache --upgrade \
    ca-certificates \
    openssl \
    gcc \
    musl-dev \
    libffi-dev \
    && update-ca-certificates

# Set working directory for the application
WORKDIR /app

# Copy Python requirements file
# Copying this separately allows Docker to cache this layer if requirements don't change
COPY requirements.txt .

# Upgrade pip to latest version and install Python dependencies
# --no-cache-dir: Don't cache downloaded packages to reduce image size
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code and setup configuration
COPY src/ /app/src/
COPY setup.py /app/

# Install the api-probe package in editable mode
# -e flag allows the package to be imported and run as a command
RUN pip install --no-cache-dir -e .

# Create a non-root user for security best practices
# -D: Don't assign a password (no login allowed)
# -u 1000: Set user ID to 1000 (common convention)
RUN adduser -D -u 1000 apiprobe && \
    chown -R apiprobe:apiprobe /app

# Switch to non-root user to run the application
# This limits potential damage if the container is compromised
USER apiprobe

# Set environment variables
# PYTHONUNBUFFERED=1: Force Python to run in unbuffered mode for real-time logging
# SSL_CERT_FILE: Point to Alpine's CA certificate bundle for SSL verification
# REQUESTS_CA_BUNDLE: Same as above, specifically for the requests library
ENV PYTHONUNBUFFERED=1 \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# Set the default command to run when container starts
# ENTRYPOINT makes 'api-probe' the main command
# CMD provides default arguments (--help) that can be overridden
ENTRYPOINT ["api-probe"]
CMD ["--help"]