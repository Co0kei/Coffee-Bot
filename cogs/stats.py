import asyncio
import logging

import asyncpg
from discord.ext import commands, tasks

log = logging.getLogger(__name__)


class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self._batch_lock = asyncio.Lock()
        self._data_batch = []

        self.bulk_insert_loop.add_exception_type(asyncpg.PostgresConnectionError)
        self.bulk_insert_loop.start()

    async def cog_unload(self) -> None:
        self.bulk_insert_loop.stop()

    @tasks.loop(seconds=10.0)
    async def bulk_insert_loop(self):
        async with self._batch_lock:
            await self.bulk_insert()

    async def bulk_insert(self):
        query = """INSERT INTO commands (guild_id, channel_id, author_id, used, prefix, command, type)
                   SELECT x.guild, x.channel, x.author, x.used, x.prefix, x.command, x.type
                   FROM jsonb_to_recordset($1::jsonb) AS
                   x(guild BIGINT, channel BIGINT, author BIGINT, used TIMESTAMP, prefix TEXT, command TEXT, type INT)
                """

        if self._data_batch:
            await self.bot.pool.execute(query, self._data_batch)
            total = len(self._data_batch)
            if total > 1:
                log.info('Registered %s commands to the database.', total)
            self._data_batch.clear()

    async def register_command(self, command_name, guild_id, channel_id, author_id, time_used, prefix, command_type):
        """ Saves message based commands / slash commands / context menu usage """

        async with self._batch_lock:
            self._data_batch.append({
                'guild': guild_id,
                'channel': channel_id,
                'author': author_id,
                'used': time_used,
                'prefix': prefix,
                'command': command_name,
                'type': command_type,
            })


async def setup(bot):
    await bot.add_cog(StatsCog(bot))
