"""Captura de imagens externas para a coleção, com limites de rede explícitos."""

from __future__ import annotations

import ipaddress
import http.client
import io
import json
import re
import socket
import ssl
import time
import zlib
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import parse_qsl, unquote, urlencode, urljoin, urlsplit, urlunsplit

import httpx
import brotli
from PIL import Image, UnidentifiedImageError

from app.fashion.media import MAX_PIXELS, MAX_UPLOAD_BYTES


MAX_REDIRECTS = 3
FETCH_TIMEOUT_SECONDS = 10.0
PAGE_MAX_BYTES = 2 * 1024 * 1024
METADATA_MAX_BYTES = 512 * 1024
MAX_IMAGE_CANDIDATES = 8
CANDIDATE_FETCH_BUDGET_SECONDS = 20.0
TRACKING_PARAMETERS = {"fbclid", "gclid", "sid", "ref", "reco_id", "reco_client", "reco_item_pos", "reco_backend", "reco_backend_type", "reco_model", "polycard_client"}
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}


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


def normalize_source_url(value: str) -> str:
    """Remove fragmento e rastreamento sem alterar parâmetros funcionais da loja."""
    parsed = urlsplit(value.strip().replace("\\&", "&").replace("\\_", "_"))
    kept_params = [
        (key, item) for key, item in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_PARAMETERS
    ]
    # Preserva a codificação original de URLs assinadas quando não há
    # parâmetros de rastreamento para remover.
    query = parsed.query if len(kept_params) == len(parse_qsl(parsed.query, keep_blank_values=True)) else urlencode(kept_params)
    cleaned = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, ""))
    return _canonical_url(cleaned)[0]


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


def _decode_zlib(content: bytes, max_bytes: int, wbits: int) -> bytes:
    decoder = zlib.decompressobj(wbits)
    expanded = decoder.decompress(content, max_bytes + 1)
    if len(expanded) > max_bytes:
        raise ExternalImageError("O conteúdo do link excede o limite permitido.")
    expanded += decoder.flush(max_bytes - len(expanded) + 1)
    if len(expanded) > max_bytes:
        raise ExternalImageError("O conteúdo do link excede o limite permitido.")
    if not decoder.eof:
        raise ExternalImageError("O site devolveu conteúdo compactado incompleto.")
    return expanded


def _decode_content(content: bytes, encoding: str, max_bytes: int) -> bytes:
    """Aplica Content-Encoding em ordem inversa, limitando também os bytes expandidos."""
    codings = [part.strip().lower() for part in encoding.split(",") if part.strip()]
    for coding in reversed(codings):
        if coding == "identity":
            continue
        if coding in {"gzip", "x-gzip", "deflate"}:
            wbits = 16 + zlib.MAX_WBITS if coding in {"gzip", "x-gzip"} else zlib.MAX_WBITS
            try:
                expanded = _decode_zlib(content, max_bytes, wbits)
            except zlib.error as exc:
                if coding != "deflate":
                    raise ExternalImageError("O site devolveu conteúdo compactado inválido.") from exc
                # Algumas lojas enviam deflate sem o envelope zlib (RFC 9110).
                try:
                    expanded = _decode_zlib(content, max_bytes, -zlib.MAX_WBITS)
                except zlib.error as raw_exc:
                    raise ExternalImageError("O site devolveu conteúdo compactado inválido.") from raw_exc
            content = expanded
        elif coding == "br":
            try:
                decoder = brotli.Decompressor()
                parts: list[bytes] = []
                total = 0
                for offset in range(0, len(content), 1024):
                    part = decoder.process(content[offset:offset + 1024])
                    total += len(part)
                    if total > max_bytes:
                        raise ExternalImageError("O conteúdo do link excede o limite permitido.")
                    parts.append(part)
                if not decoder.is_finished():
                    raise ExternalImageError("O site devolveu conteúdo compactado incompleto.")
            except brotli.error as exc:
                raise ExternalImageError("O site devolveu conteúdo compactado inválido.") from exc
            content = b"".join(parts)
        else:
            raise ExternalImageError("O site usou uma compactação de resposta não suportada.")
    return content


