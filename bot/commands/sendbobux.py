import bot.discordbot as discordbot
from ..betterbot import Member
import discord
import db

name = 'sendbobux'


async def run(message, member: Member = None, amount: int = 0):
	if not member:
		return await message.channel.send('Invalid member')
	if not amount or amount <= 0:
		return await message.channel.send('Invalid amount')
	sender_bobux = await db.get_bobux(message.author.id)
	if sender_bobux < amount:
		return await message.channel.send('You don\'t have enough bobux')
	await db.change_bobux(message.author.id, -amount)
	await db.change_bobux(member.id, amount)
	reciever_bobux = await db.get_bobux(member.id)
	await message.channel.send(
		embed=discord.Embed(
			description=f'Ok, <@{member.id}> now has **{reciever_bobux}** bobux.'
		)
	)
	await discordbot.check_bobux_roles(member.id, reciever_bobux)