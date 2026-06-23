"""
Подключение к порталу ModusBI (single-instance per process).

В этой модели **один процесс = один портал**. Конфигурация задаётся через
env vars (`MODUSBI_URL`, `MODUSBI_USERNAME`, `MODUSBI_PASSWORD`) при старте
сервера. Multi-portal сценарии решаются на уровне MCP-клиента — несколько
записей `mcpServers`, каждая со своими env vars (см. `INSTALL.md`).

Конфигурация хранится только в env vars: нет файла `instances.json`,
нет понятия «активный инстанс» — одно поле `_instance: Instance`.
"""

import asyncio
import json
import time
import base64
import httpx
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from .exceptions import AuthenticationError


def _http_error_message(response) -> str:
    """Сообщение для APIError на non-200: HTTP-код + причина из тела портала.

    Без этого все инструменты показывали бы голое «HTTP 400» — реальное
    `message` портала терялось бы.
    """
    base = f"Ошибка API: HTTP {response.status_code}"
    try:
        body_msg = (response.json().get("message") or "")[:300]
    except Exception:
        body_msg = (response.text or "")[:200].strip()
    if body_msg:
        from .exceptions import mask_sensitive
        return f"{base} — {mask_sensitive(body_msg)}"
    return base


@dataclass
class Instance:
    """Представляет подключение к порталу ModusBI."""

    name: str
    base_url: str
    username: str
    password: str
    description: str = ""
    token: str | None = None
    token_exp: int = 0
    is_connected: bool = False

    @property
    def login_url(self) -> str:
        """URL для авторизации."""
        return f"{self.base_url.rstrip('/')}/v1/api/login"

    @property
    def api_base_url(self) -> str:
        """Базовый URL для API."""
        return f"{self.base_url.rstrip('/')}/v1/api"

    def get_api_url(self, object_name: str, object_id: int | None = None) -> str:
        """Формирует URL для API вызова."""
        if object_id is not None:
            return f"{self.api_base_url}/{object_name}/{object_id}"
        return f"{self.api_base_url}/{object_name}"

    def is_token_valid(self) -> bool:
        """Проверяет валидность токена."""
        return self.token is not None and self.token_exp > time.time()

    def to_dict(self, include_token: bool = False) -> dict:
        """Преобразует в dict для сериализации."""
        result = {
            "name": self.name,
            "base_url": self.base_url,
            "username": self.username,
            "description": self.description,
            "is_connected": self.is_connected
        }
        if include_token and self.token:
            result["token_valid"] = self.is_token_valid()
        return result


