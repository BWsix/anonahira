import app.config
import typing
import asyncio
import interactions

config = app.config.Config()


@interactions.listen()
async def on_startup(event: interactions.api.events.Startup):
    bot = typing.cast(interactions.Client, event.bot)
    print(f"Bot: {bot.user.username}")

    guild = await bot.fetch_guild(config.guild_id)
    assert guild
    config.guild = guild
    print(f"Server: {guild.name}")

    for channel_name, channel_id in config.channel_ids.items():
        print(f"Searching for {channel_name}")
        channel = guild.get_channel(channel_id)
        assert isinstance(channel, interactions.GuildText)
        config.set_channel(channel_name, channel)
        print(f"...Found {channel_name}.")

    print("Searching for :pingme:")
    emojis = await guild.fetch_all_custom_emojis()
    assert "pingme" in [emoji.name for emoji in emojis]
    print("...Found :pingme:")


@interactions.listen()
async def on_disconnect(event: interactions.api.events.Disconnect):
    event.bot.ws.close()
    print("Bot is now offline")


async def startup():
    bot = interactions.Client(
        send_command_tracebacks=config.dev,
        send_not_ready_messages=True,
    )
    bot.load_extension("app.upload")
    await bot.astart(config.bot_token)

if __name__ == "__main__":
    asyncio.run(startup())
