FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    pandoc \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-xetex \
    texlive-fonts-recommended \
    texlive-latex-extra \
    librsvg2-bin \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy rest of the app
COPY . .

# Create output directory explicitly
RUN mkdir -p output

# Railway exposes PORT dynamically
ENV PORT=5000

# Expose Flask port
EXPOSE 5000

# Start Flask
CMD ["python", "app.py"]