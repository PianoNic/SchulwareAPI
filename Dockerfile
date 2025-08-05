FROM python:3.13.5-slim

# Set environment variables for Docker and Playwright
ARG DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install only Chromium browser and its dependencies using the official Playwright method
# This installs only Chromium and its system dependencies, following Playwright best practices
RUN playwright install --with-deps chromium

# Copy the application code
COPY . .

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Expose port 8000
EXPOSE 8000

# Run the application
CMD ["python", "asgi.py"]
