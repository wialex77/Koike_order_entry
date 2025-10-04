# AWS Elastic Beanstalk WSGI entry point
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import the Flask app
from app import app as application

if __name__ == "__main__":
    application.run()
