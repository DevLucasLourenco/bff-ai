import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.security import MasterKeyError, SecretCipher
from app.db.schema import SchemaOutOfDateError, current_revision, head_revision, verify_schema
from app.db.session import SessionLocal, engine
from app.domain.models import ProviderConfig
from app.services.bootstrap import bootstrap
from app.services.llm.errors import LLMError

# F5.2: sem isso, uma falha de provider não deixava rastro nenhum — a única
# evidência era o texto na tela, que até a Fase 3 era descartado.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s",
)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Migração é passo explícito de deploy (`alembic upgrade head`), nunca
    # automática no boot: com mais de um processo, migrar no lifespan é corrida.
    verify_schema(engine)
    with SessionLocal() as db:
        bootstrap(db)
    logger.info("BFF AI pronto — schema %s", head_revision())
    yield


app = FastAPI(title="BFF AI API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.exception_handler(LLMError)
async def handle_llm_error(_request: Request, exc: LLMError) -> JSONResponse:
    """Erro de provider com `code` estável, em vez de `str(exc)` cru na tela."""
    logger.error("falha de provider code=%s detail=%s", exc.code, exc.provider_detail)
    return JSONResponse(status_code=exc.http_status, content={"detail": exc.as_payload()})


@app.exception_handler(MasterKeyError)
async def handle_master_key_error(_request: Request, exc: MasterKeyError) -> JSONResponse:
    logger.error("problema com APP_MASTER_KEY: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": {"code": exc.code, "message": str(exc), "provider_detail": None}},
    )


@app.get("/health")
def health():
    """Raso de propósito: só diz que o processo está de pé."""
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready():
    """Checa o que realmente quebra: banco, revisão do schema e chave-mestra.

    Antes, /health devolvia ok incondicional e uma APP_MASTER_KEY trocada só
    aparecia na hora de enviar a primeira mensagem, com erro obscuro.
    """
    checks: dict[str, dict] = {}
    ok = True

    try:
        revision = current_revision(engine)
        expected = head_revision()
        healthy = revision == expected
        checks["database"] = {"ok": healthy, "revision": revision, "expected": expected}
        ok &= healthy
    except Exception as exc:  # noqa: BLE001 - o health precisa reportar, não estourar
        checks["database"] = {"ok": False, "error": str(exc)}
        ok = False

    cipher = SecretCipher()
    if not cipher.enabled:
        checks["master_key"] = {"ok": False, "error": "APP_MASTER_KEY não configurada"}
        ok = False
    else:
        try:
            with SessionLocal() as db:
                guardados = db.query(ProviderConfig).filter(ProviderConfig.api_key_encrypted.isnot(None)).all()
                for provider in guardados:
                    cipher.decrypt(provider.api_key_encrypted)
            checks["master_key"] = {"ok": True, "secrets_checked": len(guardados)}
        except MasterKeyError as exc:
            checks["master_key"] = {"ok": False, "error": str(exc)}
            ok = False

    return JSONResponse(status_code=200 if ok else 503, content={"status": "ok" if ok else "degraded", "checks": checks})


__all__ = ["app", "lifespan", "SchemaOutOfDateError"]
