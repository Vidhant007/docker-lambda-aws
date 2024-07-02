FROM public.ecr.aws/lambda/python:3.12

# Install distutils
RUN yum install -y python3-distutils

# Copy requirements.txt to the container
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Upgrade pip to the latest version
RUN pip install --upgrade pip

# Install the required packages
RUN pip install -r requirements.txt

# Copy the function code to the container
COPY src/* ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler
CMD ["main.lambda_handler"]
