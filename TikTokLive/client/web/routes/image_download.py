from typing import Union

from httpx import Response

from TikTokLive.client.web.web_base import ClientRoute
from TikTokLive.proto import Image


class ImageFetchRoute(ClientRoute):
    """
    Fetch an image from the TikTok CDN

    """

    async def __call__(self, image: Union[str, Image]) -> bytes:
        """
        Fetch the image from TikTok

        :param image: A betterproto Image message
        :return:

        """

        image_url: str = image.url_list[0] if isinstance(image, Image) else image
        response: Response = await self._web.get_response(url=image_url)
        return response.read()
