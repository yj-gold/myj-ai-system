import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

IG_API_KEY = os.getenv("IG_API_KEY", "")
IG_USERNAME = os.getenv("IG_USERNAME", "")
IG_PASSWORD = os.getenv("IG_PASSWORD", "")
IG_ACCOUNT_TYPE = os.getenv("IG_ACCOUNT_TYPE", "LIVE").upper()
IG_ACCOUNT_ID = os.getenv("IG_ACCOUNT_ID", "")

BASE_URL_LIVE = "https://api.ig.com/gateway/deal"
BASE_URL_DEMO = "https://demo-api.ig.com/gateway/deal"
BASE_URL = BASE_URL_LIVE if IG_ACCOUNT_TYPE == "LIVE" else BASE_URL_DEMO

_default_from = (datetime.utcnow() - timedelta(days=730)).strftime("%Y-%m-%d")
_default_to = datetime.utcnow().strftime("%Y-%m-%d")

ANALYSIS_FROM_DATE = os.getenv("ANALYSIS_FROM_DATE") or _default_from
ANALYSIS_TO_DATE = os.getenv("ANALYSIS_TO_DATE") or _default_to

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")
