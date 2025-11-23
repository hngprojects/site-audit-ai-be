import logging
import os
from logging.handlers import RotatingFileHandler

# 1. Create the logs directory if it doesn't exist
log_dir = os.path.join(os.getcwd(), "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 2. Define the path to the log file
log_file_path = os.path.join(log_dir, "site_audit.log")

def get_logger(name: str):
    """
    Creates a logger instance that writes to console AND a file.
    """
    # Create a custom logger
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)

    # 3. Create Formatters (How the log looks)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 4. Handler 1: Write to File (Rotating)
    file_handler = RotatingFileHandler(log_file_path, maxBytes=10_000_000, backupCount=5)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # 5. Handler 2: Write to Console (Terminal)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger