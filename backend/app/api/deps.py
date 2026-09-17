from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db

# Ponto único de injeção da sessão. Trocar a estratégia de sessão (threadpool,
# AsyncSession) passa a ser uma edição neste arquivo, não em seis rotas.
Db = Annotated[Session, Depends(get_db)]
