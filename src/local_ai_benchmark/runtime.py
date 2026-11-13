"""Questions to the Ollama server other than generation: its version, a model's details, and
which models are loaded and where."""

from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx
import ollama

DEFAULT_HOST = "http://127.0.0.1:11434"


def host() -> str:
    """The Ollama base URL, read from OLLAMA_HOST the way the Ollama client reads it."""
    raw = os.environ.get("OLLAMA_HOST", "").strip()
    if not raw:
        return DEFAULT_HOST
    if "://" not in raw:
        raw = f"http://{raw}"
    parts = urlsplit(raw)
    hostname = parts.hostname or "127.0.0.1"
    # A bind-all address in OLLAMA_HOST means the server listens locally; compare, never bind.
    if hostname in ("0.0.0.0", "::"):  # noqa: S104
        hostname = "127.0.0.1"
    if ":" in hostname:
        hostname = f"[{hostname}]"
    return f"{parts.scheme}://{hostname}:{parts.port or 11434}"


def is_loopback(address: str) -> bool:
    """Whether an IP address is this machine's loopback (127.0.0.0/8, ::1, or ::1-mapped)."""
    try:
        ip = ipaddress.ip_address(address.split("%")[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_loopback


def is_local(url: str) -> bool:
    """Whether a base URL points at this machine: `localhost` or a loopback address. Other
    names are not resolved, because resolving one could itself reach the network."""
    hostname = (urlsplit(url).hostname or "").lower()
    return hostname == "localhost" or is_loopback(hostname)


def server_version(timeout: float = 5.0) -> str:
    response = httpx.get(f"{host()}/api/version", timeout=timeout)
    response.raise_for_status()
    return str(response.json()["version"])


@dataclass(frozen=True)
class ModelDetails:
    name: str
    digest: str | None
    family: str | None
    parameter_size: str | None
    quantization: str | None
    format: str | None
    capabilities: tuple[str, ...]


def _same_model(listed: str | None, requested: str) -> bool:
    if listed is None:
        return False
    return listed == requested or listed == f"{requested}:latest"


def model_details(name: str) -> ModelDetails:
    """Describe a pulled model. Raises ollama.ResponseError (status 404) if it is not pulled."""
    shown = ollama.show(name)
    details = shown.details
    digest = next((m.digest for m in ollama.list().models if _same_model(m.model, name)), None)
    return ModelDetails(
        name=name,
        digest=digest,
        family=details.family if details else None,
        parameter_size=details.parameter_size if details else None,
        quantization=details.quantization_level if details else None,
        format=details.format if details else None,
        capabilities=tuple(shown.capabilities or ()),
    )


@dataclass(frozen=True)
class LoadedModel:
    name: str
    size_bytes: int
    vram_bytes: int
    context_length: int | None

    @property
    def gpu_share(self) -> float | None:
        """The share of the loaded model's memory that sits on the GPU, from 0 to 1."""
        return self.vram_bytes / self.size_bytes if self.size_bytes else None


def loaded_model(name: str) -> LoadedModel | None:
    """Where a loaded model sits, or None if it is not loaded."""
    for model in ollama.ps().models:
        if _same_model(model.model, name):
            return LoadedModel(
                name=name,
                size_bytes=int(model.size or 0),
                vram_bytes=int(model.size_vram or 0),
                context_length=model.context_length,
            )
    return None
