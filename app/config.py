import os
import typing
import dotenv
import interactions

def singleton(cls):
    instances = {}
    def wrapper(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return wrapper

@singleton
class Config:
    dev: bool
    bot_token: str

    guild_id: int
    upload_sharing_channel_id: int
    ost_sharing_channel_id: int
    misc_sharing_channel_id: int
    upload_request_channel_id: int

    guild: interactions.Guild
    upload_sharing_channel = typing.cast(interactions.GuildText, None)
    ost_sharing_channel = typing.cast(interactions.GuildText, None)
    misc_sharing_channel = typing.cast(interactions.GuildText, None)
    upload_request_channel = typing.cast(interactions.GuildText, None)

    def __init__(self):
        dotenv.load_dotenv()

        self.dev = "DEV" in os.environ

        assert "TOKEN" in os.environ
        self.bot_token = os.environ["TOKEN"]

        assert "GUILD_ID" in os.environ
        self.guild_id = int(os.environ["GUILD_ID"])

        assert "UPLOAD_SHARING_CHANNEL_ID" in os.environ
        self.upload_sharing_channel_id = int(os.environ["UPLOAD_SHARING_CHANNEL_ID"])

        assert "OST_SHARING_CHANNEL_ID" in os.environ
        self.ost_sharing_channel_id = int(os.environ["OST_SHARING_CHANNEL_ID"])

        assert "MISC_SHARING_CHANNEL_ID" in os.environ
        self.misc_sharing_channel_id = int(os.environ["MISC_SHARING_CHANNEL_ID"])

        assert "UPLOAD_REQUEST_CHANNEL_ID" in os.environ
        self.upload_request_channel_id = int(os.environ["UPLOAD_REQUEST_CHANNEL_ID"])

    @property
    def channel_ids(self):
        return {
            "#upload-sharing": self.upload_sharing_channel_id,
            "#ost-sharing": self.ost_sharing_channel_id,
            "#misc-sharing": self.misc_sharing_channel_id,
            "#upload-request": self.upload_request_channel_id,
        }

    @property
    def channels(self):
        return {
            self.upload_sharing_channel_id: self.upload_sharing_channel,
            self.ost_sharing_channel_id: self.ost_sharing_channel,
            self.misc_sharing_channel_id: self.misc_sharing_channel,
            self.upload_request_channel_id: self.upload_request_channel,
        }

    def set_channel(self, channel_name: str, channel: interactions.GuildText):
        if channel_name == "#upload-sharing":
            self.upload_sharing_channel = channel
        if channel_name == "#ost-sharing":
            self.ost_sharing_channel = channel
        if channel_name == "#misc-sharing":
            self.misc_sharing_channel = channel
        if channel_name == "#upload-request":
            self.upload_request_channel = channel

