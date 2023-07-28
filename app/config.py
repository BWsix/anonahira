import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    dev: bool
    bot_token: str
    guild_id: int
    upload_sharing_channel_id: int
    ost_sharing_channel_id: int
    misc_sharing_channel_id: int
    upload_request_channel_id: int

    def __init__(self):
        config = os.environ

        self.dev = "DEV" in config

        assert "TOKEN" in config
        if "TOKEN" in config:
            self.bot_token = config["TOKEN"]

        assert "GUILD_ID" in config
        self.guild_id = int(config["GUILD_ID"])

        assert "UPLOAD_SHARING_CHANNEL_ID" in config
        self.upload_sharing_channel_id = int(
            config["UPLOAD_SHARING_CHANNEL_ID"])

        assert "OST_SHARING_CHANNEL_ID" in config
        self.ost_sharing_channel_id = int(config["OST_SHARING_CHANNEL_ID"])

        assert "MISC_SHARING_CHANNEL_ID" in config
        self.misc_sharing_channel_id = int(config["MISC_SHARING_CHANNEL_ID"])

        assert "UPLOAD_REQUEST_CHANNEL_ID" in config
        self.upload_request_channel_id = int(
            config["UPLOAD_REQUEST_CHANNEL_ID"])

    @property
    def channels(self):
        return {
            "#upload-sharing": self.upload_sharing_channel_id,
            "#ost-sharing": self.ost_sharing_channel_id,
            "#misc-sharing": self.misc_sharing_channel_id,
            "#upload-request": self.upload_request_channel_id,
        }
