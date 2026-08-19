"""Exceptions raised by activity providers. These are not HTTP responses."""


class ProviderNotConfiguredError(Exception):
    """The selected provider cannot run until official credentials exist."""

    def __init__(self, provider: str, message: str) -> None:
        self.provider = provider
        self.message = message
        super().__init__(message)


class ProviderActivityNotFoundError(Exception):
    """The remote provider has no activity with this id for the user."""

    def __init__(self, provider: str, provider_activity_id: str) -> None:
        self.provider = provider
        self.provider_activity_id = provider_activity_id
        super().__init__(f"{provider} activity {provider_activity_id} was not found")
