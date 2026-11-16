"""Builds the digest email: subject, HTML and plain text."""

from typing import Protocol, Sequence

from app.application.ports import EmailMessage
from app.domain.agenda import Agenda
from app.domain.recurrence import RescheduledTask
from app.presentation.email import copy


class BodyRenderer(Protocol):
    def render(
        self,
        agenda: Agenda,
        rescheduled: Sequence[RescheduledTask],
        warnings: Sequence[str],
    ) -> str:
        """Renders one body format."""


class DigestEmailComposer:
    def __init__(self, html_renderer: BodyRenderer, text_renderer: BodyRenderer):
        self._html = html_renderer
        self._text = text_renderer

    def compose(
        self,
        agenda: Agenda,
        rescheduled: Sequence[RescheduledTask],
        warnings: Sequence[str],
    ) -> EmailMessage:
        return EmailMessage(
            subject=copy.subject(agenda),
            html=self._html.render(agenda, rescheduled, warnings),
            text=self._text.render(agenda, rescheduled, warnings),
        )
