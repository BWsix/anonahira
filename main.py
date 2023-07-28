import app.config
import asyncio
import interactions

config = app.config.Config()


@interactions.listen()
async def on_startup(event: interactions.api.events.Startup):
    bot_name = event.bot.user.username
    print(f"Bot: {bot_name}")

    guild = await event.bot.fetch_guild(config.guild_id)
    assert guild
    print(f"Server: {guild.name}")

    assert guild.get_channel(config.channels["#upload-request"])
    print("Found #upload-request")
    assert guild.get_channel(config.channels["#upload-sharing"])
    print("Found #upload-sharing")
    assert guild.get_channel(config.channels["#misc-sharing"])
    print("Found #misc-sharing")
    assert guild.get_channel(config.channels["#upload-request"])
    print("Found #upload-request")

    emojis = await guild.fetch_all_custom_emojis()
    assert "pingme" in [emoji.name for emoji in emojis]
    print("Found :pingme:")


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
