import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Configure test environment variables
os.environ["DOWNLOAD_DIR"] = str(backend_dir / "tests" / "test_data" / "downloads")
os.environ["TEMP_DIR"] = str(backend_dir / "tests" / "test_data" / "temp")
os.environ["YTDLP_AUTO_UPDATE"] = "false"
os.environ["MAX_CONCURRENT_DOWNLOADS"] = "2"
