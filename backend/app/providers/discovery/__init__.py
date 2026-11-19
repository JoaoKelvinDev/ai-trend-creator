"""Discovery providers package."""

from backend.app.providers.discovery.base import DiscoveryProvider, DiscoveryResult
from backend.app.providers.discovery.rss import RSSDiscoveryProvider
from backend.app.providers.discovery.manual import ManualDiscoveryProvider
from backend.app.providers.discovery.mock import MockDiscoveryProvider
from backend.app.providers.discovery.youtube import YouTubeDiscoveryProvider

__all__ = [
    "DiscoveryProvider",
    "DiscoveryResult",
    "RSSDiscoveryProvider",
    "ManualDiscoveryProvider",
    "MockDiscoveryProvider",
    "YouTubeDiscoveryProvider",
]