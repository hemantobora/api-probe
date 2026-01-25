FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ src/
COPY setup.py .

# Install api-probe
RUN pip install --no-cache-dir .

# Create directory for configs
RUN mkdir -p /configs

# Run as non-root user for security
RUN useradd -m -u 1000 apiprobe && chown -R apiprobe:apiprobe /app
USER apiprobe

ENTRYPOINT ["api-probe"]
CMD ["--help"]