class InstanceManager:
    """
    Управляет единственным подключением к порталу.

    Создаётся в `server_lifespan` из env vars; tools получают
    `InstanceClient` через `get_client()`.

    Example:
        instance = Instance(name="prod", base_url=..., username=..., password=...)
        manager = InstanceManager(instance)
        await manager.authenticate()
        client = await manager.get_client()
    """

    def __init__(self, instance: Instance):
        self._instance = instance
        # Lock для предотвращения concurrent re-auth когда несколько tool
        # calls параллельно получают 401: первый ставит lock, обновляет
        # токен; остальные ждут, потом видят свежий токен и не делают
        # redundant POST /login.
        self._auth_lock = asyncio.Lock()
        # Один общий httpx клиент с connection pooling — соединения переиспользуются
        # вместо TCP+TLS handshake на каждый запрос. Отдельный lock от auth_lock
        # потому что _do_authenticate под auth_lock зовёт _http_client → reentrancy
        # на одном lock'е заклинит asyncio.Lock (не reentrant).
        self._http: httpx.AsyncClient | None = None
        self._http_lock = asyncio.Lock()

    async def _http_client(self) -> httpx.AsyncClient:
        """Возвращает shared httpx.AsyncClient. Lazy-init под отдельным lock'ом."""
        if self._http is None:
            async with self._http_lock:
                if self._http is None:  # double-check
                    self._http = httpx.AsyncClient(
                        timeout=30.0,
                        limits=httpx.Limits(
                            max_connections=10,
                            max_keepalive_connections=5,
                            keepalive_expiry=30.0,
                        ),
                    )
        return self._http

    async def aclose(self) -> None:
        """Lifespan finalizer — закрыть pool при остановке сервера. Идемпотентен."""
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    async def authenticate(self) -> None:
        """Авторизуется в портале (получает JWT)."""
        await self._authenticate(self._instance)

    def get_active(self) -> Instance:
        """Возвращает единственный инстанс."""
        return self._instance

    def list(self) -> list[dict]:
        """Возвращает список из 1 элемента (для совместимости с tools/list).

        `is_active` отражает реальное состояние авторизации, а не
        захардкожен — после auth failure поле будет False.
        """
        return [
            {
                **self._instance.to_dict(include_token=True),
                "is_active": self._instance.is_token_valid(),
            }
        ]

    async def get_client(self) -> "InstanceClient":
        """Возвращает клиент. Перезапросит токен если истёк.

        Передаёт shared httpx pool + `_authenticate` callback. При 401
        client делает silent retry с обновлённым токеном (`asyncio.Lock`
        защищает от concurrent re-auth).
        """
        if not self._instance.is_token_valid():
            await self._authenticate(self._instance)
        http = await self._http_client()
        return InstanceClient(
            self._instance,
            http_client=http,
            reauth_callback=self._authenticate,
        )

    async def _authenticate(self, instance: Instance) -> None:
        """
        Авторизуется на портале (с lock для concurrent safety).

        Если другой call уже обновил токен пока мы ждали lock —
        не делаем redundant POST /login.

        Args:
            instance: Инстанс для авторизации
        """
        async with self._auth_lock:
            # double-check: пока ждали lock, другой call мог уже обновить токен
            if instance.is_token_valid():
                return
            await self._do_authenticate(instance)

    async def _do_authenticate(self, instance: Instance) -> None:
        """Реальный POST /login. Вызывается под `_auth_lock`."""
        client = await self._http_client()
        try:
            response = await client.post(
                instance.login_url,
                json={
                    "object": {"name": "login"},
                    "command": {"name": "create"},
                    "data": [{
                        "username": instance.username,
                        "password": instance.password,
                        "pcid": 1
                    }]
                },
                headers={"Content-Type": "application/json"},
                timeout=30.0
            )
        except httpx.RequestError as e:
            raise AuthenticationError(
                f"Ошибка подключения к {instance.name}: {e}",
                details={"url": instance.login_url, "instance": instance.name}
            )

        if response.status_code != 200:
            raise AuthenticationError(
                f"Ошибка авторизации на {instance.name}: HTTP {response.status_code}",
                details={"status_code": response.status_code, "instance": instance.name}
            )

        data = response.json()
        if data.get("status") != 200:
            raise AuthenticationError(
                f"Ошибка авторизации на {instance.name}: {data.get('message')}",
                details={"api_status": data.get("status"), "instance": instance.name}
            )

        instance.token = data["data"]["token"]
        instance.is_connected = True

        # Парсим exp из JWT
        try:
            payload = instance.token.split('.')[1]
            payload += '=' * (4 - len(payload) % 4)
            jwt_data = json.loads(base64.urlsafe_b64decode(payload))
            instance.token_exp = jwt_data.get("exp", int(time.time()) + 86400)
        except Exception:
            instance.token_exp = int(time.time()) + 86400


