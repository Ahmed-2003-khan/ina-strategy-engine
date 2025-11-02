# Purpose: Defines the steps to build a production-ready container image
# for the strategy-engine service.

# --- Stage 1: The "Builder" Stage ---
# We use a full Python image to install dependencies
FROM python:3.11-slim as builder

# Set the working directory inside the container
WORKDIR /opt/app

# Install build-time dependencies (if any)
# (We don't have any here, but it's good practice)
# RUN apt-get update && apt-get install -y build-essential

# We will install our dependencies into a local directory
# This avoids installing them system-wide
ENV PIP_TARGET=/opt/app/deps
ENV PATH="${PIP_TARGET}/bin:${PATH}"

# Copy only the requirements file first
# This leverages Docker's layer caching.
COPY requirements.txt .

# Install dependencies into our target directory
RUN pip install --no-cache-dir -r requirements.txt --target $PIP_TARGET

# --- Stage 2: The "Final" Stage ---
# We use a *new*, clean base image for our production container
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the *installed dependencies* from the 'builder' stage
COPY --from=builder /opt/app/deps /usr/local/lib/python3.11/site-packages

# Copy our application source code
COPY ./app /app

# Expose the port our application will run on
EXPOSE 8000

# Define the command to run our application
# We use Gunicorn for production instead of Uvicorn's dev server.
# First, let's install Gunicorn.
RUN pip install gunicorn

# Run the app
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000"]