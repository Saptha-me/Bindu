from typing import Any

class ProxyEntry:
    name: str
    port: int

    def __init__(self, name: str, port: int) -> None: ...

class NetworkConfig:
    proxies: list[ProxyEntry] | None

    def __init__(self, proxies: list[ProxyEntry] | None = ...) -> None: ...

class LifecycleConfig:
    auto_suspend_timeout: int | None

    def __init__(self, auto_suspend_timeout: int | None = ...) -> None: ...

class BoxConfig:
    vcpu: int | None
    memory: str | None
    disk: str | None
    lifecycle: LifecycleConfig | None
    network: NetworkConfig | None

    def __init__(
        self,
        *,
        vcpu: int | None = ...,
        memory: str | None = ...,
        disk: str | None = ...,
        lifecycle: LifecycleConfig | None = ...,
        network: NetworkConfig | None = ...,
        **kwargs: Any,
    ) -> None: ...
