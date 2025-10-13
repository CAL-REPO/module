# -*- coding: utf-8 -*-
# log_utils/notifier.py - 예외 발생 시 외부 알림(Hook) 통합 모듈

from __future__ import annotations
import smtplib
from email.mime.text import MIMEText
from types import TracebackType
from typing import Type, Optional, Callable
import traceback


class LogNotifier:
    """
    ✅ LogNotifier
    - 예외 발생 시 이메일, 슬랙, 웹훅 등 외부 알림 전송 담당
    - LogContextManager와 연동하여 자동 호출 가능
    """

    def __init__(
        self,
        on_notify: Optional[Callable[[str], None]] = None,
        *,
        email_host: Optional[str] = None,
        email_port: int = 587,
        email_sender: Optional[str] = None,
        email_password: Optional[str] = None,
        email_recipient: Optional[str] = None,
        slack_webhook_url: Optional[str] = None,
    ):
        self.on_notify = on_notify  # 사용자 정의 콜백
        self.email_host = email_host
        self.email_port = email_port
        self.email_sender = email_sender
        self.email_password = email_password
        self.email_recipient = email_recipient
        self.slack_webhook_url = slack_webhook_url

    # -------------------------------------------------
    # 📧 이메일 알림
    # -------------------------------------------------
    def _send_email(self, subject: str, message: str):
        if not (self.email_host and self.email_sender and self.email_password and self.email_recipient):
            return

        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = self.email_sender
        msg["To"] = self.email_recipient

        try:
            with smtplib.SMTP(self.email_host, self.email_port) as server:
                server.starttls()
                server.login(self.email_sender, self.email_password)
                server.sendmail(self.email_sender, [self.email_recipient], msg.as_string())
        except Exception as e:
            print(f"[LogNotifier] 이메일 전송 실패: {e}")

    # -------------------------------------------------
    # 💬 슬랙 웹훅 알림
    # -------------------------------------------------
    def _send_slack(self, message: str):
        if not self.slack_webhook_url:
            return
        try:
            import requests
            requests.post(self.slack_webhook_url, json={"text": message})
        except Exception as e:
            print(f"[LogNotifier] Slack 전송 실패: {e}")

    # -------------------------------------------------
    # 🚨 통합 알림 트리거
    # -------------------------------------------------

    def notify(
        self,
        title: str,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ):

        tb_text = ''.join(traceback.format_exception(exc_type, exc_val, exc_tb))
        message = f"🚨 {title}에서 예외 발생!\n{exc_val}\n\n{tb_text}"

        # 사용자 정의 콜백이 있으면 우선 실행
        if self.on_notify:
            try:
                self.on_notify(message)
            except Exception as e:
                print(f"[LogNotifier] 사용자 콜백 실행 실패: {e}")

        # 이메일 / 슬랙 순차 전송
        self._send_email(subject=f"[ALERT] {title} 예외 발생", message=message)
        self._send_slack(message)

        print(f"[LogNotifier] 외부 알림 전송 완료: {title}")
