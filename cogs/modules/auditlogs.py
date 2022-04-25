import logging
from datetime import timedelta
from io import BytesIO

import discord
from discord.ext import commands

log = logging.getLogger(__name__)


class AuditLogCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def handleEdit(self, before: discord.Message, after: discord.Message):

        embed = discord.Embed()
        embed.set_author(name="Message Edited", icon_url=after.author.display_avatar.url)
        embed.colour = discord.Colour(0x2F3136)

        content_before = before.clean_content.replace("`", "")
        content_after = after.clean_content.replace("`", "")

        embed.description = f'**Message\'s Info:**\n' \
                            f'Message Author: {after.author.mention} ({after.author})\n' \
                            f'Channel: {after.channel.mention}\n' \
                            f'Created: {discord.utils.format_dt(after.created_at, "F")} ({discord.utils.format_dt(after.created_at, "R")})\n' \
                            f'Message ID: `{after.id}`\n' \
                            f'Attachments: `{len(after.attachments)}`' \
                            f'\n\n**Message Content Before:**\n`{content_before} `' \
                            f'\n\n**Message Content After:**\n`{content_after} `'

        file = None
        content = None
        if len(embed) > 6000 or len(embed.description) > 4096:
            # attach as a file
            embed = None
            content = "**Message Edit!**"
            fileContent = \
                f'Message Author: {after.author}\n' \
                f'Channel: #{after.channel}\n' \
                f'Created (UTC): {after.created_at.strftime("%Y-%m-%d %H:%M-%S")}\n' \
                f'Message ID: {after.id}\n' \
                f'Attachments: {len(after.attachments)}' \
                f'\n\nMessage Content Before:\n{before.clean_content}' \
                f'\n\nMessage Content After:\n{after.clean_content}'

            buffer = BytesIO(fileContent.encode('utf-8'))
            file = discord.File(fp=buffer, filename='edited_message.txt')

        settingsCog = self.bot.get_cog("SettingsCommand")
        await settingsCog.getMsgEditChannel(after.guild).send(content=content, embed=embed, file=file)

    async def handleRawEdit(self, payload: discord.RawMessageUpdateEvent, guild: discord.Guild):
        """ Message before is unknown """

        channel = guild.get_channel(payload.channel_id)
        message: discord.Message = await channel.fetch_message(payload.message_id)

        embed = discord.Embed()
        embed.set_author(name="Message Edited", icon_url=message.author.display_avatar.url)
        embed.colour = discord.Colour(0x2F3136)

        content_after = message.clean_content.replace("`", "")

        embed.description = f'**Message\'s Info:**\n' \
                            f'Message Author: {message.author.mention} ({message.author})\n' \
                            f'Channel: {message.channel.mention}\n' \
                            f'Created: {discord.utils.format_dt(message.created_at, "F")} ({discord.utils.format_dt(message.created_at, "R")})\n' \
                            f'Message ID: `{message.id}`\n' \
                            f'Attachments: `{len(message.attachments)}`' \
                            f'\n\n**Message Content Before:**\nUnknown' \
                            f'\n\n**Message Content After:**\n`{content_after} `'

        file = None
        content = None
        if len(embed) > 6000 or len(embed.description) > 4096:
            # attach as a file
            embed = None
            content = "**Message Edit!**"
            fileContent = \
                f'Message Author: {message.author}\n' \
                f'Channel: #{message.channel}\n' \
                f'Created (UTC): {message.created_at.strftime("%Y-%m-%d %H:%M-%S")}\n' \
                f'Message ID: {message.id}\n' \
                f'Attachments: {len(message.attachments)}' \
                f'\n\nMessage Content Before:\nUnknown' \
                f'\n\nMessage Content After:\n{message.clean_content}'

            buffer = BytesIO(fileContent.encode('utf-8'))
            file = discord.File(fp=buffer, filename='edited_message.txt')

        settingsCog = self.bot.get_cog("SettingsCommand")
        await settingsCog.getMsgEditChannel(guild).send(content=content, embed=embed, file=file)

    async def handleDelete(self, message: discord.Message):
        # ATTEMPT 27
        # after = discord.utils.utcnow() - timedelta(seconds=1)
        # async for entry in message.guild.audit_logs(limit=1, action=discord.AuditLogAction.message_delete):
        #     # If a bot/the author deletes the message it won't show up in audit logs
        #     _self = False
        #     if entry and message.author == entry.target and entry.extra.channel == message.channel:  # make sure right user and channel
        #         if entry.created_at >= after:  # message deleted by moderator as audit log created within past second
        #             deleted_by = f"{entry.user.mention} ({entry.user})"
        # 
        #         elif entry.extra.count > 1 and discord.utils.utcnow() - entry.created_at < timedelta(minutes=2):  # deletes can stack up SO limit to only in the previous 2 mins
        #             # THIS not fail proof but best i can do.
        #             # Say a mod deletes a members message then a bot deletes a members message within 2 mins. It will say the mod deleted it since bots dont show up in the audit log.
        #             # The deleted message counter increases but the log creation time stays the same which makes it tricky.
        #             deleted_by = f"{entry.user.mention} ({entry.user})"
        #         else:
        #             deleted_by = "`Self or a Bot`"
        #             _self = True
        # 
        #     else:  # no audit log entry
        #         deleted_by = "`Self or a Bot`"
        #         _self = True
        # 

        # MY AUDIT LOG CHECKING METHOD THING
        author = message.author
        channel = message.channel
        time = discord.utils.utcnow()

        # self.bot.delete_log_cache is a map of audit log id to COUNT OF DELETED MESSAGEs
        message_deleter = "`Self or a Bot`"
        _self = True
        async for entry in message.guild.audit_logs(limit=10, action=discord.AuditLogAction.message_delete):
            entry_id = entry.id
            entry_deleter = entry.user
            entry_victim = entry.target  # member that had message deleted
            entry_channel = entry.extra.channel
            entry_count = entry.extra.count
            entry_created = entry.created_at

            if author == entry_victim and channel == entry_channel and time - entry_created < timedelta(seconds=1):
                # If same author channel AND created within last seconds, we have 100% found deleter.
                # This is when a human moderator deletes another human or bots message
                self.bot.delete_log_cache[entry_id] = entry_count  # Cache it
                message_deleter = f"{entry_deleter.mention} ({entry_deleter})"
                _self = False
                break

            # Now we must analyse stacked deletions
            if entry_id not in self.bot.delete_log_cache:
                # Cache all deleted message logs and numbers
                self.bot.delete_log_cache[entry_id] = entry_count
            else:
                # Pull cached val
                cached_count = self.bot.delete_log_cache[entry_id]
                # print(f"Cache: {self.bot.delete_log_cache}")
                # print(f"Entry count: {entry_count}")
                # print(f"Cached count: {cached_count}")
                # print(f"Author: {entry_victim}")

                if entry_count > cached_count and author == entry_victim and channel == entry_channel:
                    # If count has gone up AND correct author/channel, we have 100% found deleter.
                    self.bot.delete_log_cache[entry_id] = entry_count  # update cache
                    message_deleter = f"{entry_deleter.mention} ({entry_deleter})"
                    _self = False
                    break
            # otherwise message deleted by self or a bot

        if _self and message.author.bot:
            return  # ppl dont care about bot deleting its own message

        embed = discord.Embed()
        embed.set_author(name="Message Deleted", icon_url=message.author.display_avatar.url)
        embed.colour = discord.Colour(0x2F3136)
        content = message.clean_content.replace("`", "")  # remove so no messed up format
        embedDescription = f'**Message\'s Info:**\n' \
                           f'Message Author: {message.author.mention} ({message.author})\n' \
                           f'Deleted By: {message_deleter}\n' \
                           f'Channel: {message.channel.mention}\n' \
                           f'Created: {discord.utils.format_dt(message.created_at, "F")} ({discord.utils.format_dt(message.created_at, "R")})\n' \
                           f'Message ID: `{message.id}`\n' \
                           f'Attachments: `{len(message.attachments)}`' \
                           f'\n\n**Message Content:**\n`{content} `'

        if len(message.attachments) != 0:
            attachement1 = message.attachments[0]
            if attachement1.content_type.startswith("image"):
                embed.set_image(url=attachement1.url)
                embedDescription += f"\n\n**Message Image:**"

        embed.description = embedDescription

        file = None
        content = None
        if len(embed) > 6000 or len(embed.description) > 4096:
            # attach as a file
            embed = None
            content = "**Message Delete!**"
            fileContent = \
                f'Message Author: {message.author}\n' \
                f'Deleted By: {message_deleter.replace("`", "")}\n' \
                f'Channel: #{message.channel}\n' \
                f'Created (UTC): {message.created_at.strftime("%Y-%m-%d %H:%M-%S")}\n' \
                f'Message ID: {message.id}\n' \
                f'Attachments: {len(message.attachments)}' \
                f'\n\nMessage Content:\n{message.clean_content}'

            buffer = BytesIO(fileContent.encode('utf-8'))
            file = discord.File(fp=buffer, filename='deleted_message.txt')

        settingsCog = self.bot.get_cog("SettingsCommand")
        if _self:
            await settingsCog.getMsgDeleteChannel(message.guild).send(content=content, embed=embed, file=file)
        else:
            await settingsCog.getModMsgDeleteChannel(message.guild).send(content=content, embed=embed, file=file)

    async def handleRawDelete(self, payload: discord.RawMessageDeleteEvent, guild: discord.Guild):  # DONE
        """ Message is unknown"""

        # MY AUDIT LOG CHECKING METHOD THING
        channel = guild.get_channel(payload.channel_id)
        time = discord.utils.utcnow()

        message_deleter = "`Self or a Bot`"
        _self = True
        async for entry in guild.audit_logs(limit=10, action=discord.AuditLogAction.message_delete):
            entry_id = entry.id
            entry_deleter = entry.user
            entry_channel = entry.extra.channel
            entry_count = entry.extra.count
            entry_created = entry.created_at

            if channel == entry_channel and time - entry_created < timedelta(seconds=1):
                self.bot.delete_log_cache[entry_id] = entry_count  # Cache it
                message_deleter = f"{entry_deleter.mention} ({entry_deleter})"
                _self = False
                break

            # Now we must analyse stacked deletions
            if entry_id not in self.bot.delete_log_cache:
                # Cache all deleted message logs and numbers
                self.bot.delete_log_cache[entry_id] = entry_count
            else:
                # Pull cached val
                cached_count = self.bot.delete_log_cache[entry_id]

                if entry_count > cached_count and channel == entry_channel:
                    self.bot.delete_log_cache[entry_id] = entry_count  # update cache
                    message_deleter = f"{entry_deleter.mention} ({entry_deleter})"
                    _self = False
                    break
            # otherwise message deleted by self or a bot

        embed = discord.Embed()
        embed.set_author(name="Message Deleted")  # , icon_url=message.author.display_avatar.url)
        embed.colour = discord.Colour(0x2F3136)
        embed.description = f'**Message\'s Info:**\n' \
                            f'Deleted By: {message_deleter}\n' \
                            f'Channel: {channel.mention}\n' \
                            f'Message ID: `{payload.message_id}`\n' \
                            f'No other information available, sorry.'

        settingsCog = self.bot.get_cog("SettingsCommand")
        if _self:
            await settingsCog.getMsgDeleteChannel(guild).send(embed=embed)
        else:
            await settingsCog.getModMsgDeleteChannel(guild).send(embed=embed)

    async def handleRawBulkDelete(self, payload: discord.RawBulkMessageDeleteEvent, guild: discord.Guild):  # DONE
        """ Some messages can be unknown """
        num_deleted = len(payload.message_ids)

        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.message_bulk_delete):
            # if payload.channel_id == entry.target.id:
            deleter = entry.user
            channel = entry.target

            # Sort messages
            _id = []
            created_at = []
            for msg in payload.cached_messages:
                _id.append(msg.id)
                created_at.append(msg.created_at)

            if len(_id) >= 1:
                data_sort = [list(a) for a in zip(_id, created_at)]
                list4 = sorted(data_sort, key=lambda x: x[1], reverse=True)
                _id, created_at = map(list, zip(*list4))

            # These are for the FILE
            cached_content = ""
            non_cached_content = ""

            # This are for the EMBED
            embed_cached_content = ""
            embed_non_cached_content = ""

            for msg_id in _id:
                cached_content += f"- Message ID {msg_id}:\n"
                embed_cached_content += f"__Message ID {msg_id}__\n"
                for cached_msg in payload.cached_messages:
                    if cached_msg.id == msg_id:
                        cached_content += f"  Author: {cached_msg.author}\n"
                        cached_content += f"  Created (UTC): {cached_msg.created_at.strftime('%Y-%m-%d %H:%M-%S')}\n"  # year-month-day hour:min:sec
                        cached_content += f"  Content: {cached_msg.clean_content}\n\n"

                        embed_cached_content += f"Author: {cached_msg.author.mention} ({cached_msg.author})\n"
                        embed_cached_content += f"Created: {discord.utils.format_dt(cached_msg.created_at)}\n"
                        embed_cached_content += f"Content: `{cached_msg.clean_content.replace('`', '')} `\n\n"
                        break

            for msg_id in payload.message_ids:
                if msg_id not in _id:  # it is not cached
                    non_cached_content += f"- Message ID {msg_id}:\n"
                    non_cached_content += f"  Message not in cache\n\n"

                    embed_non_cached_content += f"__Message ID {msg_id}__\n"
                    embed_non_cached_content += f"Message not in cache\n\n"

            content = None
            embed = None
            file = None
            if len(f"{embed_cached_content}{embed_non_cached_content}") > 3500:
                # send file
                content = "**Bulk Message Delete!**"
                fileContent = f"{num_deleted} messages deleted in #{channel} by {deleter}:\n\n{cached_content}{non_cached_content}"
                buffer = BytesIO(fileContent.encode('utf-8'))
                file = discord.File(fp=buffer, filename='deleted_messages.txt')
            else:
                # send embed
                embed = discord.Embed(timestamp=discord.utils.utcnow())
                embed.set_author(name="Bulk Message Delete", icon_url=deleter.display_avatar.url)
                embed.colour = discord.Colour(0x2F3136)

                embed.description = f'{num_deleted} messages deleted by {deleter.mention} ({deleter}) in {channel.mention}' \
                                    f'\n\n**Messages:**\n\n' \
                                    f'{f"{embed_cached_content}{embed_non_cached_content}"}'

            settingsCog = self.bot.get_cog("SettingsCommand")
            await settingsCog.getModMsgDeleteChannel(guild).send(content=content, embed=embed, file=file)


async def setup(bot):
    await bot.add_cog(AuditLogCog(bot))
