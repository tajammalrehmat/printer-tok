from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Type, Union, Optional

from TikTokLive.events.base_event import BaseEvent
from TikTokLive.events.proto_events import SocialEvent, ControlEvent
from TikTokLive.proto import WebcastResponseMessage


class WebsocketResponseEvent(WebcastResponseMessage, BaseEvent):
    """
    Triggered when any event is received from the WebSocket

    """


class UnknownEvent(WebsocketResponseEvent):
    """
    Triggered when a Webcast message is received that is NOT tracked by TikTokLive yet.

    """

    @property
    def bytes(self) -> bytes:
        return base64.b64decode(self.payload)


@dataclass()
class ConnectEvent(BaseEvent):
    """
    Manually thrown whenever a connection is started

    """

    unique_id: str
    room_id: int


class DisconnectEvent(BaseEvent):
    """
    Thrown when disconnecting from a stream

    """


class LiveEndEvent(ControlEvent):
    """
    Thrown when the stream ends

    """


class LivePauseEvent(ControlEvent):
    """
    Thrown when the stream is paused

    """


class LiveUnpauseEvent(ControlEvent):
    """
    Thrown when a paused stream is unpaused

    """


class FollowEvent(SocialEvent):
    """
    A SocialEvent, but we give it its own class for clarity's sake.

    """


class ShareEvent(SocialEvent):
    """
    A SocialEvent, but we give it its own class for clarity's sake.

    """

    @property
    def users_joined(self) -> Optional[int]:
        """
        The number of people that have joined the stream from the share

        :return: The number of people that have joined

        """

        try:
            display_text: str = self.common.display_text.key
            return int(display_text.split("pm_mt_guidance_viewer_")[1].split("_share")[0])
        except IndexError:
            return None


CustomEvent: Type = Union[
    WebsocketResponseEvent,
    UnknownEvent,
    ConnectEvent,
    FollowEvent,
    ShareEvent,
    LiveEndEvent,
    LivePauseEvent,
    LiveUnpauseEvent,
    DisconnectEvent
]

__all__ = [
    "WebsocketResponseEvent",
    "UnknownEvent",
    "ConnectEvent",
    "FollowEvent",
    "ShareEvent",
    "LiveEndEvent",
    "LivePauseEvent",
    "LiveUnpauseEvent",
    "CustomEvent",
    "DisconnectEvent"
]
