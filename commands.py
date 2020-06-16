import discord
from discordbot import (
	betterbot,
	client,
	has_role
)
import discordbot
from discord.ext import commands
import hypixel
import db
from betterbot import (
	Member,
	Time
)
import json
from datetime import datetime
import io
from contextlib import redirect_stdout, redirect_stderr
import forums
import time


bot_owners = {
	224588823898619905, # mat
	385506886222348290, # andytimbo
	573609464620515351, # quaglet
}

with open('roles.json', 'r') as f:
	roles = json.loads(f.read())


def get_role_id(guild_id, rank_name):
	return roles.get(str(guild_id), {}).get(rank_name)

# def bot_channel(func, *args2, **kwargs2):
# 	print('2', args2, kwargs2)
# 	def wrapper(*args, **kwargs):
# 		print('1', args, kwargs)
# 		# print('Calling', func.__name__)
# 		message = args[0]
# 		if not message.guild or bot_channels[message.guild.id] == message.channel.id:
# 			return func(*args, **kwargs)
# 		else:
# 			print('no')
# 	return wrapper

@betterbot.command(name='e')
async def e(message):
	'Sends "e".'
	await message.send('e')

@betterbot.command(name='link')
async def link(message, ign: str=None):
	if not ign:
		return await message.send('Do `!link yourusername` to link to your Hypixel account.')
	ign = ign.strip()
	try:
		print('getting user data')
		# discord_name = await hypixel.get_discord_name(ign)
		data = await hypixel.get_user_data(ign)
		print('data')
		try:
			# discord_name = data['links']['DISCORD']
			discord_name = data['discord']['name']
			assert discord_name is not None
		except:
			raise hypixel.DiscordNotFound()
	except hypixel.PlayerNotFound:
		return await message.send('Invalid username.')
	except hypixel.DiscordNotFound:
		return await message.send("You haven't set your Discord username in Hypixel yet.")
	if str(message.author) == discord_name:
		pass # good
	else:
		return await message.send(embed=discord.Embed(
			description=f'Incorrect username. Did you link your account correctly in Hypixel? ({ign} is linked to {discord_name})'
		))

	# Remove the user's old rank
	old_rank = await db.get_hypixel_rank(message.author.id)
	if old_rank:
		old_rank_role_id = get_role_id(message.guild.id, old_rank)
		if old_rank_role_id:
			old_rank_role = message.guild.get_role(old_rank_role_id)
			await message.author.remove_roles(old_rank_role, reason='Old rank')
	
	# new_rank = await hypixel.get_hypixel_rank(ign)
	new_rank = data['rank']
	new_rank_role_id = get_role_id(message.guild.id, new_rank)
	if new_rank_role_id:
		new_rank_role = message.guild.get_role(new_rank_role_id)
		await message.author.add_roles(new_rank_role, reason='Update rank')

	await db.set_hypixel_rank(message.author.id, new_rank)
	await db.set_minecraft_ign(message.author.id, ign, data['uuid'])

	if new_rank_role_id:
		await message.channel.send(
			embed=discord.Embed(
				description=f'Linked your account to **{ign}** and updated your role to **{new_rank}**.'
			)
		)
	else:
		await message.channel.send(
			embed=discord.Embed(
				description=f'Linked your account to **{ign}**.'
			)
		)

@betterbot.command(name='whois')
async def whois(message, member: Member=None):
	if not member:
		return await message.send('Do `!whois @member` to get information on that user.')
	data = await db.get_minecraft_data(member.id)
	if not data:
		return await message.send(embed=discord.Embed(
			description="This user hasn't linked their account yet. Tell them to do **!link**."
		))
	print(data)
	embed = discord.Embed(
		title=f'Who is {member}'
	)

	uuid = data['uuid']

	embed.add_field(
		name='IGN',
		value=data['ign'],
		inline=False,
	)
	embed.add_field(
		name='UUID',
		value=uuid,
		inline=False,
	)

	embed.set_thumbnail(url=f'https://crafatar.com/renders/head/{uuid}?overlay=1')

	await message.channel.send(embed=embed)


@betterbot.command(name='debugtime')
async def debugtime(message, length: Time):
	'Debugging command to test time'
	await message.send(str(length))

