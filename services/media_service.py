from googleapiclient.discovery import build
from typing import Optional
import config
from services.google_credentials import get_credentials

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# URL raw do GitHub para imagens hospedadas no repositório
_GITHUB_RAW_URL = "https://raw.githubusercontent.com/EGameiro/AgenteAmora/master/fotos/{foto_id}"


def get_foto_url(foto_id: str) -> Optional[str]:
    """
    Recebe o nome do arquivo (ex: picanha.jpg) e retorna a URL raw do GitHub.
    As imagens devem estar na pasta fotos/ do repositório.
    """
    if not foto_id:
        return None
    return _GITHUB_RAW_URL.format(foto_id=foto_id)


def get_foto_thumbnail_url(foto_id: str) -> Optional[str]:
    """Alias para get_foto_url — GitHub raw já é URL direta."""
    return get_foto_url(foto_id)


def verificar_arquivo_existe(foto_id: str) -> bool:
    """
    Verifica via Google Drive API se o arquivo existe e está acessível.
    Útil para validar os IDs da planilha antes de enviar ao cliente.
    """
    if not foto_id:
        return False
    try:
        creds = get_credentials(SCOPES)
        service = build("drive", "v3", credentials=creds)
        service.files().get(fileId=foto_id, fields="id,name").execute()
        return True
    except Exception:
        return False
