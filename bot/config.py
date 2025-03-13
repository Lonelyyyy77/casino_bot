import dotenv
import os

dotenv.load_dotenv()

TOKEN = os.getenv('TOKEN')
CRYPTO_TOKEN = os.getenv('CRYPTO_TOKEN')
WH_URL = os.getenv('WEBHOOK_URL')