@betterbot.command(name='mute', bot_channel=False)
async def mute(message, member: Member, length: Time=0, reason: str=None):
	'Mutes a member for a specified amount of time'

	if not has_role(message.author.id, 717904501692170260, 'helper'): return

	if not member or not length:
		return await message.channel.send(
			'Invalid command usage. Example: **!mute gogourt 10 years nerd**'
		)

	if reason:
		reason = reason.strip()

	if reason:
		mute_message = f'<@{member.id}> has been muted for "**{reason}**".'
	else:
		mute_message = f'<@{member.id}> has been muted.'

	await message.send(embed=discord.Embed(
		description=mute_message
	))

	await db.add_infraction(
		member.id,
		'mute',
		reason
	)

	await member.send(f'You were muted for "**{reason}**"')

	try:
		await discordbot.mute_user(
			member,
			length,
			message.guild.id if message.guild else None
		)
	except discord.errors.Forbidden:
		await message.send("I don't have permission to do this")

@betterbot.command(name='unmute', bot_channel=False)
async def unmute(message, member: Member):
	'Removes a mute from a member'

	if not has_role(message.author.id, 717904501692170260, 'helper'):
		return

	await discordbot.unmute_user(
		member.id
	)

	await message.send(embed=discord.Embed(
		description=f'<@{member.id}> has been unmuted.'
	))

@betterbot.command(name='gulag')
async def gulag(message):
	'Mutes you for one minute'
	await message.send('You have entered gulag for 60 seconds.')
	await discordbot.mute_user(
		message.author,
		60,
		message.guild.id if message.guild else None
	)

@betterbot.command(name='infractions', bot_channel=False)
async def infractions(message, member: Member=None):
	'Checks the infractions that a user has (mutes, warns, bans, etc)'

	if not member:
		member = message.author

	is_checking_self = message.author.id == member.id
	
	if (
		not is_checking_self
		and not has_role(message.author.id, 717904501692170260, 'helper')
	):
		return

	infractions = await db.get_infractions(member.id)

	embed_title = 'Your infractions' if is_checking_self else f'{member}\'s infractions'

	embed = discord.Embed(
		title=embed_title
	)
	for infraction in infractions:
		value = infraction.get('reason') or '<no reason>'
		name = infraction['type']
		if 'date' in infraction:
			date_pretty = infraction['date'].strftime('%m/%d/%Y')
			name += f' ({date_pretty})'
		embed.add_field(
			name=name,
			value=value,
			inline=False
		)

	if len(infractions) == 0:
		embed.description = 'No infractions'

	if is_checking_self:
		await message.author.send(embed=embed)
	else:
		await message.send(embed=embed)


@betterbot.command(name='clearinfractions', bot_channel=False)
async def clearinfractions(message, member: Member, date: str=None):
	'Checks the infractions that a user has (mutes, warns, bans, etc)'

	if not has_role(message.author.id, 717904501692170260, 'helper'):
		return

	if not member or not date:
		return await message.send('Please use `!clearinfractions @member date`')
	# month, day, year = date.split('/')
	try:
		date = datetime.strptime(date.strip(), '%m/%d/%Y')
	except ValueError:
		return await message.send('Invalid date (use format mm/dd/yyyy)')
	cleared = await db.clear_infractions(member.id, date)

	if cleared > 1:
		return await message.send(f'Cleared {cleared} infractions from that date.')
	if cleared == 1:
		return await message.send('Cleared 1 infraction from that date.')
	else:
		return await message.send('No infractions found from that date.')


def execute(_code, loc):  # Executes code asynchronously
	_code = _code.replace('\n', '\n ')
	globs = globals()
	globs.update(loc)
	exec(
		'async def __ex():\n ' + _code,
		globs
	)
	return globs['__ex']()

@betterbot.command(name='exec', aliases=['eval'], bot_channel=False)
async def execute_command(message, code: str):
	if message.author.id != 224588823898619905: return
	f = io.StringIO()
	f2 = io.StringIO()
	with redirect_stdout(f):
		command = message.content.split(None, 1)[1].strip()
		if command.startswith('```') and command.endswith('```'):
			command = '\n'.join(command.split('\n')[1:])
			command = command[:-3]
		await execute(command, locals())
	out = f.getvalue()
	if out == '':
		out = 'No output.'
	await message.send(
		embed=discord.Embed(
			title='Eval',
			description=out
		)
	)

