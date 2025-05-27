FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create user and directories
RUN useradd --system --shell /bin/false --home-dir /opt/meet-bot --create-home meet-bot
RUN mkdir -p /etc/meet-bot /var/log/meet-bot
RUN chown -R meet-bot:meet-bot /opt/meet-bot /var/log/meet-bot

# Set working directory
WORKDIR /opt/meet-bot

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .
RUN chown meet-bot:meet-bot main.py

# Switch to non-root user
USER meet-bot

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run application
CMD ["python", "main.py"]