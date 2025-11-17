import os
from dotenv import load_dotenv


class EnvironmentHandler:
    def __init__(self):
        if os.path.exists('.env'):
            load_dotenv()

        self.environment = os.getenv('ENVIRONMENT', 'LOCAL')
