"""
Context manager for automatic logger lifecycle management.

The :class:`LogContextManager` simplifies common logging scenarios by
automatically calling :meth:`LogManager.setup` on entry and emitting start
and finish messages.  It also integrates with :class:`LogNotifier` to
send external notifications (e.g. email, Slack) when exceptions escape the
managed block.  All configuration is supplied via a :class:`LogPolicy`.
"""

from __future__ import annotations

import traceback
from typing import Optional, Type, Any
from types import TracebackType

from .manager import LogManager, DummyLogger
from .policy import LogPolicy
from .notifier import LogNotifier


class LogContextManager:
    """
    A context manager that sets up and tears down logging automatically.

    Upon entry the associated :class:`LogManager` is configured and a logger
    instance (or ``DummyLogger`` if logging is disabled) is returned.  Upon
    exit any unhandled exception will be logged and, when enabled, a
    notification will be dispatched via the configured :class:`LogNotifier`.
    """

    def __init__(self, name: str, policy: Optional[LogPolicy] = None) -> None:
        self.name = name
        self.policy = policy or LogPolicy() # pyright: ignore[reportCallIssue]
        self.manager = LogManager(name, policy=self.policy)
        # ``log`` may be an instance of loguru's logger, the fallback logger,
        # or a ``DummyLogger``.  Use ``Any`` here to avoid Pylance reporting
        # missing attributes like ``info`` or ``error`` on an ``object`` type.
        self.log: Optional[Any] = None

        # Determine if a notifier should be created based on the policy
        self.use_notifier: bool = bool(self.policy.use_notifier and self.policy.notifier_policy.enabled)
        self.notifier: Optional[LogNotifier] = None
        if self.use_notifier:
            try:
                # Pass a filtered set of fields to the LogNotifier.  The
                # NotifierPolicy model includes an ``enabled`` flag which is
                # not accepted by the LogNotifier constructor, so we exclude
                # it when constructing the keyword arguments.  Additional
                # unsupported keys would similarly be ignored here.
                kwargs = self.policy.notifier_policy.model_dump(exclude={"enabled"})
                self.notifier = LogNotifier(**kwargs)
            except Exception as e:  # pragma: no cover - runtime protection
                # If initialisation fails, fall back to no notification rather
                # than raising to the caller.  Emit a diagnostic message to
                # aid debugging.
                print(f"[LogContextManager] Notifier 초기화 실패: {e}")
                self.use_notifier = False

    def __enter__(self):
        """Set up logging and return a logger object.

        When logging is disabled a ``DummyLogger`` is returned which exposes the
        same API as the real logger but discards all messages.
        """
        self.log = self.manager.setup()
        # Emit a start message if the logger implements the ``info`` method
        if hasattr(self.log, "info"):
            self.log.info(f"[{self.name}] Logging started.")
        return self.log

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Handle exceptions and emit a finish message upon context exit."""
        # Nothing to clean up if no logger was set up
        if not self.log:
            return
        try:
            # If an exception occurred propagate details to the log and
            # optionally trigger the notifier
            if exc_type:
                tb_text = ''.join(traceback.format_exception(exc_type, exc_val, exc_tb))
                if hasattr(self.log, "error"):
                    self.log.error(f"[{self.name}] Exception occurred: {exc_val}\n{tb_text}")

                # Send notifications when configured
                if self.use_notifier and self.notifier:
                    try:
                        self.notifier.notify(self.name, exc_type, exc_val, exc_tb)
                    except Exception as e:
                        print(f"[LogContextManager] Notifier 실행 실패: {e}")
            # Always emit a finish message
            if hasattr(self.log, "info"):
                self.log.info(f"[{self.name}] Logging finished.")
        except Exception as e:
            print(f"[LogContextManager] Cleanup failed: {e}")