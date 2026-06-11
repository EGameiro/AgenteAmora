from typing import Optional


def get_foto_url(foto_id: str) -> Optional[str]:
    """
    Retorna a URL da foto do prato.
    O campo foto_id da planilha deve conter a URL completa da imagem (ex: Imgur).
    """
    if not foto_id:
        return None
    return foto_id


def get_foto_thumbnail_url(foto_id: str) -> Optional[str]:
    return get_foto_url(foto_id)
