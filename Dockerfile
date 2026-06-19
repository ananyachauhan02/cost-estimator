FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies + LibreOffice headless for Excel formula recalculation
RUN apt-get update && apt-get install -y \
    build-essential \
    libreoffice-calc \
    libreoffice-core \
    --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the default Streamlit port
EXPOSE 8501

# Run the Streamlit application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
