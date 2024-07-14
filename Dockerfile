FROM python:3.9-slim as builder

# Define build arguments
ARG DB_USER
ARG DB_NAME
ARG DB_PASSWORD
ARG DB_HOST
ARG DB_PORT

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    build-essential

WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt > pip_install.log

# Copy the current directory contents into the container at /app
COPY . /app

# Copy the entrypoint script into the container
COPY entrypoint.sh /app/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Make the entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Collect static files
RUN python manage.py collectstatic --noinput

# Use a minimal base image for the final build
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=template.settings.development

# Set work directory
WORKDIR /app

# Copy only the necessary files from the builder stage
COPY --from=builder /app /app

# Install gunicorn
RUN pip install gunicorn
RUN pip install --no-cache-dir -r requirements.txt
# RUN python manage.py migrate
# Create superuser if it doesn't exist
RUN python manage.py create_superuser_if_not_exists
RUN echo "======== CREATED SUPER USER ==========="

# Expose port 8000 for the application
EXPOSE 8000

# Define the command to run the application
CMD ["gunicorn", "template.wsgi:application", "--bind", "0.0.0.0:8000"]
