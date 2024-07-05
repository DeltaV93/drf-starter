FROM python:3.9-slim as builder

ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE template.settings.development

WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt /app/
# Install any dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . /app/

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

# Expose port 8000 for the application
EXPOSE 8000

# Define the command to run the application
CMD ["gunicorn", "template.wsgi:application", "--bind", "0.0.0.0:8000"]
