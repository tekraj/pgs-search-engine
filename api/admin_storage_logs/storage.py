import shutil
import logging
import os
from pathlib import Path

# Setup Logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "storage.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Directories
STORAGE_DIR = Path("storage")
QUARANTINE_DIR = Path("quarantine")

STORAGE_DIR.mkdir(exist_ok=True)
QUARANTINE_DIR.mkdir(exist_ok=True)

class StorageManager:
    @staticmethod
    def save_file(file_content: bytes, filename: str):
        """Saves file to storage if safe, otherwise quarantine."""
        
        # Simple Security Check: Block .exe for this example
        if filename.endswith(".exe"):
            logger.warning(f"Malicious file detected: {filename}")
            StorageManager.quarantine_file(file_content, filename)
            return {"status": "quarantined", "reason": "Executable files not allowed"}

        file_path = STORAGE_DIR / filename
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        logger.info(f"File saved successfully: {filename}")
        return {"status": "success", "path": str(file_path)}

    @staticmethod
    def quarantine_file(file_content: bytes, filename: str):
        """Moves file to a quarantine folder."""
        file_path = QUARANTINE_DIR / filename
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        logger.error(f"File quarantined: {filename}")