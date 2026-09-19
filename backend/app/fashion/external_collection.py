"""Captura de imagens externas para a coleção, com limites de rede explícitos."""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from app.fashion.media import MAX_UPLOAD_BYTES


MAX_REDIRECTS = 3
FETCH_TIMEOUT_SECONDS = 10.0


class ExternalImageError(ValueError):
    pass


@dataclass(frozen=True)
class RemoteImage:
    canonical_url: str
    domain: str
    content: bytes
    content_type: str | None


def _canonical_url(value: str) -> tuple[str, str]:
    parsed = urlsplit(value.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ExternalImageError("Use uma URL HTTP(S) pública de imagem.")
    if parsed.username or parsed.password:
        raise ExternalImageError("A URL da imagem não pode conter credenciais.")
    try:
        host = parsed.hostname.encode("idna").decode("ascii").lower()
        port = f":{parsed.port}" if parsed.port else ""
    except ValueError as exc:
        raise ExternalImageError("A porta da URL da imagem é inválida.") from exc
    host_for_url = f"[{host}]" if ":" in host else host
    return urlunsplit((parsed.scheme.lower(), f"{host_for_url}{port}", parsed.path or "/", parsed.query, "")), host


def _validate_public_host(host: str) -> None:
    try:
        addresses = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ExternalImageError("Não foi possível localizar o servidor da imagem.") from exc
    if not addresses:
        raise ExternalImageError("Não foi possível localizar o servidor da imagem.")
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ExternalImageError("A URL da imagem aponta para uma rede não permitida.")


def fetch_remote_image(url: str, *, client_factory=httpx.Client) -> RemoteImage:
    """Baixa uma imagem pública, revisando a URL a cada redirect.

    Resolver o host antes de cada requisição evita que URLs apontem para a rede
    local. O cliente não segue redirects automaticamente para que a validação
    seja aplicada também ao destino de cada salto.
    """
    current_url, domain = _canonical_url(url)
    for _ in range(MAX_REDIRECTS + 1):
        current_url, domain = _canonical_url(current_url)
        _validate_public_host(domain)
        try:
            with client_factory(follow_redirects=False, timeout=FETCH_TIMEOUT_SECONDS, trust_env=False) as client:
                with client.stream("GET", current_url, headers={"Accept": "image/avif,image/webp,image/png,image/jpeg"}) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            raise ExternalImageError("O redirecionamento da imagem não informa destino.")
                        current_url = urljoin(current_url, location)
                        continue
                    if response.status_code < 200 or response.status_code >= 300:
                        raise ExternalImageError("A imagem externa não pôde ser baixada.")
                    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower() or None
                    if content_type and not content_type.startswith("image/"):
                        raise ExternalImageError("A URL não devolveu uma imagem.")
                    parts: list[bytes] = []
                    total = 0
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > MAX_UPLOAD_BYTES:
                            raise ExternalImageError("A imagem excede o limite de 10 MB.")
                        parts.append(chunk)
        except ExternalImageError:
            raise
        except httpx.HTTPError as exc:
            raise ExternalImageError("Não foi possível baixar a imagem externa.") from exc
        return RemoteImage(current_url, domain, b"".join(parts), content_type)
    raise ExternalImageError("A imagem excedeu o limite de redirecionamentos.")
