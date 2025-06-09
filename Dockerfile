FROM python:3.9-slim

WORKDIR /app

# Install SQLite
RUN apt-get update && apt-get install -y sqlite3 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Make init script executable
RUN chmod +x init_db.sh

ENV FLASK_APP=app.py
ENV FLASK_ENV=development

EXPOSE 5000

# Run init script
CMD ["./init_db.sh"] 