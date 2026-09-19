from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.models import User

# Ponto único de injeção da sessão. Trocar a estratégia de sessão (threadpool,
# AsyncSession) passa a ser uma edição neste arquivo, não em seis rotas.
Db = Annotated[Session, Depends(get_db)]


def get_local_owner(db: Db) -> int:
    """Dono fixo do produto local até existir autenticação de verdade.

    O endpoint nunca recebe owner_id do cliente ou da LLM. Quando houver login,
    esta é a única dependência que deve mudar para resolver a sessão autenticada.
    """
    if db.get(User, 1) is None:
        raise HTTPException(503, "Dono local ainda não foi inicializado")
    return 1


CurrentOwner = Annotated[int, Depends(get_local_owner)]


def get_active(db: Session, model, row_id: int | None, rotulo: str):
    """Busca uma linha que exista **e não esteja arquivada**, ou levanta 404.

    Sem isto, itens excluídos (soft delete) continuavam utilizáveis pela API:
    dava para ativar um modelo excluído ou abrir conversa com persona excluída.
    """
    row = db.get(model, row_id) if row_id is not None else None
    if row is None or getattr(row, "is_archived", False):
        raise HTTPException(404, f"{rotulo} não encontrado(a)")
    return row