@betterbot.command(name='help', aliases=['commands'])
async def help_command(message):
	commands = [
		{
			'name': 'link',
			'args': '<ign>',
			'desc': 'Links your Discord account to your Minecraft account and gives you Hypixel rank roles',
		},
		{
			'name': 'e',
			'args': '',
			'desc': 'e',
		},
		{
			'name': 'gulag',
			'args': '',
			'desc': 'Puts you in gulag for one minute',
		},
		{
			'name': 'rock',
			'args': '@member',
			'desc': "Extends the length of a user's time in gulag by 5 minutes",
		},
		{
			'name': 'forum user',
			'args': '<username>',
			'desc': 'Gets the forum stats for a username',
		}
	]

	if has_role(message.author.id, 717904501692170260, 'helper'):
		commands.extend([
			{
				'name': 'mute',
				'args': '@member <length> [reason]',
				'desc': 'Mutes a user from sending messages for a certain amount of time',
			},
			{
				'name': 'unmute',
				'args': '@member',
				'desc': 'Unmutes a user early so they can send messages',
			},
			{
				'name': 'infractions',
				'args': '@member',
				'desc': 'View the infractions of another member (mutes, warns, etc)',
			},
			{
				'name': 'clearinfractions',
				'args': '@member <mm/dd/yyyy>',
				'desc': 'Clear the infractions for a member from a specific date',
			}
		])
	else:
		commands.extend([
			{
				'name': 'infractions',
				'args': '',
				'desc': 'View your own infractions (mutes, warns, etc)',
			}
		])

	description = []

	for command in commands:
		command_name = command['name']
		command_args = command['args']
		command_desc = command['desc']
		if command_args:
			command_title = f'!**{command_name}** {command_args}'
		else:
			command_title = f'!**{command_name}**'
		description.append(
			f'{command_title} - {command_desc}'
		)

	embed = discord.Embed(title='Commands', description='\n'.join(description))
	await message.send(embed=embed)

@betterbot.command(name='membercount', aliases=['members'])
async def membercount(message, command, user):
	true_member_count = message.guild.member_count
	await message.channel.send(f'There are **{true_member_count:,}** people in this server.')

# !forum
@betterbot.command(name='forum', aliases=['forums', 'f'], pad_none=False)
async def forum(message):
	await message.send('Forum commands: **!forums user (username)**')

forum_ratelimit = {}

def check_forum_ratelimit(user):
	global forum_ratelimit
	if user not in forum_ratelimit: return False
	user_ratelimit = forum_ratelimit[user]
	last_minute_uses = 0
	last_10_second_uses = 0
	last_3_second_uses = 0
	for ratelimit in user_ratelimit:
		if time.time() - ratelimit < 60:
			last_minute_uses += 1
			if time.time() - ratelimit < 10:
				last_10_second_uses += 1
				if time.time() - ratelimit < 10:
					last_3_second_uses += 1
		else:
			del user_ratelimit[0]
	print('last_minute_uses', last_minute_uses)
	print('last_10_second_uses', last_10_second_uses)
	if last_minute_uses >= 10: return True
	if last_10_second_uses >= 3: return True
	if last_3_second_uses >= 2: return True
	return False

def add_forum_ratelimit(user):
	global forum_ratelimit
	if user not in forum_ratelimit:
		forum_ratelimit[user] = []
	forum_ratelimit[user].append(time.time())
	print('forum_ratelimit', forum_ratelimit)

# !forum user
@betterbot.command(name='forum', aliases=['forums', 'f'], pad_none=False)
async def forum_user(message, command, user):
	if command not in {
		'member',
		'user'
	}:
		raise TypeError

	if check_forum_ratelimit(message.author.id):
		print('no')
		return await message.send('Stop spamming the command, nerd')
	add_forum_ratelimit(message.author.id)


	async with message.channel.typing():
		member_id = await forums.member_id_from_name(user)
		if not member_id:
			await message.send('Invalid user.')
		member = await forums.get_member(member_id)


		total_messages = member['messages']
		follower_count = member['follower_count']
		positive_reactions = member['reactions']['positive_total']
		member_name = member['name']
		member_id = member['id']
		avatar_url = member['avatar_url']

		description = (
			f'Messages: {total_messages:,}\n'
			f'Followers: {follower_count:,}\n'
			f'Reactions: {positive_reactions:,}\n'
		)

		embed = discord.Embed(
			title=f"{member_name}'s forum stats",
			description=description,
			url=f'https://hypixel.net/members/{member_id}/'
		)


		embed.set_thumbnail(url=avatar_url)


		await message.channel.send(embed=embed)

