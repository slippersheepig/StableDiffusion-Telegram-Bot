# Use an official Python runtime as a parent image
FROM python:alpine

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Define environment variable for Python to run in unbuffered mode
ENV PYTHONUNBUFFERED 1

# Run app.py when the container launches
CMD ["python", "main.py"]
