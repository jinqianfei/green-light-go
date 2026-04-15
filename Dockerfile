FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip install --no-cache-dir -r requirements.txt --break-system-packages

# Copy application files
COPY . .

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "server.py"]