@betterbot.command(name='pee', bot_channel=False)
async def pee(message):
	'pees in gulag'

	if message.channel.id != 720073985412562975: return

	await message.channel.send('You have peed.')

@betterbot.command(name='poo', aliases=['poop'], bot_channel=False)
async def poop(message):
	'poops in gulag'

	if message.channel.id != 720073985412562975: return

	await message.channel.send('You have pooped.')

@betterbot.command(name='rock', aliases=['stone'], bot_channel=False)
async def throw_rock(message, member: Member):
	"Adds 5 minutes to someone's mute in gulag"

	if message.channel.id not in {
		720073985412562975, # gulag
		718076311150788649, # bot-commands
	}: return

	if not member:
		return await message.send('Unknown member. Example usage: **!rock piglegs**')

	if member == message.author.id:
		return await message.send("You can't throw a rock at yourself.")

	mute_end = await db.get_mute_end(member.id)
	if not (mute_end and mute_end > time.time()):
		return await message.send('This person is not in gulag.')
	mute_remaining = mute_end - time.time()

	print('mute_remaining')


	# makes sure people havent thrown a rock in the last hour
	last_rock_thrown = await db.get_rock(message.author.id)
	# if message.author.id == 224588823898619905:
	# 	last_rock_thrown = 0
	print('last_rock_thrown', last_rock_thrown)
	if time.time() - last_rock_thrown < 60 * 60:
		next_rock_seconds = (60 * 60) - int(time.time() - last_rock_thrown)
		next_rock_minutes = next_rock_seconds // 60
		if next_rock_minutes >= 2:
			next_rock_str = f'{next_rock_minutes} minutes'
		elif next_rock_minutes == 1:
			next_rock_str = f'one minute'
		elif next_rock_seconds == 1:
			next_rock_str = f'one second'
		else:
			next_rock_str = f'{next_rock_seconds} seconds'
		return await message.send(f'You threw a rock too recently. You can throw a rock again in {next_rock_str}')

	await db.set_rock(message.author.id)

	# Add 5 minutes to someone's mute
	new_mute_remaining = int(mute_remaining + (60 * 5))

	print('muting again')

	new_mute_remaining_minutes = int(new_mute_remaining // 60)
	new_mute_remaining_hours = int(new_mute_remaining_minutes // 60)
	if new_mute_remaining_hours >= 2:
		new_mute_str = f'{new_mute_remaining_hours} hours'
	elif new_mute_remaining_hours == 1:
		new_mute_str = f'one hour'
	elif new_mute_remaining_minutes >= 2:
		new_mute_str = f'{new_mute_remaining_minutes} minutes'
	elif new_mute_remaining_minutes == 1:
		new_mute_str = f'one minute'
	elif new_mute_remaining == 1:
		new_mute_str = f'one second'
	else:
		new_mute_str = f'{new_mute_remaining} seconds'
	await message.send(f'<@{member.id}> is now muted for {new_mute_str}')

	await discordbot.mute_user(
		member,
		new_mute_remaining,
		717904501692170260
	)

@betterbot.command(name='mutelength', aliases=['mutetime'], bot_channel=False)
async def mute_length(message, member: Member=None):
	if message.channel.id not in {
		720073985412562975, # gulag
		718076311150788649, # bot-commands
		719518839171186698, # staff-bot-commands
	}: return

	if not member:
		member = message.author

	mute_remaining = int((await db.get_mute_end(member.id)) - time.time())

	if mute_remaining < 0:
		await discordbot.unmute_user(member.id, True, False)
 
	mute_remaining_minutes = int(mute_remaining // 60)
	mute_remaining_hours = int(mute_remaining_minutes // 60)
	if mute_remaining_hours >= 2:
		mute_str = f'{mute_remaining_hours} hours'
	elif mute_remaining_hours == 1:
		mute_str = f'one hour'
	elif mute_remaining_minutes >= 2:
		mute_str = f'{mute_remaining_minutes} minutes'
	elif mute_remaining_minutes == 1:
		mute_str = f'one minute'
	elif mute_remaining == 1:
		mute_str = f'one second'
	else:
		mute_str = f'{mute_remaining} seconds'

	if member.id == message.author.id:
		await message.send(embed=discord.Embed(
			description=f'You are muted for {mute_str}'
		))
	else:
		await message.send(embed=discord.Embed(
			description=f'<@{member.id}> is muted for {mute_str}'
		))