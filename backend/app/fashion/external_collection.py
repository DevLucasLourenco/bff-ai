"""Captura de imagens externas para a coleção, com limites de rede explícitos."""

from __future__ import annotations

import ipaddress
import http.client
import json
import socket
import ssl
from dataclasses import dataclass
from html.parser import HTMLParser
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


@dataclass(frozen=True)
class CapturedLink:
    image: RemoteImage
    source_url: str
    source_domain: str
    title: str | None


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
    if parsed.port and parsed.port not in {80, 443}:
        raise ExternalImageError("Use uma URL com porta HTTP(S) padrão.")
    host_for_url = f"[{host}]" if ":" in host else host
    canonical = urlunsplit((parsed.scheme.lower(), f"{host_for_url}{port}", parsed.path or "/", parsed.query, ""))
    if len(canonical) > 2048 or len(host) > 255:
        raise ExternalImageError("A URL da imagem é longa demais.")
    return canonical, host


def _validate_public_host(host: str) -> str:
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
    return addresses[0][4][0]


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, ip: str, port: int, timeout: float) -> None:
        super().__init__(host, port, timeout=timeout)
        self._validated_ip = ip

    def connect(self) -> None:
        self.sock = socket.create_connection((self._validated_ip, self.port), self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, ip: str, port: int, timeout: float) -> None:
        super().__init__(host, port, timeout=timeout, context=ssl.create_default_context())
        self._validated_ip = ip

    def connect(self) -> None:
        raw = socket.create_connection((self._validated_ip, self.port), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise


def _request_pinned(url: str, ip: str, accept: str, max_bytes: int) -> tuple[int, dict[str, str], bytes]:
    parsed = urlsplit(url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    connection_class = _PinnedHTTPSConnection if parsed.scheme == "https" else _PinnedHTTPConnection
    connection = connection_class(parsed.hostname or "", ip, port, FETCH_TIMEOUT_SECONDS)
    try:
        target = parsed.path or "/"
        if parsed.query:
            target += f"?{parsed.query}"
        connection.request("GET", target, headers={"Accept": accept, "User-Agent": "BffFashion/1.0"})
        response = connection.getresponse()
        headers = {key.lower(): value for key, value in response.getheaders()}
        length = headers.get("content-length", "")
        if length.isdecimal() and int(length) > max_bytes:
            raise ExternalImageError("O conteúdo do link excede o limite permitido.")
        chunks: list[bytes] = []
        total = 0
        while chunk := response.read(min(65536, max_bytes - total + 1)):
            total += len(chunk)
            if total > max_bytes:
                raise ExternalImageError("O conteúdo do link excede o limite permitido.")
            chunks.append(chunk)
        return response.status, headers, b"".join(chunks)
    except (OSError, http.client.HTTPException, ssl.SSLError) as exc:
        raise ExternalImageError("Não foi possível baixar o conteúdo do link.") from exc
    finally:
        connection.close()


def _fetch_public_resource(url: str, *, max_bytes: int, accept: str, client_factory=None) -> tuple[str, str, bytes, str | None]:
    """Baixa conteúdo limitado e revalida o destino de cada redirect.

    Resolver o host antes de cada requisição evita que URLs apontem para a rede
    local. O cliente não segue redirects automaticamente para que a validação
    seja aplicada também ao destino de cada salto.
    """
    current_url, domain = _canonical_url(url)
    for _ in range(MAX_REDIRECTS + 1):
        current_url, domain = _canonical_url(current_url)
        ip = _validate_public_host(domain)
        try:
            if client_factory is None:
                status, headers, content = _request_pinned(current_url, ip, accept, max_bytes)
            else:
                # Test seam: the production path above pins the socket to the
                # validated IP; fake clients make network tests deterministic.
                with client_factory(follow_redirects=False, timeout=FETCH_TIMEOUT_SECONDS, trust_env=False) as client:
                    with client.stream("GET", current_url, headers={"Accept": accept}) as response:
                        status, headers = response.status_code, response.headers
                        parts: list[bytes] = []
                        total = 0
                        for chunk in response.iter_bytes():
                            total += len(chunk)
                            if total > max_bytes:
                                raise ExternalImageError("O conteúdo do link excede o limite permitido.")
                            parts.append(chunk)
                        content = b"".join(parts)
            if status in {301, 302, 303, 307, 308}:
                location = headers.get("location")
                if not location:
                    raise ExternalImageError("O redirecionamento não informa destino.")
                current_url = urljoin(current_url, location)
                continue
            if status < 200 or status >= 300:
                raise ExternalImageError("O conteúdo do link não pôde ser baixado.")
            content_type = headers.get("content-type", "").split(";", 1)[0].lower() or None
        except ExternalImageError:
            raise
        except httpx.HTTPError as exc:
            raise ExternalImageError("Não foi possível baixar a imagem externa.") from exc
        return current_url, domain, content, content_type
    raise ExternalImageError("O link excedeu o limite de redirecionamentos.")


def fetch_remote_image(url: str, *, client_factory=None) -> RemoteImage:
    final_url, domain, content, content_type = _fetch_public_resource(
        url, max_bytes=MAX_UPLOAD_BYTES, accept="image/webp,image/png,image/jpeg", client_factory=client_factory,
    )
    if content_type and not content_type.startswith("image/"):
        raise ExternalImageError("A URL não devolveu uma imagem.")
    return RemoteImage(final_url, domain, content, content_type)


def _looks_like_supported_image(content: bytes) -> bool:
    return content.startswith((b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"RIFF"))


class _ProductImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.image_urls: list[str] = []
        self.product_image_urls: list[str] = []
        self.title: str | None = None
        self._inside_title = False
        self._json_ld = False
        self._json_ld_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag == "title":
            self._inside_title = True
        if tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self._json_ld = True
            self._json_ld_parts = []
        if tag == "meta":
            key = (values.get("property") or values.get("name") or values.get("itemprop") or "").lower()
            if key in {"og:image", "og:image:secure_url", "twitter:image", "image"} and values.get("content"):
                self.image_urls.append(values["content"])
            if key in {"og:title", "twitter:title"} and values.get("content"):
                self.title = values["content"][:180]
        if tag == "link" and values.get("rel", "").lower() == "image_src" and values.get("href"):
            self.image_urls.append(values["href"])
        if tag == "img" and values.get("src") and any(term in values.get("alt", "").lower() for term in ("produto", "product", "peça", "roupa")):
            self.image_urls.append(values["src"])
        if tag == "img" and values.get("data-src") and any(term in values.get("alt", "").lower() for term in ("produto", "product", "peça", "roupa")):
            self.image_urls.append(values["data-src"])

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._inside_title = False
        if tag == "script" and self._json_ld:
            self._json_ld = False
            try:
                document = json.loads("".join(self._json_ld_parts))
                entries = document if isinstance(document, list) else [document]
                expanded = []
                for entry in entries:
                    if isinstance(entry, dict):
                        graph = entry.get("@graph")
                        expanded.extend(graph if isinstance(graph, list) else [entry])
                entries = expanded
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    kinds = entry.get("@type", [])
                    kinds = [kinds] if isinstance(kinds, str) else kinds
                    if not isinstance(kinds, list) or not any(isinstance(kind, str) and kind.lower().endswith("product") for kind in kinds):
                        continue
                    image = entry.get("image")
                    if isinstance(image, str):
                        self.product_image_urls.append(image)
                    elif isinstance(image, list):
                        self.product_image_urls.extend(value for value in image if isinstance(value, str))
                    elif isinstance(image, dict) and isinstance(image.get("url"), str):
                        self.product_image_urls.append(image["url"])
            except (ValueError, TypeError):
                pass

    def handle_data(self, data: str) -> None:
        if self._inside_title and not self.title:
            self.title = data.strip()[:180] or None
        if self._json_ld:
            self._json_ld_parts.append(data)


def fetch_fashion_link(url: str, *, client_factory=None) -> CapturedLink:
    """Aceita URL direta de imagem ou página com imagem principal identificável."""
    final_url, domain, content, content_type = _fetch_public_resource(
        url, max_bytes=MAX_UPLOAD_BYTES, accept="text/html,image/webp,image/png,image/jpeg", client_factory=client_factory,
    )
    if (content_type and content_type.startswith("image/")) or (content_type is None and _looks_like_supported_image(content)):
        return CapturedLink(RemoteImage(final_url, domain, content, content_type), final_url, domain, None)
    if content_type not in {"text/html", "application/xhtml+xml"} and not (content_type is None and content.lstrip().startswith(b"<")):
        raise ExternalImageError("O link não contém uma imagem ou página de produto reconhecível.")
    if len(content) > 2 * 1024 * 1024:
        raise ExternalImageError("A página é grande demais para extrair uma imagem.")
    parser = _ProductImageParser()
    parser.feed(content.decode("utf-8", errors="replace"))
    for image_url in list(dict.fromkeys(parser.product_image_urls + parser.image_urls))[:5]:
        candidate = urljoin(final_url, image_url)
        try:
            image = fetch_remote_image(candidate, client_factory=client_factory)
            return CapturedLink(image, final_url, domain, parser.title)
        except ExternalImageError:
            continue
    raise ExternalImageError("Não encontrei uma foto principal nesse link. Envie a URL direta da imagem ou anexe uma foto.")