class InstanceClient:
    """
    API клиент для конкретного инстанса.

    Example:
        client = await manager.get_client()
        result = await client.api_call("reports", "get", object_id=35)
    """

    def __init__(
        self,
        instance: Instance,
        *,
        http_client: httpx.AsyncClient | None = None,
        reauth_callback: Callable[[Instance], Awaitable[None]] | None = None,
    ):
        """
        Args:
            instance: portal connection
            http_client: shared httpx client from InstanceManager. If None
                (legacy/test mode), every request creates a per-call client.
            reauth_callback: async callable invoked on 401 to refresh token.
                Typically `InstanceManager._authenticate` (with built-in lock).
                If None, 401 → raise without retry (legacy behavior).
        """
        self._instance = instance
        self._http = http_client
        self._reauth = reauth_callback

    async def _try_reauth(self) -> bool:
        """Re-auth via callback. Returns True if success, False if no callback."""
        if self._reauth is None:
            return False
        await self._reauth(self._instance)
        return self._instance.is_token_valid()

    async def raw_post(self, url: str, *, json=None, headers=None, timeout=30.0):
        """Public helper: POST через shared client (если есть) или per-call (legacy).

        Используется в query_execute и других местах где нужны сырые HTTP-вызовы
        вне стандартной ModusBI API обёртки {object, command, data}. Все equivalent
        per-call `async with httpx.AsyncClient()` callsites должны использовать это.
        """
        if self._http is not None:
            return await self._http.post(url, json=json, headers=headers, timeout=timeout)
        async with httpx.AsyncClient() as client:
            return await client.post(url, json=json, headers=headers, timeout=timeout)

    async def raw_get(self, url: str, *, headers=None, timeout=30.0):
        """Public helper: GET через shared client (если есть) или per-call (legacy)."""
        if self._http is not None:
            return await self._http.get(url, headers=headers, timeout=timeout)
        async with httpx.AsyncClient() as client:
            return await client.get(url, headers=headers, timeout=timeout)

    # Backward-compat aliases for the public raw_* helpers.
    _post = raw_post
    _get = raw_get

    @property
    def instance(self) -> Instance:
        """Возвращает связанный инстанс."""
        return self._instance

    @property
    def base_url(self) -> str:
        """Возвращает base_url инстанса."""
        return self._instance.base_url

    async def api_call(
        self,
        object_name: str,
        command_name: str,
        object_id: int | None = None,
        data: list | None = None,
        retry: bool = True
    ) -> dict[str, Any]:
        """
        Универсальный метод для вызова ModusBI API.

        Args:
            object_name: Имя объекта API (reports, datasets, etc.)
            command_name: Имя команды (get, update, create, delete, etc.)
            object_id: ID объекта (опционально)
            data: Данные для отправки (опционально)
            retry: Повторить при 401 ошибке

        Returns:
            Ответ API в виде dict
        """
        # Note: no early-return on empty token. If token was reset between
        # parallel api_calls, the request will get 401 → silent retry will
        # re-auth (this is the right behavior; an early raise would be a
        # race-condition bug for concurrent calls).

        # Формируем URL и payload
        if object_name == "recordsets" and command_name == "create":
            # recordsets.create uses direct params, not wrapped in {object, command, data}
            # URL: /v1/api/recordsets/{dataset_id}
            # Body: {"select": [...], "group": [], "where": [], ...}
            api_url = self._instance.get_api_url(object_name, object_id)
            # data[0] contains the query params directly
            payload = data[0] if data and isinstance(data, list) and data else {}
        else:
            # Standard ModusBI API structure
            payload: dict[str, Any] = {
                "object": {"name": object_name},
                "command": {"name": command_name}
            }

            if object_id is not None:
                payload["object"]["id"] = object_id

            if data is not None:
                payload["data"] = data

            if object_name == "recordsets":
                api_url = self._instance.get_api_url(object_name, object_id)
                if "id" in payload["object"]:
                    del payload["object"]["id"]
            else:
                api_url = self._instance.get_api_url(object_name)

        try:
            response = await self._post(
                api_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._instance.token}"
                },
            )
        except httpx.RequestError as e:
            from .exceptions import APIError
            raise APIError(f"Ошибка подключения: {e}", details={"url": api_url})

        if response.status_code == 401:
            # Token expired or invalid. Reset state and try re-auth once.
            self._instance.token = None
            self._instance.token_exp = 0
            self._instance.is_connected = False
            if not retry:
                raise AuthenticationError(
                    f"Auth failed after refresh for {self._instance.name}",
                    details={"instance": self._instance.name}
                )
            if not await self._try_reauth():
                raise AuthenticationError(
                    f"Token expired and re-auth not configured for {self._instance.name}",
                    details={"instance": self._instance.name}
                )
            # Retry the request once with the fresh token
            return await self.api_call(
                object_name, command_name,
                object_id=object_id, data=data,
                retry=False,
            )

        if response.status_code != 200:
            from .exceptions import APIError
            # Пробрасываем причину из тела ответа портала — иначе пользователь
            # видит голое «HTTP 400» вместо реального сообщения (бьёт ВСЕ tools).
            raise APIError(
                _http_error_message(response),
                status_code=response.status_code
            )

        return response.json()

    async def api_get(
        self,
        path: str,
        retry: bool = True
    ) -> dict[str, Any]:
        """
        HTTP GET для REST-style эндпоинтов (например /v1/api/geodata).

        Args:
            path: Путь относительно api_base_url (например "geodata")
            retry: Повторить при 401 ошибке

        Returns:
            Ответ API в виде dict
        """
        # See api_call: no early-return on empty token (race-safe with retry).

        api_url = f"{self._instance.api_base_url}/{path}"

        try:
            response = await self._get(
                api_url,
                headers={
                    "Authorization": f"Bearer {self._instance.token}"
                },
            )
        except httpx.RequestError as e:
            from .exceptions import APIError
            raise APIError(f"Ошибка подключения: {e}", details={"url": api_url})

        if response.status_code == 401:
            self._instance.token = None
            self._instance.token_exp = 0
            self._instance.is_connected = False
            if not retry:
                raise AuthenticationError(
                    f"Auth failed after refresh for {self._instance.name}",
                    details={"instance": self._instance.name}
                )
            if not await self._try_reauth():
                raise AuthenticationError(
                    f"Token expired and re-auth not configured for {self._instance.name}",
                    details={"instance": self._instance.name}
                )
            return await self.api_get(path, retry=False)

        if response.status_code != 200:
            from .exceptions import APIError
            raise APIError(
                _http_error_message(response),
                status_code=response.status_code
            )

        return response.json()
