import json
import re
from abc import ABC
from typing import Optional, List

from parse import parse

from mcdreforged.handler.abstract_server_handler import AbstractServerHandler
from mcdreforged.info_reactor.info import Info
from mcdreforged.info_reactor.server_information import ServerInformation
from mcdreforged.minecraft.rtext.text import RTextBase
from mcdreforged.plugin.meta.version import VersionParsingError
from mcdreforged.utils import string_util
from mcdreforged.utils.types import MessageText


class AbstractMinecraftHandler(AbstractServerHandler, ABC):
	"""
	An abstract handler for Minecraft Java Edition servers
	"""
	def get_stop_command(self) -> str:
		return 'stop'

	@classmethod
	def get_player_message_parsing_formatter(cls) -> List[str]:
		"""
		Return a list of str that is used in method :meth:`parse_server_stdout` for parsing player message

		These strings will be passed as the 1st parameter to ``parse.parse``,
		they are both supposed to contain at least the following fields:

		- ``name``, the name of the player
		- ``message``, what the player said

		The return value of the first succeeded ``parse.parse`` call will be used
		for filling fields of the :class:`~mcdreforged.info_reactor.info.Info` object

		If none of these formatter strings can be parsed successfully, then this info
		is considered as a non-player message, i.e. has :attr:`info.player <mcdreforged.info_reactor.info.Info.hour>` equaling None
		"""
		return [
			'<{name}> {message}',
			'[Not Secure] <{name}> {message}',  # since mc 1.19, when a player sends an un-verified chat message
		]

	@classmethod
	def format_message(cls, message: MessageText) -> str:
		"""
		A utility method to convert a message into a valid argument used in message sending command
		"""
		if isinstance(message, RTextBase):
			return message.to_json_str()
		else:
			return json.dumps(str(message))

	def get_send_message_command(self, target: str, message: MessageText, server_information: ServerInformation) -> Optional[str]:
		can_do_execute = False
		if server_information.version is not None:
			try:
				from mcdreforged.plugin.meta.version import Version
				version = Version(server_information.version.split(' ')[0])
				if version >= Version('1.13.0'):
					can_do_execute = True
			except VersionParsingError:
				pass
		command = 'tellraw {} {}'.format(target, self.format_message(message))
		if can_do_execute:
			command = 'execute at @p run ' + command
		return command

	def get_broadcast_message_command(self, message: MessageText, server_information: ServerInformation) -> Optional[str]:
		return self.get_send_message_command('@a', message, server_information)

	@classmethod
	def _get_server_stdout_raw_result(cls, text: str) -> Info:
		raw_result = super()._get_server_stdout_raw_result(text)
		# Minecraft <= 1.12.x might output minecraft color codes to the console
		# Just remove that
		raw_result.content = string_util.clean_minecraft_color_code(raw_result.content)
		return raw_result

	@classmethod
	def _verify_player_name(cls, name: str):
		return re.fullmatch(r'[.a-zA-Z0-9_]{2,16}', name) is not None

	def parse_server_stdout(self, text: str):
		result = super().parse_server_stdout(text)

		for formatter in self.get_player_message_parsing_formatter():
			parsed = parse(formatter, result.content)
			if parsed is not None and self._verify_player_name(parsed['name']):
				result.player, result.content = parsed['name'], parsed['message']
				break
		return result

	def parse_player_joined(self, info: Info):
		# Steve[/127.0.0.1:9864] logged in with entity id 131 at (187.2703, 146.79014, 404.84718)
		if not info.is_user:
			parsed = parse('{name}[{}] logged in with entity id {} at ({})', info.content)
			if parsed is not None and self._verify_player_name(parsed['name']):
				return parsed['name']
		return None

	def parse_player_left(self, info: Info):
		# Steve left the game
		if not info.is_user and re.fullmatch(r'\w{1,16} left the game', info.content):
			return info.content.split(' ')[0]
		return None

	def parse_server_version(self, info: Info):
		if not info.is_user:
			parsed = parse('Starting minecraft server version {version}', info.content)
			if parsed is not None:
				return parsed['version']
		return None

	def parse_server_address(self, info: Info):
		if not info.is_user:
			parsed = parse('Starting Minecraft server on {}:{:d}', info.content)
			if parsed is not None:
				return parsed[0], parsed[1]
		return None

	def test_server_startup_done(self, info: Info):
		# 1.13+ Done (3.500s)! For help, type "help"
		# 1.13- Done (3.500s)! For help, type "help" or "?"
		return info.is_from_server and re.fullmatch(r'Done \([0-9.]*s\)! For help, type "help"( or "\?")?', info.content) is not None

	def test_rcon_started(self, info: Info):
		# RCON running on 0.0.0.0:25575
		return info.is_from_server and re.fullmatch(r'RCON running on [\w.]+:\d+', info.content) is not None

	def test_server_stopping(self, info: Info):
		# Stopping server
		return info.is_from_server and info.content == 'Stopping server'
