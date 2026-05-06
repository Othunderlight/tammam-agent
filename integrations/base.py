"""
Base Integration Class

Abstract base class for all channel integrations.
Each messaging platform (Telegram, WhatsApp, Slack, etc.) 
should implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class IncomingMessage:
    """
    Normalized incoming message format.
    
    All integrations convert their platform-specific messages
    to this format for uniform processing.
    """
    message_id: str
    channel: str
    sender_id: str
    sender_name: Optional[str]
    text: str
    raw: dict[str, Any]  # Original platform-specific data


@dataclass
class OutgoingMessage:
    """
    Normalized outgoing message format.
    
    Converted to platform-specific format before sending.
    """
    recipient_id: str
    text: str
    buttons: Optional[list[dict[str, str]]] = None  # [{"label": "...", "action": "..."}]
    attachments: Optional[list[str]] = None


class BaseIntegration(ABC):
    """
    Base class for all channel integrations.
    
    Each integration must implement:
    - handle_webhook: Process incoming webhook requests
    - send_message: Send a message to the user
    - parse_message: Convert platform message to IncomingMessage
    - format_message: Convert OutgoingMessage to platform format
    """
    
    channel_name: str = "base"
    
    @abstractmethod
    async def handle_webhook(self, request_data: dict[str, Any]) -> IncomingMessage:
        """
        Handle incoming webhook from the platform.
        
        Args:
            request_data: Raw webhook payload
            
        Returns:
            IncomingMessage: Normalized message
        """
        pass
    
    @abstractmethod
    async def send_message(self, message: OutgoingMessage) -> bool:
        """
        Send a message to the user via the platform.
        
        Args:
            message: Message to send
            
        Returns:
            bool: Success status
        """
        pass
    
    def parse_message(self, raw_data: dict[str, Any]) -> IncomingMessage:
        """
        Parse platform-specific message to IncomingMessage.
        
        Args:
            raw_data: Raw message data
            
        Returns:
            IncomingMessage: Normalized message
        """
        # TODO: Implement in subclass
        pass
    
    def format_message(self, message: OutgoingMessage) -> dict[str, Any]:
        """
        Format OutgoingMessage to platform-specific format.
        
        Args:
            message: Normalized message
            
        Returns:
            dict: Platform-specific payload
        """
        # TODO: Implement in subclass
        pass
