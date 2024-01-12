import io
import re
import tempfile
import typing

import aiohttp
import interactions
from PIL import Image, UnidentifiedImageError

from app import config

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
                description="Paste the link to the fulfilled request here",
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
        # form handler
        upload_form = self.get_description_form_modal()
        await ctx.send_modal(modal=upload_form)
        upload_form_ctx = await ctx.bot.wait_for_modal(upload_form, author=ctx.author)
        form_loading_message = await upload_form_ctx.send("Anonahira is processing your post...", ephemeral=True)

        # build and publish anonymous post
        description = upload_form_ctx.responses["description"]
        upload_channel_id = self.config.channel_ids[upload_channel]
        target_channel = self.config.channels[upload_channel_id]

        users_to_ping = ""
        if fulfilled_request_link:
            try:
                users_to_ping = await self.fetch_requested_users(fulfilled_request_link)
            except:
                await ctx.send("Invalid fulfilled request link provided, will skip pinging users.", ephemeral=True)
                return

        async with aiohttp.ClientSession() as session:
            async with session.get(image_attachment.url) as res:
                if res.status != 200:
                    raise Exception("Failed to download image")
                original_image_raw = await res.read()

        image_files = []
        original_image = Image.new("L", (1, 1))
        original_image_filename = image_attachment.filename
        try:
            original_image = Image.open(io.BytesIO(original_image_raw))
            if original_image.format in ["BMP"]:
                with tempfile.NamedTemporaryFile(delete=False) as f:
                    original_image.save(f.name, format="PNG")
                    preveiw_file = interactions.File(
                        file=f.name,
                        file_name="generated_preview.png",
                        content_type="image/png",
                    )
                    image_files.append(preveiw_file)
                    original_image_filename = f"original_image_file - {image_attachment.filename}"
        except UnidentifiedImageError:
            original_image_filename = f"no_preview - {image_attachment.filename}"

        original_file = interactions.File(
            file=io.BytesIO(original_image_raw),
            file_name=original_image_filename,
            content_type=image_attachment.content_type,
        )
        image_files.append(original_file)

        anonymous_post_message = await target_channel.send(
            content=f"{description}\n{users_to_ping}",
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
            "The post has been uploaded to the server.\n" +
                f"Link: {anonymous_post_message.jump_url}",
            ephemeral=True,
            components=[interactions.ActionRow(
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
            )],
        )

    def get_description_form_modal(self, value=""):
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
        """Returns `None` if unexpected error happened, `str` if expected error, `Message` if success."""
        message = confirmation_callback_ctx.message
        if not message:
            return None
        searchResult = re.search(r"(?P<url>https?://[^\s]+)", message.content)
        if not searchResult:
            return None
        link = searchResult.group("url")
        if not isinstance(link, str):
            return None

        channel_id = int(link.split("/")[-2])
        message_id = int(link.split("/")[-1])

        anonymous_post_message = await self.config.channels[channel_id].fetch_message(message_id)
        if not anonymous_post_message:
            return "Post not found, it may have already been deleted by admins.",
        return anonymous_post_message

    @interactions.component_callback("btn:delete_post")
    async def delete_post(self, ctx: interactions.ComponentContext):
        anonymous_post_message = await self.get_anonymous_post(ctx)
        if isinstance(anonymous_post_message, str):
            return await ctx.send(anonymous_post_message , ephemeral=True)
        if not isinstance(anonymous_post_message, interactions.Message):
            return await ctx.send("An execpected error happened.", ephemeral=True)

        await anonymous_post_message.delete(context=ctx)
        await ctx.send("Post deleted.", ephemeral=True)
        if ctx.message:
            await ctx.message.delete(context=ctx)

    @interactions.component_callback("btn:edit_description")
    async def edit_discription(self, ctx: interactions.ComponentContext):
        anonymous_post_message = await self.get_anonymous_post(ctx)
        if isinstance(anonymous_post_message, str):
            return await ctx.send(anonymous_post_message , ephemeral=True)
        if not isinstance(anonymous_post_message, interactions.Message):
            return await ctx.send("An execpected error happened.", ephemeral=True)

        # form handler
        form_modal = self.get_description_form_modal(anonymous_post_message.content)
        await ctx.send_modal(modal=form_modal)
        form_ctx = await ctx.bot.wait_for_modal(
            form_modal,
            author=ctx.author,
        )

        # update description
        description = form_ctx.responses["description"]
        await anonymous_post_message.edit(content=description)
        await form_ctx.send("Description updated.", ephemeral=True)

    async def fetch_requested_users(self, fulfilled_request_link: str) -> str:
        request_message_id = int(fulfilled_request_link.split("/")[-1])
        request_message = await self.config.upload_request_channel.fetch_message(request_message_id)
        if request_message is None:
            raise Exception("Cannot find message")

        pingme_reaction = next((reaction for reaction in request_message.reactions if reaction.emoji.name == "pingme"), None)
        if pingme_reaction is None:
            raise Exception("No one reacted to your message with :pingme:")

        users = await pingme_reaction.users().fetch()
        return "".join([u.mention for u in users])


def setup(bot: interactions.Client):
    UploadExtension(bot)