def _request_pinned(url: str, ip: str, accept: str, max_bytes: int) -> tuple[int, dict[str, str], bytes]:
    parsed = urlsplit(url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    connection_class = _PinnedHTTPSConnection if parsed.scheme == "https" else _PinnedHTTPConnection
    connection = connection_class(parsed.hostname or "", ip, port, FETCH_TIMEOUT_SECONDS)
    try:
        target = parsed.path or "/"
        if parsed.query:
            target += f"?{parsed.query}"
        connection.request("GET", target, headers={"Accept": accept, **REQUEST_HEADERS})
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
        content = _decode_content(b"".join(chunks), headers.get("content-encoding", ""), max_bytes)
        return response.status, headers, content
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
                    with client.stream("GET", current_url, headers={"Accept": accept, **REQUEST_HEADERS}) as response:
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
        self.gallery_image_urls: list[str] = []
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
            if key in {"og:image", "og:image:url", "og:image:secure_url", "twitter:image", "twitter:image:src", "image"} and values.get("content"):
                self.image_urls.append(values["content"])
            if key in {"og:title", "twitter:title"} and values.get("content"):
                self.title = values["content"][:180]
        if tag == "link" and (values.get("rel", "").lower() == "image_src" or values.get("itemprop", "").lower() == "image") and values.get("href"):
            self.image_urls.append(values["href"])
        if tag in {"img", "source"}:
            context = " ".join(values.get(key, "") for key in ("alt", "class", "id", "data-testid")).lower()
            if any(term in context for term in ("produto", "product", "peça", "roupa", "gallery", "galeria", "hero", "photo", "picture")):
                for key in ("data-zoom-src", "data-original", "data-src", "src"):
                    if values.get(key):
                        self.gallery_image_urls.append(values[key])
                for key in ("data-srcset", "srcset"):
                    if values.get(key):
                        # A última variante costuma ser a maior resolução.
                        self.gallery_image_urls.extend(
                            part.strip().split()[0] for part in values[key].split(",") if part.strip()
                        )

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._inside_title = False
        if tag == "script" and self._json_ld:
            self._json_ld = False
            try:
                document = json.loads("".join(self._json_ld_parts))
                for entry in _product_entries(document):
                    image = entry.get("image")
                    if isinstance(image, str):
                        self.product_image_urls.append(image)
                    elif isinstance(image, list):
                        for value in image:
                            if isinstance(value, str):
                                self.product_image_urls.append(value)
                            elif isinstance(value, dict):
                                candidate = value.get("contentUrl") or value.get("url")
                                if isinstance(candidate, str):
                                    self.product_image_urls.append(candidate)
                    elif isinstance(image, dict):
                        candidate = image.get("contentUrl") or image.get("url")
                        if isinstance(candidate, str):
                            self.product_image_urls.append(candidate)
            except (ValueError, TypeError):
                pass

    def handle_data(self, data: str) -> None:
        if self._inside_title and not self.title:
            self.title = data.strip()[:180] or None
        if self._json_ld:
            self._json_ld_parts.append(data)


def _product_entries(value: object, depth: int = 0):
    """Encontra Product e ProductGroup também em @graph e hasVariant."""
    if depth > 5:
        return
    if isinstance(value, list):
        for child in value:
            yield from _product_entries(child, depth + 1)
    elif isinstance(value, dict):
        kinds = value.get("@type", [])
        kinds = [kinds] if isinstance(kinds, str) else kinds
        if isinstance(kinds, list) and any(
            isinstance(kind, str) and kind.lower().rsplit("/", 1)[-1] in {"product", "productgroup"}
            for kind in kinds
        ):
            yield value
        for key in ("@graph", "mainEntity", "hasVariant"):
            if key in value:
                yield from _product_entries(value[key], depth + 1)


def _valid_image(content: bytes) -> bool:
    try:
        with Image.open(io.BytesIO(content)) as image:
            if image.format not in {"JPEG", "PNG", "WEBP"} or image.width * image.height > MAX_PIXELS:
                return False
            image.verify()
        return True
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        return False


def _capture_candidate_images(urls: list[str], *, base_url: str, client_factory=None) -> RemoteImage | None:
    deadline = time.monotonic() + CANDIDATE_FETCH_BUDGET_SECONDS
    for image_url in list(dict.fromkeys(urljoin(base_url, url) for url in urls if url and not url.startswith("data:")))[:MAX_IMAGE_CANDIDATES]:
        if time.monotonic() >= deadline:
            break
        try:
            image = fetch_remote_image(image_url, client_factory=client_factory)
            if _valid_image(image.content):
                return image
        except ExternalImageError:
            continue
    return None


def _mercadolivre_item_id(url: str) -> str | None:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if host not in {"produto.mercadolivre.com.br", "www.mercadolivre.com.br", "mercadolivre.com.br"}:
        return None
    match = re.search(r"/(MLB)-?(\d{6,})(?:-|/|$)", parsed.path, re.I)
    return f"MLB{match.group(2)}" if match else None


def _capture_mercadolivre_api(source_url: str, *, client_factory=None) -> CapturedLink | None:
    item_id = _mercadolivre_item_id(source_url)
    if not item_id:
        return None
    try:
        api_url, _, content, content_type = _fetch_public_resource(
            f"https://api.mercadolibre.com/items/{item_id}",
            max_bytes=METADATA_MAX_BYTES, accept="application/json", client_factory=client_factory,
        )
        if content_type != "application/json":
            return None
        data = json.loads(content)
        if not isinstance(data, dict) or data.get("id") != item_id:
            return None
        pictures = data.get("pictures")
        urls = [picture.get("secure_url") or picture.get("url") for picture in pictures if isinstance(picture, dict)] if isinstance(pictures, list) else []
        if isinstance(data.get("thumbnail"), str):
            urls.append(data["thumbnail"])
        image = _capture_candidate_images(urls, base_url=api_url, client_factory=client_factory)
        if image:
            return CapturedLink(image, source_url, urlsplit(source_url).hostname or "", data.get("title") if isinstance(data.get("title"), str) else None)
    except (ExternalImageError, ValueError, TypeError):
        pass
    return None


def _capture_vtex_api(source_url: str, *, client_factory=None) -> CapturedLink | None:
    """Consulta o catálogo público VTEX quando a página /slug/p não expõe foto."""
    parsed = urlsplit(source_url)
    match = re.fullmatch(r"/([^/]+)/p/?", parsed.path)
    if not match:
        return None
    slug = match.group(1)
    api_url = urlunsplit((parsed.scheme, parsed.netloc, f"/api/catalog_system/pub/products/search/{slug}/p", "", ""))
    try:
        final_url, _, content, content_type = _fetch_public_resource(
            api_url, max_bytes=METADATA_MAX_BYTES, accept="application/json", client_factory=client_factory,
        )
        if content_type != "application/json":
            return None
        products = json.loads(content)
        if not isinstance(products, list) or not products:
            return None
        product = next((item for item in products if isinstance(item, dict) and item.get("linkText") == unquote(slug)), None)
        if product is None:
            return None
        items = product.get("items")
        if not isinstance(items, list):
            return None
        selected_sku = next((value for key, value in parse_qsl(parsed.query) if key.lower() in {"skuid", "idsku", "sku"}), None)
        if selected_sku:
            items = sorted(items, key=lambda item: str(item.get("itemId")) != selected_sku if isinstance(item, dict) else True)
        urls: list[str] = []
        for item in items:
            images = item.get("images") if isinstance(item, dict) else None
            if not isinstance(images, list):
                continue
            urls.extend(image["imageUrl"] for image in images if isinstance(image, dict) and isinstance(image.get("imageUrl"), str))
        image = _capture_candidate_images(urls, base_url=final_url, client_factory=client_factory)
        if image:
            title = product.get("productName")
            return CapturedLink(image, source_url, parsed.hostname or "", title[:180] if isinstance(title, str) else None)
    except (ExternalImageError, ValueError, TypeError):
        pass
    return None


def _capture_store_api(source_url: str, *, client_factory=None) -> CapturedLink | None:
    return _capture_mercadolivre_api(source_url, client_factory=client_factory) or _capture_vtex_api(source_url, client_factory=client_factory)


def _is_access_challenge(final_url: str, content: bytes) -> bool:
    path = urlsplit(final_url).path.lower()
    head = content[:2048].lower()
    return any(marker in path for marker in ("account-verification", "captcha", "challenge")) or any(
        marker in head for marker in (b"suspicious-traffic-frontend", b"cf-chl-", b"captcha-delivery")
    )


def fetch_fashion_link(url: str, *, client_factory=None) -> CapturedLink:
    """Aceita imagem, página de produto e API pública da loja quando disponível."""
    source_url = normalize_source_url(url)
    try:
        final_url, domain, content, content_type = _fetch_public_resource(
            source_url, max_bytes=MAX_UPLOAD_BYTES,
            accept="text/html,application/xhtml+xml,image/webp,image/png,image/jpeg", client_factory=client_factory,
        )
    except ExternalImageError:
        fallback = _capture_store_api(source_url, client_factory=client_factory)
        if fallback:
            return fallback
        raise
    if (content_type and content_type.startswith("image/")) or (content_type is None and _looks_like_supported_image(content)):
        return CapturedLink(RemoteImage(final_url, domain, content, content_type), final_url, domain, None)
    if _is_access_challenge(final_url, content):
        fallback = _capture_store_api(source_url, client_factory=client_factory)
        if fallback:
            return fallback
        raise ExternalImageError("A loja exigiu verificação de acesso e não liberou a foto do produto. Mantenha o link na mensagem e cole a imagem da peça com Ctrl+V, ou anexe uma captura de tela.")
    if content_type not in {"text/html", "application/xhtml+xml"} and not (content_type is None and content.lstrip().startswith(b"<")):
        raise ExternalImageError("O link não contém uma imagem ou página de produto reconhecível.")
    if len(content) > PAGE_MAX_BYTES:
        raise ExternalImageError("A página é grande demais para extrair uma imagem.")
    parser = _ProductImageParser()
    parser.feed(content.decode("utf-8", errors="replace"))
    image = _capture_candidate_images(
        parser.product_image_urls + parser.gallery_image_urls + parser.image_urls,
        base_url=final_url, client_factory=client_factory,
    )
    if image:
        return CapturedLink(image, final_url, domain, parser.title)
    fallback = _capture_store_api(source_url, client_factory=client_factory)
    if fallback:
        return fallback
    raise ExternalImageError("Não encontrei uma foto principal nesse link. Envie a URL direta da imagem ou anexe uma foto.")
