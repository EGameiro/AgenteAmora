import json
from google.oauth2.service_account import Credentials
import config


def get_credentials(scopes: list[str]) -> Credentials:
    """
    Carrega credenciais da service account.
    Prioridade: variável GOOGLE_CREDENTIALS_JSON (Railway) > arquivo local.
    """
    if config.GOOGLE_CREDENTIALS_JSON:
        info = json.loads(config.GOOGLE_CREDENTIALS_JSON)
        return Credentials.from_service_account_info(info, scopes=scopes)
    return Credentials.from_service_account_file(config.GOOGLE_CREDENTIALS_FILE, scopes=scopes)
