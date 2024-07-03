FROM public.ecr.aws/lambda/python:3.12

# Install pip and distutils
RUN pip install --upgrade pip && \
    pip install setuptools

# Copy requirements.txt to the container
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install dependencies
RUN pip install -r requirements.txt

# Copy the source code to the container
COPY src/* ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (could also be done as a parameter override outside of Dockerfile)
CMD ["main.handler"]
