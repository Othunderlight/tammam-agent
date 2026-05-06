"""
Integrations Module - Channel-specific integrations
"""

from integrations.telegram import webhook
from integrations.whatsapp import client

__all__ = ["webhook", "client"]
