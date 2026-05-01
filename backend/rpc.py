"""
Module for the Discord RPC client.
"""

import enum
import inspect
import json
import os
import struct
import time
import typing
import uuid
from typing import Any

from .logger import logger
from .utils import remove_none


class RPCError(RuntimeError):
    """Raised when the Discord RPC protocol fails."""


class OperationCode(enum.Enum):
    """Discord IPC operation codes."""

    HANDSHAKE = 0
    FRAME = 1
    CLOSE = 2


class ActivityType(enum.Enum):
    """Discord activity types."""

    PLAYING = 0
    LISTENING = 2
    WATCHING = 3
    COMPETING = 5


class ClientRPC:
    """ClientRPC core class for Discord RPC."""

    def __init__(
        self,
        client_id: typing.Optional[typing.Union[str, int]] = None,
        debug: bool = False,
    ) -> None:
        self.debug = debug
        self.__client_id = "" if client_id is None else str(client_id)

        self.__socket: typing.Optional[typing.BinaryIO] = None
        self.__connected: bool = False
        self._pipe_connected: bool = True

        self._rpc_pid: int = os.getpid()

        pipe_template = r"\\.\pipe\discord-ipc-{}"
        for index in range(10):
            path = pipe_template.format(index)
            try:
                self.__socket = open(path, "w+b")  # pylint: disable=consider-using-with
                if self.debug:
                    logger.info("Connected to Discord IPC: %s", path)
                break
            except FileNotFoundError:
                continue
            except OSError as exc:
                logger.error("OS error opening pipe %s: %s", path, exc)
        else:
            logger.error("Failed to connect to Discord IPC (is Discord running?)")
            self._pipe_connected = False

    def _send(self, payload: dict[str, Any], operation_code: OperationCode) -> None:
        """Send a payload to the Discord IPC."""
        if not self.__socket:
            raise RPCError("Discord IPC socket is not available")

        try:
            if self.debug:
                logger.debug("IPC SEND op=%s payload=%s", operation_code.name, payload)
            raw = json.dumps(payload).encode("utf-8")
            packet = struct.pack("<ii", operation_code.value, len(raw)) + raw
            self.__socket.write(packet)
            self.__socket.flush()
        except OSError as exc:
            raise RPCError(f"IPC send failed: {exc}") from exc

    def _recv(self) -> dict[str, Any]:
        """Receive a payload from the Discord IPC."""
        if not self.__socket:
            raise RPCError("Discord IPC socket is not available")

        try:
            header = self.__socket.read(8)
            if not header or len(header) < 8:
                raise RPCError("Incomplete IPC header")

            _, size = struct.unpack("<ii", header)
            data = self.__socket.read(size)
            if not data or len(data) < size:
                raise RPCError("Incomplete IPC payload")

            payload = json.loads(data.decode("utf-8"))
            if self.debug:
                logger.debug("IPC RECV payload=%s", payload)
            return payload
        except json.JSONDecodeError as exc:
            raise RPCError(f"Invalid IPC JSON payload: {exc}") from exc
        except OSError as exc:
            raise RPCError(f"IPC receive failed: {exc}") from exc

    def connect(self) -> bool:
        """Establish the RPC connection with Discord."""
        if not self._pipe_connected:
            logger.warning("Pipe not connected")
            return False
        if self.__connected:
            return True

        try:
            self.__handshake()
            return True
        except RPCError:
            logger.exception("Discord RPC handshake failed")
            try:
                if self.__socket:
                    self.__socket.close()
            except OSError as exc:
                logger.error("Error closing IPC socket after handshake failure: %s", exc)
            self.__socket = None
            self._pipe_connected = False
            self.__connected = False
            return False

    def __handshake(self) -> None:
        """Perform the Discord IPC handshake and set the connected flag.

        Raises:
            RPCError: If Discord returns an error code or an unexpected response.
        """
        self._send({"v": 1, "client_id": self.__client_id}, OperationCode.HANDSHAKE)
        data = self._recv()

        if data.get("code") == 4000:
            raise RPCError(data.get("message", "Handshake error"))

        if data.get("evt") == "READY":
            self.__connected = True
            if self.debug:
                user = data.get("data", {}).get("user", {}).get("username")
                logger.info("Discord RPC ready (user=%s)", user)
            return

        raise RPCError(f"Handshake failed: {data}")

    # pylint: disable=too-many-arguments
    def update(
        self,
        state: typing.Optional[str],
        details: typing.Optional[str],
        activity_type: typing.Optional[ActivityType],
        start_time: typing.Optional[int],
        end_time: typing.Optional[int],
        large_image: typing.Optional[str],
        large_text: typing.Optional[str],
        small_image: typing.Optional[str],
        small_text: typing.Optional[str],
        buttons: typing.Optional[list[dict[str, str]]],
    ) -> None:
        """Update the Discord Rich Presence activity."""
        if not self._pipe_connected or not self.__connected:
            return

        if activity_type is not None and not isinstance(activity_type, ActivityType):
            raise ValueError("Invalid activity type")

        if buttons is not None:
            if not isinstance(buttons, list):
                raise ValueError("buttons must be a list")
            for button in buttons[:2]:
                if not isinstance(button, dict):
                    raise ValueError("Each button must be a dict")
                if "label" not in button or "url" not in button:
                    raise ValueError("Each button must include 'label' and 'url'")

        activity: dict[str, Any] = {}

        if state is not None:
            activity["state"] = state
        if details is not None:
            activity["details"] = details
        if activity_type is not None:
            activity["type"] = activity_type.value

        timestamps: dict[str, int] = {}
        if start_time is not None:
            timestamps["start"] = start_time
        if end_time is not None:
            timestamps["end"] = end_time
        if timestamps:
            activity["timestamps"] = timestamps

        assets: dict[str, str] = {}
        if large_image is not None:
            assets["large_image"] = large_image
        if large_text is not None:
            assets["large_text"] = large_text
        if small_image is not None:
            assets["small_image"] = small_image
        if small_text is not None:
            assets["small_text"] = small_text
        if assets:
            activity["assets"] = assets

        if buttons:
            activity["buttons"] = buttons[:2]

        activity = remove_none(activity)

        payload = {
            "cmd": "SET_ACTIVITY",
            "args": {"pid": self._rpc_pid, "activity": activity},
            "nonce": str(uuid.uuid4()),
        }

        if self.debug:
            try:
                frame = inspect.stack()[1]
                mod = inspect.getmodule(frame[0])
                caller = mod.__name__ if mod else frame.filename
            except Exception:
                caller = "unknown"
            logger.debug("SET_ACTIVITY pid=%s caller=%s", self._rpc_pid, caller)

        self._send(payload, OperationCode.FRAME)
        response = self._recv()
        if response.get("evt") not in {None, "ACTIVITY_JOIN", "ACTIVITY_SPECTATE"}:
            logger.debug("Unexpected SET_ACTIVITY response: %s", response)

    def clear_activity(self) -> None:
        """Clear the current Discord Rich Presence activity."""
        if not self._pipe_connected or not self.__connected:
            return

        payload = {
            "cmd": "SET_ACTIVITY",
            "args": {"pid": self._rpc_pid, "activity": None},
            "nonce": str(uuid.uuid4()),
        }

        if self.debug:
            logger.debug("Clearing activity pid=%s", self._rpc_pid)

        self._send(payload, OperationCode.FRAME)
        response = self._recv()
        if response.get("evt") not in {None, "ACTIVITY_JOIN", "ACTIVITY_SPECTATE"}:
            logger.debug("Unexpected clear_activity response: %s", response)

    def close(self) -> None:
        """Close the RPC connection cleanly."""
        if not self._pipe_connected:
            return

        if self.__connected:
            try:
                self.clear_activity()
                time.sleep(0.25)
            except Exception:
                logger.exception("Failed to clear Discord activity during close")

            try:
                self._send({}, OperationCode.CLOSE)
            except Exception:
                logger.exception("Failed to send CLOSE frame to Discord IPC")

        try:
            if self.__socket:
                self.__socket.close()
        except OSError as exc:
            logger.error("Error closing IPC socket: %s", exc)

        self.__connected = False
        if self.debug:
            logger.info("Discord RPC closed cleanly")
