FROM python:3.12

# Set the working directory
WORKDIR /app

# Copy the requirements file first to install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire src directory into the container
COPY ./app /app/app/ 

COPY setup.py /app/setup.py

# Install the app in editable mode
RUN pip install -e . 

RUN pip install --upgrade certifi

# Command to run the FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
