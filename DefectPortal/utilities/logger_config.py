from datetime import datetime
import logging
import logging.handlers
import os
import shutil
import sys

def setup_logger(log_root="logs", log_file="app.log"):
    """
    Sets up logging with:
      - Daily folder creation (logs/YYYY-MM-DD/)
      - Keeps only the last 2 days of log folders
      - Rotating log file (daily)
      - Redirects stdout/stderr safely
    """
    # --- Create today's dated folder ---
    today_folder = datetime.now().strftime("%Y-%m-%d")
    log_dir = os.path.join(log_root, today_folder)
    # Create logs folder if not exists
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)

    # --- Cleanup old log folders (keep last 2) ---
    cleanup_old_log_folders(log_root, keep_days=2)

    # Rotating daily log file (keep 14 backups)
    handler = logging.handlers.TimedRotatingFileHandler(
        log_path, when="midnight", backupCount=14, encoding="utf-8"
    )
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if reloaded
    if not any(isinstance(h, logging.handlers.TimedRotatingFileHandler) for h in root_logger.handlers):
        root_logger.addHandler(handler)

    # Print BEFORE redirecting stdout/stderr
    print(f"Logger initialized, writing to {log_path}")

    # Redirect stdout/stderr into logging
    class StreamToLogger:
        def __init__(self, logger, level=logging.INFO):
            self.logger = logger
            self.level = level
        def write(self, message):
            message = message.strip()
            if message:
                if "RecursionError" not in message:
                    self.logger.log(self.level, message)
        def flush(self):
            pass
        def isatty(self):
            return False
        def fileno(self):
            # Return a dummy file descriptor for compatibility
            return -1

    

    # redirect after print
    sys.stdout = StreamToLogger(root_logger, logging.INFO)
    sys.stderr = StreamToLogger(root_logger, logging.ERROR)

    logging.getLogger("streamlit").setLevel(logging.INFO)

    # logger = logging.getLogger(__name__)
    # logger.info(" Logger initialized, writing to %s", log_path)

    return root_logger


def cleanup_old_log_folders(log_root, keep_days):
    """
    Keeps only the most recent 'keep_days' folders under log_root.
    Deletes older folders safely.
    """
    try:
        if not os.path.exists(log_root):
            return

        # Get all subdirectories under logs/
        folders = [
            f for f in os.listdir(log_root)
            if os.path.isdir(os.path.join(log_root, f))
        ]

        # Sort by date (lexical order works for YYYY-MM-DD)
        folders.sort()

        # If more than N folders exist, delete older ones
        if len(folders) > keep_days:
            old_folders = folders[:-keep_days]
            for folder in old_folders:
                folder_path = os.path.join(log_root, folder)
                shutil.rmtree(folder_path, ignore_errors=True)
                print(f" Deleted old log folder: {folder_path}")

    except Exception as e:
        print(f" Log cleanup failed: {e}")
