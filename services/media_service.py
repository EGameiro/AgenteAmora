from googleapiclient.discovery import build
from typing import Optional
import config
from services.google_credentials import get_credentials

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# URL pública para imagens compartilhadas no Google Drive
_DRIVE_VIEW_URL = "https://drive.google.com/uc?export=view&id={file_id}"
_DRIVE_THUMB_URL = "https://drive.google.com/thumbnail?id={file_id}&sz=w800"


def get_foto_url(foto_id: str) -> Optional[str]:
    """
    Recebe o ID do arquivo no Google Drive e retorna a URL direta da imagem.
    O arquivo precisa estar compartilhado como 'Qualquer pessoa com o link pode ver'.
    """
    if not foto_id:
        return None
    return _DRIVE_VIEW_URL.format(file_id=foto_id)


def get_foto_thumbnail_url(foto_id: str) -> Optional[str]:
    """Retorna URL de thumbnail (800px) — útil para preview rápido."""
    if not foto_id:
        return None
    return _DRIVE_THUMB_URL.format(file_id=foto_id)


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
