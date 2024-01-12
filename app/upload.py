import io
import re
import tempfile
import typing

import aiohttp
import interactions
from PIL import Image, UnidentifiedImageError

from app import config


class MyException(Exception):
    message: str

    def __init__(self, message, *args, **kwargs):
        super().__init__(message, *args, **kwargs)
        self.message = message

class NonCriticalException(MyException):
    pass

class CriticalException(MyException):
    pass


class UploadExtension(interactions.Extension):
    bot: interactions.Client
    config = config.Config()

    @interactions.listen()
    async def on_startup(self, event: interactions.api.events.Startup):
        self.bot = event.bot
        print("Upload Extension Loaded")

    @interactions.slash_command(
        name="upload",
        description="Upload Anonymously.",
        options=[
            interactions.SlashCommandOption(
                name="upload_channel",
                description="Select a channel to upload to",
                required=True,
                type=interactions.OptionType.STRING,
                choices=[
                    interactions.SlashCommandChoice("#upload-sharing", "#upload-sharing"),
                    interactions.SlashCommandChoice("#ost-sharing", "#ost-sharing"),
                    interactions.SlashCommandChoice("#misc-sharing", "#misc-sharing"),
                ],
            ),
            interactions.SlashCommandOption(
                name="image_attachment",
                description="Paste your image here!",
                required=True,
                type=interactions.OptionType.ATTACHMENT,
            ),
            interactions.SlashCommandOption(
                name="fulfilled_request_link",
                description="Paste the link (or id) to the fulfilled request here",
                required=False,
                type=interactions.OptionType.STRING,
            ),
        ],
    )
    async def upload_anonymously(
        self,
        ctx: interactions.SlashContext,
        upload_channel: str,
        image_attachment: interactions.Attachment,
        fulfilled_request_link: typing.Optional[str] = None,
    ):
        try:
            await self._upload_anonymously(ctx, upload_channel, image_attachment, fulfilled_request_link)
        except CriticalException as e:
            await ctx.send(f"**ERROR**\n{e.message}", ephemeral=True)
        except:
            await ctx.send(
                "**UNEXPEDTED ERROR**\n" +
                "Something went wrong. Please try /upload again later.",
                ephemeral=True
            )

    async def _upload_anonymously(
        self,
        ctx: interactions.SlashContext,
        upload_channel: str,
        image_attachment: interactions.Attachment,
        fulfilled_request_link: typing.Optional[str] = None,
    ):
        # form handler
        upload_form = self.generate_form()
        await ctx.send_modal(modal=upload_form)
        upload_form_ctx = await ctx.bot.wait_for_modal(upload_form, author=ctx.author)
        form_loading_message = await upload_form_ctx.send("processing your post...", ephemeral=True)

        # build and publish anonymous post
        description = upload_form_ctx.responses["description"]
        upload_channel_id = self.config.channel_ids[upload_channel]
        target_channel = self.config.channels[upload_channel_id]

        users_to_ping = ""
        if fulfilled_request_link:
            try:
                users_to_ping = await self.fetch_requested_users(fulfilled_request_link)
            except NonCriticalException as e:
                await ctx.send(e.message, ephemeral=True)
            except:
                await ctx.send(
                    "You provided a link to the request you fulfilled; however, something went wrong when parsing the link.\n"
                    "The upload process will continue without pinging anyone",
                    ephemeral=True
                )

        image_files: list[interactions.File] = list()
        try:
            await self.fetch_images(image_attachment, image_files)
        except NonCriticalException as e:
            await ctx.send(e.message, ephemeral=True)
        except CriticalException as e:
            return await ctx.send(e.message, ephemeral=True)
        except:
            raise CriticalException("Something went wrong while processing the image")

        message = f"{description}\n{users_to_ping}".strip()
        anonymous_post_message = await target_channel.send(
            content=message,
            files=image_files,
            suppress_embeds=True,
        )

        # delete form loading message
        try:
            await form_loading_message.delete(context=ctx)
        except interactions.errors.NotFound:
            pass

        # send confirmation message
        await ctx.send(
            "Your post has been submitted. Thank you for sharing!\n"
            f"Link: {anonymous_post_message.jump_url}",
            ephemeral=True,
            components=[
                interactions.ActionRow(
                    interactions.Button(
                        style=interactions.ButtonStyle.BLURPLE,
                        label="Edit Description",
                        custom_id="btn:edit_description",
                    ),
                    interactions.Button(
                        style=interactions.ButtonStyle.RED,
                        label="Delete Post",
                        custom_id="btn:delete_post",
                    )
                ),
            ]
        )

    def generate_form(self, value=""):
        return interactions.Modal(
            interactions.ParagraphText(
                label="Description",
                placeholder="Description of the upload",
                custom_id="description",
                required=True,
                value=value,
            ),
            title="Upload Anonymously",
        )

    async def get_anonymous_post(self, confirmation_callback_ctx: interactions.ComponentContext):
        message = confirmation_callback_ctx.message
        if not message:
            raise CriticalException("Failed to load the confirmation message")

        searchResult = re.search(r"(?P<url>https?://[^\s]+)", message.content)
        if not searchResult:
            raise CriticalException("Failed to extract link from confirmation message")

        link = searchResult.group("url")
        if not isinstance(link, str):
            raise CriticalException("Failed to extract link from confirmation message")

        try:
            channel_id = int(link.split("/")[-2])
            message_id = int(link.split("/")[-1])
        except:
            raise CriticalException("Loaded confirmation message, but failed to parse it")

        anonymous_post_message = await self.config.channels[channel_id].fetch_message(message_id)
        if not anonymous_post_message:
            raise CriticalException("Could not find your post; it may have been deleted by admins.")
        return anonymous_post_message

    @interactions.component_callback("btn:delete_post")
    async def delete_post(self, ctx: interactions.ComponentContext):
        try:
            anonymous_post_message = await self.get_anonymous_post(ctx)
        except CriticalException as e:
            return await ctx.send(e.message, ephemeral=True)
        except:
            return await ctx.send("An execpected error happened.", ephemeral=True)

        await anonymous_post_message.delete(context=ctx)
        await ctx.send("Your post has been deleted", ephemeral=True)
        if ctx.message:
            await ctx.message.delete(context=ctx)

    @interactions.component_callback("btn:edit_description")
    async def edit_discription(self, ctx: interactions.ComponentContext):
        try:
            anonymous_post_message = await self.get_anonymous_post(ctx)
        except CriticalException as e:
            return await ctx.send(e.message, ephemeral=True)
        except:
            return await ctx.send("An execpected error happened.", ephemeral=True)

        # form handler
        form_modal = self.generate_form(anonymous_post_message.content)
        await ctx.send_modal(modal=form_modal)
        form_ctx = await ctx.bot.wait_for_modal(
            form_modal,
            author=ctx.author,
        )

        # update description
        description = form_ctx.responses["description"]
        await anonymous_post_message.edit(content=description)
        await form_ctx.send("Description has been updated", ephemeral=True)

    async def fetch_requested_users(self, fulfilled_request_link: str) -> str:
        try:
            request_message_id = int(fulfilled_request_link.split("/")[-1])
        except:
            raise NonCriticalException(
                "You provided a link to the request you fulfilled; however, something went wrong while parsing the link.\n"
                "The upload process will continue without pinging anyone"
            )

        request_message = await self.config.upload_request_channel.fetch_message(request_message_id)
        if request_message is None:
            raise NonCriticalException(
                "You provided a link to the request you fulfilled; however, the message could not be found.\n"
                "The upload process will continue without pinging anyone"
            )

        pingme_reaction = next((reaction for reaction in request_message.reactions if reaction.emoji.name == "pingme"), None)
        if pingme_reaction is None:
            raise NonCriticalException(
                "You provided a link to the fulfilled request, but no one reacted to the message with a :pingme: emoji.\n"
                "The upload process will continue without pinging anyone"
            )

        users = await pingme_reaction.users().fetch()
        return "".join([u.mention for u in users])

    async def fetch_images(
        self,
        image_attachment: interactions.Attachment,
        image_files: list[interactions.File]
    ):
        async with aiohttp.ClientSession() as session:
            async with session.get(image_attachment.url) as res:
                if res.status != 200:
                    raise CriticalException(
                        "Failed to download the image you sent.\n"
                        "This shouldn't happend, try /upload again and see if it helps."
                    )
                original_image_raw = await res.read()

        original_image_filename = image_attachment.filename
        original_file = interactions.File(
            file=io.BytesIO(original_image_raw),
            file_name=original_image_filename,
            content_type=image_attachment.content_type,
        )
        image_files.append(original_file)

        try:
            original_image = Image.open(io.BytesIO(original_image_raw))
            if original_image.format in ["BMP"]:
                with tempfile.NamedTemporaryFile(delete=False) as f:
                    original_image.save(f.name, format="PNG")
                    preview_file = interactions.File(
                        file=f.name,
                        file_name="anonahira_generated_preview.png",
                        content_type="image/png",
                    )
                    image_files[0].file_name = f"original cover - {image_attachment.filename}"
                    image_files.insert(0, preview_file)
        except UnidentifiedImageError:
            raise NonCriticalException(
                "The file you uploaded is not recognized as an image.\n"
                "The upload process will continue but you might not see a preview image for your post."
            )
        except:
            raise NonCriticalException(
                "Discord does not support the format of your image, and something went wrong while generating a preview image for it.\n"
                "The upload process will continue but you might not see a preview image for your post."
            )


def setup(bot: interactions.Client):
    UploadExtension(bot)
