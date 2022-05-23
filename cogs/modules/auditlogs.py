import asyncio
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

        settingsCog = self.bot.get_cog("SettingsCommand")
        if after.author.bot and not settingsCog.isLogBotActionsEnabled(after.guild):
            return

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
                            f'\n\n**Message Content Before:**\n`{content_before}`' \
                            f'\n\n**Message Content After:**\n`{content_after}`'

        if len(after.attachments) != 0:
            attachement1 = after.attachments[0]
            if attachement1.content_type.startswith("image"):
                embed.set_image(url=attachement1.url)
                embed.description += f"\n\n**Message Image:**"

        file = None
        content = None
        if len(embed.description) > 4096 or len(embed) > 6000:
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

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Jump to message", url=after.jump_url))

        await settingsCog.getMsgEditChannel(after.guild).send(content=content, embed=embed, file=file, view=view)

    async def handleRawEdit(self, payload: discord.RawMessageUpdateEvent, guild: discord.Guild):
        """ Message before is unknown """

        channel = guild.get_channel(payload.channel_id)
        try:
            message: discord.Message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:  # message not found?
            return

        settingsCog = self.bot.get_cog("SettingsCommand")
        if message.author.bot and not settingsCog.isLogBotActionsEnabled(guild):
            return

        embed = discord.Embed()
        embed.set_author(name="Message Edited", icon_url=message.author.display_avatar.url)
        embed.colour = discord.Colour(0x2F3136)

        if message.content:
            content_after = message.clean_content.replace("`", "")  # remove so no messed up format
        else:
            content_after = "None"
            if message.embeds:
                embed_ = message.embeds[0]
                if embed_:
                    content = f"{embed_.author.name or ''}\n{embed_.title or ''}\n{embed_.description or ''}\n"
                    for field in getattr(embed_, '_fields', []):
                        content += f"\n{field['name']}\n{field['value']}\n"
                    content += f"\n{embed_.footer.text or ''}"
                    content_after = content.replace("`", "")

        embed.description = f'**Message\'s Info:**\n' \
                            f'Message Author: {message.author.mention} ({message.author})\n' \
                            f'Channel: {message.channel.mention}\n' \
                            f'Created: {discord.utils.format_dt(message.created_at, "F")} ({discord.utils.format_dt(message.created_at, "R")})\n' \
                            f'Message ID: `{message.id}`\n' \
                            f'Attachments: `{len(message.attachments)}`' \
                            f'\n\n**Message Content Before:**\nUnknown' \
                            f'\n\n**Message Content After:**\n`{content_after}`'

        if len(message.attachments) != 0:
            attachement1 = message.attachments[0]
            if attachement1.content_type.startswith("image"):
                embed.set_image(url=attachement1.url)
                embed.description += f"\n\n**Message Image:**"

        file = None
        content = None
        if len(embed.description) > 4096 or len(embed) > 6000:
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

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Jump to message", url=message.jump_url))

        await settingsCog.getMsgEditChannel(guild).send(content=content, embed=embed, file=file, view=view)

    async def handleDelete(self, message: discord.Message):

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

        settingsCog = self.bot.get_cog("SettingsCommand")
        if _self and message.author.bot and not settingsCog.isLogBotActionsEnabled(message.guild):
            return

        embed = discord.Embed()
        embed.set_author(name="Message Deleted", icon_url=message.author.display_avatar.url)
        embed.colour = discord.Colour(0x2F3136)

        if message.content:
            content = message.clean_content.replace("`", "")  # remove so no messed up format
        else:
            content = "None"
            if message.embeds:
                embed_ = message.embeds[0]
                if embed_:
                    content = f"{embed_.author.name or ''}\n{embed_.title or ''}\n{embed_.description or ''}\n"
                    for field in getattr(embed_, '_fields', []):
                        content += f"\n{field['name']}\n{field['value']}\n"
                    content += f"\n{embed_.footer.text or ''}"
                    content = content.replace("`", "")

        embedDescription = f'**Message\'s Info:**\n' \
                           f'Message Author: {message.author.mention} ({message.author})\n' \
                           f'Deleted By: {message_deleter}\n' \
                           f'Channel: {message.channel.mention}\n' \
                           f'Created: {discord.utils.format_dt(message.created_at, "F")} ({discord.utils.format_dt(message.created_at, "R")})\n' \
                           f'Message ID: `{message.id}`\n' \
                           f'Attachments: `{len(message.attachments)}`\n' \
                           f'Stickers: `{len(message.stickers)}`' \
                           f'\n\n**Message Content:**\n`{content}`'

        if len(message.attachments) != 0:
            attachement1 = message.attachments[0]
            if attachement1 and attachement1.content_type and attachement1.content_type.startswith("image"):
                embed.set_image(url=attachement1.url)
                embedDescription += f"\n\n**Message Image:**"

        embed.description = embedDescription

        file = None
        content = None
        if len(embed.description) > 4096 or len(embed) > 6000:
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

        if _self:
            channel: discord.TextChannel = settingsCog.getMsgDeleteChannel(message.guild)
            if channel:
                await channel.send(content=content, embed=embed, file=file)
        else:
            channel: discord.TextChannel = settingsCog.getModMsgDeleteChannel(message.guild)
            if channel:
                await channel.send(content=content, embed=embed, file=file)

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

        # NO WAY TO GET AUTHOR. so idk if bot. so cant return here

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
            channel: discord.TextChannel = settingsCog.getMsgDeleteChannel(guild)
            if channel:
                await channel.send(embed=embed)
        else:
            channel: discord.TextChannel = settingsCog.getModMsgDeleteChannel(guild)
            if channel:
                await channel.send(embed=embed)

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

                        if cached_msg.content:
                            embed_cached_content += f"Content: `{cached_msg.clean_content.replace('`', '')}`\n\n"
                        else:
                            embed_cached_content += f"Content: `None`\n\n"

                        break

            for msg_id in payload.message_ids:
                if msg_id not in _id:  # it is not cached
                    non_cached_content += f"- Message ID {msg_id}:\n"
                    non_cached_content += f"  Message not in cache\n\n"

                    embed_non_cached_content += f"__Message ID {msg_id}__\n"
                    embed_non_cached_content += f"Message not in cache\n\n"

            embed = discord.Embed(timestamp=discord.utils.utcnow())
            embed.set_author(name="Bulk Message Delete", icon_url=deleter.display_avatar.url)
            embed.colour = discord.Colour(0x2F3136)

            embed.description = f'{num_deleted} messages deleted by {deleter.mention} ({deleter}) in {channel.mention}' \
                                f'\n\n**Messages:**\n\n' \
                                f'{f"{embed_cached_content}{embed_non_cached_content}"}'

            file = None
            content = None
            if len(embed.description) > 4096 or len(embed) > 6000:
                # attach as a file
                embed = None
                content = "**Bulk Message Delete!**"
                fileContent = f"{num_deleted} messages deleted in #{channel} by {deleter}:\n\n{cached_content}{non_cached_content}"

                buffer = BytesIO(fileContent.encode('utf-8'))
                file = discord.File(fp=buffer, filename='deleted_messages.txt')

            settingsCog = self.bot.get_cog("SettingsCommand")
            await settingsCog.getModMsgDeleteChannel(guild).send(content=content, embed=embed, file=file)

    async def handleNickUpdate(self, before: discord.Member, after: discord.Member):

        async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
            NickBefore = discord.utils.escape_markdown(before.display_name)
            NickAfter = discord.utils.escape_markdown(after.display_name)

            settingsCog = self.bot.get_cog("SettingsCommand")
            if entry.user.bot and not settingsCog.isLogBotActionsEnabled(after.guild):
                return

            embed = discord.Embed()
            embed.set_author(name="Nickname Update", icon_url=after.display_avatar.url)
            embed.colour = discord.Colour(0x2F3136)

            if entry.user == after:
                changed_by = "`Self`"
            else:
                changed_by = f"{entry.user.mention}  ({discord.utils.escape_markdown(str(entry.user))})"

            embed.description = f"**Member:** {after.mention}  ({discord.utils.escape_markdown(str(after))})\n" \
                                f"**Nickname Before:** `{NickBefore}`\n" \
                                f"**Nickname After:** `{NickAfter}`\n" \
                                f"**Changed By:** {changed_by}\n"

            await settingsCog.getNickUpdateChannel(after.guild).send(embed=embed)

    async def handleTimeout(self, before: discord.Member, after: discord.Member):

        async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):

            settingsCog = self.bot.get_cog("SettingsCommand")
            if entry.user.bot and not settingsCog.isLogBotActionsEnabled(after.guild):
                return

            embed = discord.Embed()
            embed.colour = discord.Colour(0x2F3136)

            if before.is_timed_out() and not after.is_timed_out():
                """ This is only triggered when a moderator manually removes a timeout. NOT when a timeout expires. """

                embed.set_author(name="Member Timeout Remove", icon_url=after.display_avatar.url)

                if entry.user == after:
                    timed_out_by = "`Self`"
                else:
                    timed_out_by = f"{entry.user.mention}  ({discord.utils.escape_markdown(str(entry.user))})"

                embed.description = f"**Member:** {after.mention}  ({discord.utils.escape_markdown(str(after))})\n" \
                                    f"**Removed By:** {timed_out_by}\n"

            else:
                embed.set_author(name="Member Timeout Add", icon_url=after.display_avatar.url)
                embed.colour = discord.Colour(0x2F3136)

                if entry.user == after:
                    timed_out_by = "`Self`"
                else:
                    timed_out_by = f"{entry.user.mention}  ({discord.utils.escape_markdown(str(entry.user))})"

                if entry.reason:
                    reason = entry.reason.replace('`', '')
                else:
                    reason = "None"

                embed.description = f"**Member:** {after.mention}  ({discord.utils.escape_markdown(str(after))})\n" \
                                    f"**Timed Out Until:** {discord.utils.format_dt(after.timed_out_until)}\n" \
                                    f"**Reason:** `{reason}`\n" \
                                    f"**Timed Out By:** {timed_out_by}\n"

            await settingsCog.getMemberTimeoutChannel(after.guild).send(embed=embed)

    async def handleRoleUpdate(self, before: discord.Member, after: discord.Member, roles_gained: list[discord.Role], roles_lost: list[discord.Role]):

        settingsCog = self.bot.get_cog("SettingsCommand")

        # parallel lists - store roles before, roles after and role user (give/remover) for the last 10 audit log entries
        audit_log_roles_before = []
        audit_log_roles_after = []
        audit_log_user = []

        async for entry in after.guild.audit_logs(limit=10, action=discord.AuditLogAction.member_role_update, oldest_first=False):
            roles_before = entry.changes.before.roles
            roles_after = entry.changes.after.roles
            user = entry.user

            audit_log_roles_before.append(roles_before)
            audit_log_roles_after.append(roles_after)
            audit_log_user.append(user)

        # print(audit_log_roles_before)
        # print(audit_log_roles_after)
        # print(audit_log_user)

        log_bot_actions: bool = settingsCog.isLogBotActionsEnabled(after.guild)

        change_list = ""

        on_first_role: bool = True
        for role in roles_gained:

            if role.is_premium_subscriber() or role.is_bot_managed() or role.id == 803221531546615840:
                given_by = "Discord"
            elif role.is_integration() or role.id == 786670642769821767:
                given_by = "An Integration"
                # Integrations are basically bots
                if not log_bot_actions:
                    continue
            else:

                given_by = None
                # print(f"finding who gave role: {role.name}")
                # loop through audit log
                for item in range(len(audit_log_user)):
                    roles_before = audit_log_roles_before[item]
                    roles_after = audit_log_roles_after[item]
                    user = audit_log_user[item]

                    # print(roles_before)
                    # print(roles_after)
                    # print(user)
                    #
                    # print(roles_lost)
                    # print(roles_gained)

                    # Check before and after equal
                    passed_before = True
                    if len(roles_after) == len(roles_gained):
                        roles_gained_id = [__item.id for __item in roles_gained]

                        for _item in roles_after:
                            if _item.id not in roles_gained_id:
                                passed_before = False
                    else:
                        passed_before = False

                    passed_after = True
                    if len(roles_before) == len(roles_lost):
                        roles_lost_id = [__item.id for __item in roles_lost]

                        for _item in roles_before:
                            if _item.id not in roles_lost_id:
                                passed_after = False
                    else:
                        passed_after = False

                    if passed_before and passed_after:
                        given_by = user
                        break

                if given_by:
                    if given_by.bot and not log_bot_actions:
                        # print("Moving onto next role as dont log bot actions")
                        continue  # move onto next role - dont log this as bot.
                    else:
                        given_by = f"{given_by.mention} ({discord.utils.escape_markdown(str(given_by))})"
                else:
                    given_by = "Unknown"

            if on_first_role:
                suffix = "s"
                if len(roles_gained) == 1:
                    suffix = ""
                change_list += (f"**Role{suffix} Gained ({len(roles_gained)}):**\n")

            on_first_role = False

            change_list += (f"<:tick:873224615881748523> {role.mention} (Name: {role.name}) | Given by {given_by}\n")

        on_first_role: bool = True
        for role in roles_lost:

            if role.is_premium_subscriber() or role.is_bot_managed() or role.id == 803221531546615840:
                removed_by = "Discord"
            elif role.is_integration() or role.id == 786670642769821767:
                removed_by = "An Integration"
                # Integrations are basically bots
                if not log_bot_actions:
                    continue
            else:

                removed_by = None
                # print(f"finding who removed role: {role.name}")

                # loop through audit log
                for item in range(len(audit_log_user)):
                    roles_before = audit_log_roles_before[item]
                    roles_after = audit_log_roles_after[item]
                    user = audit_log_user[item]

                    # print(roles_before)
                    # print(roles_after)
                    # print(user)

                    # Check before and after equal
                    passed_before = True
                    if len(roles_after) == len(roles_gained):
                        roles_gained_id = [__item.id for __item in roles_gained]

                        for _item in roles_after:
                            if _item.id not in roles_gained_id:
                                passed_before = False
                    else:
                        passed_before = False

                    passed_after = True
                    if len(roles_before) == len(roles_lost):
                        roles_lost_id = [__item.id for __item in roles_lost]

                        for _item in roles_before:
                            if _item.id not in roles_lost_id:
                                passed_after = False
                    else:
                        passed_after = False

                    if passed_before and passed_after:
                        # if roles_after == roles_gained and roles_before == roles_lost:
                        removed_by = user
                        break

                if removed_by:
                    if removed_by.bot and not log_bot_actions:
                        # print("Moving onto next role as dont log bot actions")
                        continue  # move onto next role - dont log this as bot.
                    else:
                        removed_by = f"{removed_by.mention} ({discord.utils.escape_markdown(str(removed_by))})"
                else:
                    removed_by = "Unknown"

            if on_first_role:
                suffix = "s"
                if len(roles_lost) == 1:
                    suffix = ""
                change_list += (f"**Role{suffix} Lost ({len(roles_lost)}):**\n")

            on_first_role = False

            change_list += (f"<:cross:872834807476924506> {role.mention} (Name: {role.name}) | Removed by {removed_by}\n")

        if change_list == "":
            return

        embed = discord.Embed()
        embed.set_author(name="Role Update", icon_url=after.display_avatar.url)
        embed.colour = discord.Colour(0x2F3136)

        embed.description = f"**Member:** {after.mention}  ({discord.utils.escape_markdown(str(after))})\n" \
                            f"{change_list}"

        await settingsCog.getRoleUpdateChannel(after.guild).send(embed=embed)

    async def handleRoleDelete(self, role: discord.Role):
        self.bot.delete_role_cache[str(role.id)] = []
        await asyncio.sleep(2)

        async for entry in role.guild.audit_logs(limit=3, action=discord.AuditLogAction.role_delete, oldest_first=False):
            if entry.target.id == role.id:
                deleter = entry.user

                # a role getting deleted is significant enough to get logged - even if deleted by a bot

                members = self.bot.delete_role_cache[str(role.id)]

                embed = discord.Embed()
                embed.set_author(name="Role Delete", icon_url=deleter.display_avatar.url)
                embed.colour = discord.Colour(0x2F3136)

                msg = ""
                file_msg = ""
                for mem in members:
                    mem_A = await self.bot.get_or_fetch_member(role.guild, mem)
                    msg += f" - {mem_A.mention} ({mem_A})\n"
                    file_msg += f" - {mem_A}\n"
                embed.description = f"Role **{role.name}** was deleted by {deleter.mention} ({deleter}).\n\n" \
                                    f"**Members That Lost Role ({len(members)}):**\n{msg}"

                file = None
                content = None
                if len(embed.description) > 4096 or len(embed) > 6000:
                    # attach as a file
                    embed = None
                    content = "**Role Delete!**"
                    fileContent = f"Role {role.name} was deleted by {deleter}.\n\n" \
                                  f"Members That Lost Role ({len(members)}):\n{file_msg}"
                    buffer = BytesIO(fileContent.encode('utf-8'))
                    file = discord.File(fp=buffer, filename='role_delete.txt')

                settingsCog = self.bot.get_cog("SettingsCommand")
                await settingsCog.getRoleUpdateChannel(role.guild).send(content=content, embed=embed, file=file)
                return


async def setup(bot):
    await bot.add_cog(AuditLogCog(bot))
