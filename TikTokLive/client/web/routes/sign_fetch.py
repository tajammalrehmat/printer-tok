import enum
import os
from http.cookies import SimpleCookie
from typing import Optional

import httpx
from httpx import Response

from TikTokLive.client.web.web_base import ClientRoute, TikTokHTTPClient
from TikTokLive.client.web.web_settings import WebDefaults, CLIENT_NAME
from TikTokLive.proto import WebcastResponse


class SignAPIError(RuntimeError):
    """
    Thrown when a fetch to the Sign API fails for one reason or another

    """

    class ErrorReason(enum.Enum):
        """
        Possible failure reasons

        """

        RATE_LIMIT = 1
        CONNECT_ERROR = 2
        EMPTY_PAYLOAD = 3
        EMPTY_COOKIES = 5
        SIGN_NOT_200 = 4

    def __init__(
            self,
            reason: ErrorReason,
            *args: str
    ):
        """
        Initialize a sign API Error class

        :param reason: The reason for the error
        :param args: Additional error arguments passed to the super-class

        """

        self.reason = reason
        args = list(args)
        args.insert(0, f"[{reason.name}]")
        super().__init__(" ".join(args))


class SignatureRateLimitError(SignAPIError):
    """
    Thrown when a user hits the Sign API limit

    """

    @classmethod
    def format_sign_server_message(cls, message: str) -> str:
        """
        Format the sign server message
        """

        message = message.strip()
        msg_len: int = len(message)
        header_text: str = "SIGN SERVER MESSAGE"
        header_len: int = (msg_len - len(header_text)) // 2
        padding_len: int = int(bool((msg_len - len(header_text)) % 2))

        # Center header text in header
        footer: str = "+" + "-" * (msg_len + 2) + "+"
        header: str = "+" + "-" * header_len + " " + header_text + " " + "-" * (header_len + padding_len) + "+"
        message: str = "| " + message + " |"

        return f"\n\t|\n\t{header}\n\t{message}\n\t{footer}"

    def __init__(self, retry_after: int, reset_time: int, api_message: Optional[str], *args):
        """
        Constructor for signature rate limit

        :param retry_after: How long to wait until the next attempt
        :param reset_time: The unix timestamp for when the client can request again
        :param api_message: The message provided by the API
        :param args: Default RuntimeException *args
        :param kwargs: Default RuntimeException **kwargs

        """

        # Message provided by the API
        euler_msg: Optional[str] = self.format_sign_server_message(api_message) if api_message else None

        self._retry_after: int = retry_after
        self._reset_time: int = reset_time

        _args = list(args)

        if euler_msg:
            _args.append(euler_msg)

        _args[0] = str(args[0]) % self.retry_after

        super().__init__(SignAPIError.ErrorReason.RATE_LIMIT, *_args)

    @property
    def retry_after(self) -> int:
        """
        How long to wait until the next attempt

        """

        return self._retry_after

    @property
    def reset_time(self) -> int:
        """
        The unix timestamp for when the client can request again

        """

        return self._reset_time


class SignFetchRoute(ClientRoute):
    """
    Call the signature server to receive the TikTok websocket URL

    """

    def __init__(self, web: TikTokHTTPClient, sign_api_key: Optional[str]):

        super().__init__(web)
        self._sign_api_key: Optional[str] = sign_api_key

    async def __call__(self) -> WebcastResponse:
        """
        Call the method to get the first WebcastResponse to use to upgrade to websocket

        :return: The WebcastResponse forwarded from the sign server proxy

        """

        try:
            response: Response = await self._web.get_response(
                url=WebDefaults.tiktok_sign_url + "/webcast/fetch/",
                extra_params={'client': CLIENT_NAME, 'apiKey': self._sign_api_key}
            )
        except httpx.ConnectError as ex:
            raise SignAPIError(
                SignAPIError.ErrorReason.CONNECT_ERROR,
                "Failed to connect to the sign server due to an httpx.ConnectError!"
            ) from ex

        data: bytes = await response.aread()

        if response.status_code == 429:
            data_json = response.json()
            server_message: Optional[str] = None if os.environ.get('SIGN_SERVER_MESSAGE_DISABLED') else data_json.get("message")
            limit_label: str = f"({data_json['limit_label']}) " if data_json.get("limit_label") else ""

            raise SignatureRateLimitError(
                response.headers.get("RateLimit-Reset"),
                response.headers.get("X-RateLimit-Reset"),
                server_message,
                (
                    f"{limit_label}Too many connections started, try again in %s seconds."
                )

            )

        elif not data:
            raise SignAPIError(
                SignAPIError.ErrorReason.EMPTY_PAYLOAD,
                f"Sign API returned an empty request. Are you being detected by TikTok?"
            )

        elif not response.status_code == 200:
            raise SignAPIError(
                SignAPIError.ErrorReason.SIGN_NOT_200,
                f"Failed request to Sign API with status code {response.status_code} and payload \"{response.read()}\"."
            )

        webcast_response: WebcastResponse = WebcastResponse().parse(response.read())

        # Update web params & cookies
        self._update_tiktok_cookies(response)
        self._web.params["cursor"] = webcast_response.cursor
        self._web.params["internal_ext"] = webcast_response.internal_ext

        return webcast_response

    def _update_tiktok_cookies(self, response: Response) -> None:
        """
        Update the cookies in the cookie jar from the sign server response

        :param response: The `httpx.Response` to parse for cookies
        :return: None

        """

        jar: SimpleCookie = SimpleCookie()
        cookies_header: Optional[str] = response.headers.get("X-Set-TT-Cookie")

        if not cookies_header:
            raise SignAPIError(
                SignAPIError.ErrorReason.EMPTY_COOKIES,
                "Sign server did not return cookies!"
            )

        jar.load(cookies_header)

        for cookie, morsel in jar.items():
            self._web.cookies.set(cookie, morsel.value, ".tiktok.com")
