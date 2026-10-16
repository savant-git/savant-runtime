from __future__ import annotations

from dataclasses import dataclass
import math
import os
import re
import shutil
import sys
import time
from typing import Any, Iterable, Sequence


ansi_pattern = re.compile(
    r"\x1b\[[0-9;]*m"
)

truecolor_pattern = re.compile(
    r"\x1b\[38;2;\d+;\d+;\d+m"
)


@dataclass(
    frozen=True,
    slots=True,
)
class terminal_palette:
    night: str = "#030405"
    night_soft: str = "#090b0c"
    ink: str = "#0b0d0e"
    paper: str = "#ece9e0"
    paper_muted: str = "#c7c4bb"
    ice: str = "#9cecff"
    acid: str = "#b8f2dc"
    amber: str = "#ffd397"
    blue: str = "#72ddff"
    green: str = "#98e8c3"
    red: str = "#ff9999"
    violet: str = "#cab7ff"


palette = terminal_palette()


def _hex_rgb(
    value: str,
) -> tuple[int, int, int]:
    clean = value.lstrip("#")

    if len(clean) != 6:
        raise ValueError(
            f"invalid rgb color: {value}"
        )

    return (
        int(
            clean[0:2],
            16,
        ),
        int(
            clean[2:4],
            16,
        ),
        int(
            clean[4:6],
            16,
        ),
    )


def _interpolate(
    start: str,
    end: str,
    fraction: float,
) -> tuple[int, int, int]:
    fraction = min(
        1.0,
        max(
            0.0,
            fraction,
        ),
    )

    a = _hex_rgb(
        start
    )
    b = _hex_rgb(
        end
    )

    return tuple(
        round(
            left
            + (
                right
                - left
            )
            * fraction
        )
        for left, right
        in zip(
            a,
            b,
        )
    )


class terminal_projection:
    """
    shared savant terminal projection.

    this object owns presentation only.

    it does not own command behavior,
    authority, source state, execution
    semantics, or command results.
    """

    reset = "\033[0m"
    bold = "\033[1m"
    dim = "\033[2m"
    italic = "\033[3m"

    def __init__(
        self,
        *,
        application: str = "savant",
        subtitle: str = "",
        stream: Any = None,
    ) -> None:
        self.application = (
            str(
                application
            ).strip()
            or "savant"
        )

        self.subtitle = str(
            subtitle
        ).strip()

        self.stream = (
            stream
            if stream is not None
            else sys.stderr
        )

        self.tty = bool(
            getattr(
                self.stream,
                "isatty",
                lambda: False,
            )()
        )

        term = os.environ.get(
            "TERM",
            "",
        ).casefold()

        self.color = (
            self.tty
            and term != "dumb"
            and "NO_COLOR"
            not in os.environ
            and os.environ.get(
                "SAVANT_COLOR",
                "1",
            ).casefold()
            not in {
                "0",
                "false",
                "no",
                "off",
            }
        )

        self.truecolor = (
            self.color
            and (
                "truecolor"
                in os.environ.get(
                    "COLORTERM",
                    "",
                ).casefold()
                or "24bit"
                in os.environ.get(
                    "COLORTERM",
                    "",
                ).casefold()
                or os.environ.get(
                    "SAVANT_TRUECOLOR",
                    "",
                ).casefold()
                in {
                    "1",
                    "true",
                    "yes",
                    "on",
                }
            )
        )

        self.unicode = (
            os.environ.get(
                "SAVANT_ASCII",
                os.environ.get(
                    "SDUMP_ASCII",
                    "",
                ),
            ).casefold()
            not in {
                "1",
                "true",
                "yes",
                "on",
            }
        )

        self.motion = (
            self.tty
            and os.environ.get(
                "SAVANT_REDUCED_MOTION",
                "",
            ).casefold()
            not in {
                "1",
                "true",
                "yes",
                "on",
            }
        )

        self.started = time.monotonic()
        self.phase_started = self.started
        self.last_render = 0.0
        self.last_line_width = 0
        self._phase_index = 0

    def width(
        self,
    ) -> int:
        return max(
            54,
            min(
                shutil.get_terminal_size(
                    (
                        88,
                        24,
                    )
                ).columns,
                132,
            ),
        )

    def _rgb(
        self,
        color: str,
    ) -> str:
        red, green, blue = _hex_rgb(
            color
        )

        return (
            f"\033[38;2;"
            f"{red};"
            f"{green};"
            f"{blue}m"
        )

    def _fallback_color(
        self,
        color: str,
    ) -> str:
        mapping = {
            palette.ice:
                "\033[96m",
            palette.acid:
                "\033[92m",
            palette.amber:
                "\033[93m",
            palette.blue:
                "\033[94m",
            palette.green:
                "\033[92m",
            palette.red:
                "\033[91m",
            palette.violet:
                "\033[95m",
            palette.paper:
                "\033[97m",
            palette.paper_muted:
                "\033[37m",
        }

        return mapping.get(
            color,
            "\033[37m",
        )

    def color_code(
        self,
        color: str,
    ) -> str:
        if not self.color:
            return ""

        if self.truecolor:
            return self._rgb(
                color
            )

        return self._fallback_color(
            color
        )

    def c(
        self,
        value: Any,
        *styles: str,
        color: str | None = None,
    ) -> str:
        text = str(
            value
        )

        if not self.color:
            return text

        prefix = "".join(
            styles
        )

        if color:
            prefix += self.color_code(
                color
            )

        return (
            prefix
            + text
            + self.reset
        )

    def plain(
        self,
        value: str,
    ) -> str:
        return ansi_pattern.sub(
            "",
            truecolor_pattern.sub(
                "",
                value,
            ),
        )

    def gradient(
        self,
        value: str,
        *,
        start: str = palette.ice,
        end: str = palette.acid,
        bold: bool = False,
    ) -> str:
        if (
            not self.color
            or not self.truecolor
            or len(
                value
            ) < 2
        ):
            styles = (
                (
                    self.bold,
                )
                if bold
                else ()
            )

            return self.c(
                value,
                *styles,
                color=start,
            )

        denominator = max(
            1,
            len(
                value
            )
            - 1,
        )

        pieces: list[str] = []

        for index, character in enumerate(
            value
        ):
            red, green, blue = _interpolate(
                start,
                end,
                index
                / denominator,
            )

            prefix = (
                self.bold
                if bold
                else ""
            )

            pieces.append(
                f"{prefix}"
                f"\033[38;2;"
                f"{red};"
                f"{green};"
                f"{blue}m"
                f"{character}"
            )

        pieces.append(
            self.reset
        )

        return "".join(
            pieces
        )

    def human_bytes(
        self,
        value: float,
    ) -> str:
        units = (
            "B",
            "KiB",
            "MiB",
            "GiB",
            "TiB",
        )

        amount = float(
            max(
                0.0,
                value,
            )
        )

        for unit in units:
            if (
                amount < 1024.0
                or unit
                == units[-1]
            ):
                if unit == "B":
                    return (
                        f"{amount:.0f} "
                        f"{unit}"
                    )

                return (
                    f"{amount:.1f} "
                    f"{unit}"
                )

            amount /= 1024.0

        return (
            f"{amount:.1f} TiB"
        )

    def duration(
        self,
        seconds: float,
    ) -> str:
        seconds_int = max(
            0,
            int(
                seconds
            ),
        )

        if seconds_int < 60:
            return (
                f"{seconds_int}s"
            )

        minutes, remainder = divmod(
            seconds_int,
            60,
        )

        if minutes < 60:
            return (
                f"{minutes}m "
                f"{remainder:02d}s"
            )

        hours, minutes = divmod(
            minutes,
            60,
        )

        return (
            f"{hours}h "
            f"{minutes:02d}m"
        )

    def rate(
        self,
        value: float,
    ) -> str:
        return (
            f"{self.human_bytes(value)}/s"
        )

    def rule(
        self,
        *,
        character: str | None = None,
        width: int | None = None,
    ) -> str:
        if character is None:
            character = (
                "─"
                if self.unicode
                else "-"
            )

        target_width = (
            width
            if width is not None
            else min(
                self.width(),
                92,
            )
        )

        return (
            character
            * max(
                1,
                target_width,
            )
        )

    def clear_progress(
        self,
    ) -> None:
        if (
            not self.tty
            or not self.last_line_width
        ):
            return

        self.stream.write(
            "\r"
            + (
                " "
                * self.last_line_width
            )
            + "\r"
        )

        self.stream.flush()

        self.last_line_width = 0

    def line(
        self,
        value: str = "",
    ) -> None:
        self.clear_progress()

        print(
            value,
            file=self.stream,
            flush=True,
        )

    def _mark(
        self,
    ) -> str:
        return (
            "◆"
            if self.unicode
            else "*"
        )

    def _phase_mark(
        self,
    ) -> str:
        marks = (
            "◇",
            "◈",
            "◊",
            "◆",
        )

        if not self.unicode:
            return ">"

        return marks[
            self._phase_index
            % len(
                marks
            )
        ]

    def banner(
        self,
        target: Any = None,
        *,
        detail: str = "",
        destination: str = "",
    ) -> None:
        rule = self.rule()

        self.line(
            self.c(
                rule,
                self.dim,
                color=palette.blue,
            )
        )

        title = (
            f"savant / "
            f"{self.application}"
        )

        self.line(
            f"{self.c(self._mark(), self.bold, color=palette.ice)} "
            f"{self.gradient(title, bold=True)}"
        )

        subtitle = (
            detail
            or self.subtitle
        )

        if subtitle:
            self.line(
                "  "
                + self.c(
                    subtitle,
                    self.dim,
                    color=palette.paper_muted,
                )
            )

        if target is not None:
            self.field(
                "target",
                str(
                    target
                ),
            )

        if destination:
            self.field(
                "projection",
                destination,
                tone="accent",
            )

        self.line(
            self.c(
                rule,
                self.dim,
                color=palette.blue,
            )
        )

    def phase(
        self,
        name: str,
        detail: str = "",
    ) -> None:
        self.phase_started = time.monotonic()
        self._phase_index += 1

        marker = self._phase_mark()

        rendered_name = self.c(
            name.casefold(),
            self.bold,
            color=palette.ice,
        )

        suffix = ""

        if detail:
            suffix = (
                "  "
                + self.c(
                    detail,
                    self.dim,
                    color=palette.paper_muted,
                )
            )

        self.line(
            f"{self.c(marker, self.bold, color=palette.blue)} "
            f"{rendered_name}"
            f"{suffix}"
        )

    def field(
        self,
        label: str,
        value: Any,
        *,
        tone: str = "normal",
    ) -> None:
        colors = {
            "accent":
                palette.ice,
            "good":
                palette.green,
            "warn":
                palette.amber,
            "bad":
                palette.red,
            "violet":
                palette.violet,
            "normal":
                palette.paper,
        }

        color = colors.get(
            tone,
            palette.paper,
        )

        rendered_label = self.c(
            str(
                label
            ).casefold(),
            self.dim,
            color=palette.paper_muted,
        )

        rendered_value = self.c(
            value,
            color=color,
        )

        self.line(
            f"  {rendered_label:<18} "
            f"{rendered_value}"
        )

    def note(
        self,
        label: str,
        value: str,
        tone: str = "normal",
    ) -> None:
        self.field(
            label,
            value,
            tone=tone,
        )

    def metric(
        self,
        label: str,
        value: Any,
        *,
        unit: str = "",
        tone: str = "accent",
    ) -> None:
        rendered = str(
            value
        )

        if unit:
            rendered = (
                f"{rendered} "
                f"{unit}"
            )

        self.field(
            label,
            rendered,
            tone=tone,
        )

    def bar(
        self,
        fraction: float,
        width: int = 22,
    ) -> str:
        fraction = min(
            1.0,
            max(
                0.0,
                fraction,
            ),
        )

        width = max(
            4,
            width,
        )

        exact = (
            width
            * fraction
        )

        full = int(
            exact
        )

        remainder = (
            exact
            - full
        )

        if self.unicode:
            partials = (
                "",
                "▏",
                "▎",
                "▍",
                "▌",
                "▋",
                "▊",
                "▉",
            )

            partial_index = min(
                7,
                int(
                    remainder
                    * 8
                ),
            )

            partial = (
                partials[
                    partial_index
                ]
                if (
                    full < width
                    and partial_index
                )
                else ""
            )

            empty = max(
                0,
                width
                - full
                - (
                    1
                    if partial
                    else 0
                ),
            )

            filled_text = (
                "█"
                * full
                + partial
            )

            empty_text = (
                "░"
                * empty
            )

        else:
            filled_text = (
                "#"
                * full
            )

            empty_text = (
                "-"
                * (
                    width
                    - full
                )
            )

        if not self.color:
            return (
                filled_text
                + empty_text
            )

        return (
            self.gradient(
                filled_text,
                start=palette.ice,
                end=palette.acid,
            )
            + self.c(
                empty_text,
                self.dim,
                color=palette.paper_muted,
            )
        )

    def progress(
        self,
        *,
        label: str,
        current: int,
        total: int,
        bytes_done: int = 0,
        bytes_total: int = 0,
        force: bool = False,
    ) -> None:
        now = time.monotonic()

        if (
            not force
            and now
            - self.last_render
            < 0.08
        ):
            return

        self.last_render = now

        safe_total = max(
            0,
            int(
                total
            ),
        )

        safe_current = max(
            0,
            int(
                current
            ),
        )

        fraction = (
            safe_current
            / safe_total
            if safe_total
            else 1.0
        )

        fraction = min(
            1.0,
            max(
                0.0,
                fraction,
            ),
        )

        elapsed = max(
            now
            - self.phase_started,
            0.001,
        )

        byte_rate = (
            bytes_done
            / elapsed
            if bytes_done
            else 0.0
        )

        remaining = max(
            bytes_total
            - bytes_done,
            0,
        )

        eta = (
            remaining
            / byte_rate
            if byte_rate > 0
            else 0.0
        )

        percent = (
            fraction
            * 100.0
        )

        terminal_width = self.width()

        bar_width = (
            14
            if terminal_width < 72
            else 22
            if terminal_width < 104
            else 30
        )

        pieces = [
            self.c(
                str(
                    label
                ).casefold(),
                self.bold,
                color=palette.ice,
            ),
            self.bar(
                fraction,
                bar_width,
            ),
            self.c(
                f"{percent:5.1f}%",
                color=palette.acid,
            ),
            self.c(
                f"{safe_current:,}/"
                f"{safe_total:,}",
                self.dim,
                color=palette.paper_muted,
            ),
        ]

        if bytes_total:
            pieces.append(
                self.c(
                    (
                        f"{self.human_bytes(bytes_done)}"
                        f"/"
                        f"{self.human_bytes(bytes_total)}"
                    ),
                    color=palette.paper,
                )
            )

        if byte_rate:
            pieces.append(
                self.c(
                    self.rate(
                        byte_rate
                    ),
                    color=palette.amber,
                )
            )

        if (
            eta > 0.5
            and safe_current
            < safe_total
        ):
            pieces.append(
                self.c(
                    (
                        f"eta "
                        f"{self.duration(eta)}"
                    ),
                    self.dim,
                    color=palette.paper_muted,
                )
            )

        text = (
            "  "
            + "  ".join(
                pieces
            )
        )

        if self.tty:
            plain_width = len(
                self.plain(
                    text
                )
            )

            padding = max(
                0,
                self.last_line_width
                - plain_width,
            )

            self.stream.write(
                "\r"
                + text
                + (
                    " "
                    * padding
                )
            )

            self.stream.flush()

            self.last_line_width = (
                plain_width
            )

        elif (
            force
            or safe_current
            == safe_total
        ):
            self.line(
                text
            )

    def spinner(
        self,
        label: str,
        *,
        detail: str = "",
        frame: int = 0,
    ) -> None:
        if self.unicode:
            frames = (
                "◐",
                "◓",
                "◑",
                "◒",
            )
        else:
            frames = (
                "|",
                "/",
                "-",
                "\\",
            )

        marker = frames[
            frame
            % len(
                frames
            )
        ]

        text = (
            f"  "
            f"{self.c(marker, self.bold, color=palette.ice)} "
            f"{self.c(label.casefold(), self.bold, color=palette.paper)}"
        )

        if detail:
            text += (
                "  "
                + self.c(
                    detail,
                    self.dim,
                    color=palette.paper_muted,
                )
            )

        if self.tty:
            plain_width = len(
                self.plain(
                    text
                )
            )

            padding = max(
                0,
                self.last_line_width
                - plain_width,
            )

            self.stream.write(
                "\r"
                + text
                + (
                    " "
                    * padding
                )
            )

            self.stream.flush()

            self.last_line_width = (
                plain_width
            )

        else:
            self.line(
                text
            )

    def sparkline(
        self,
        values: Sequence[float],
    ) -> str:
        if not values:
            return ""

        if not self.unicode:
            return "".join(
                "."
                if value
                < 0.5
                else "#"
                for value
                in values
            )

        blocks = (
            "▁",
            "▂",
            "▃",
            "▄",
            "▅",
            "▆",
            "▇",
            "█",
        )

        minimum = min(
            values
        )
        maximum = max(
            values
        )

        span = (
            maximum
            - minimum
        )

        if math.isclose(
            span,
            0.0,
        ):
            return (
                blocks[3]
                * len(
                    values
                )
            )

        return "".join(
            blocks[
                min(
                    7,
                    max(
                        0,
                        round(
                            (
                                value
                                - minimum
                            )
                            / span
                            * 7
                        ),
                    ),
                )
            ]
            for value
            in values
        )

    def table(
        self,
        rows: Iterable[
            tuple[Any, Any]
        ],
    ) -> None:
        materialized = [
            (
                str(
                    left
                ),
                str(
                    right
                ),
            )
            for left, right
            in rows
        ]

        if not materialized:
            return

        label_width = min(
            24,
            max(
                len(
                    left
                )
                for left, _
                in materialized
            ),
        )

        for left, right in materialized:
            rendered_left = self.c(
                left.casefold(),
                self.dim,
                color=palette.paper_muted,
            )

            rendered_right = self.c(
                right,
                color=palette.paper,
            )

            self.line(
                f"  "
                f"{rendered_left:<{label_width + 9}} "
                f"{rendered_right}"
            )

    def success(
        self,
        artifact_size: int = 0,
        source_files: int = 0,
        elapsed: float | None = None,
        *,
        message: str | None = None,
    ) -> None:
        self.clear_progress()

        elapsed_value = (
            time.monotonic()
            - self.started
            if elapsed is None
            else elapsed
        )

        marker = (
            "✓"
            if self.unicode
            else "OK"
        )

        label = (
            message
            or (
                f"{self.application} complete"
            )
        )

        self.line()

        self.line(
            f"{self.c(marker, self.bold, color=palette.green)} "
            f"{self.c(label.casefold(), self.bold, color=palette.green)}"
        )

        if source_files:
            self.note(
                "source files",
                f"{source_files:,}",
            )

        if artifact_size:
            self.note(
                "gzip",
                self.human_bytes(
                    artifact_size
                ),
            )

        self.note(
            "elapsed",
            self.duration(
                elapsed_value
            ),
        )

        if (
            self.application
            == "sdump"
        ):
            self.note(
                "local artifact",
                "deleted after verified publication",
                "good",
            )

        self.line(
            self.c(
                self.rule(),
                self.dim,
                color=palette.green,
            )
        )

    def failure(
        self,
        message: str,
    ) -> None:
        self.clear_progress()

        marker = (
            "✕"
            if self.unicode
            else "ERROR"
        )

        self.line()

        self.line(
            f"{self.c(marker, self.bold, color=palette.red)} "
            f"{self.c(f'{self.application} failed', self.bold, color=palette.red)}"
        )

        self.line(
            "  "
            + self.c(
                message,
                color=palette.paper,
            )
        )

        self.line(
            self.c(
                self.rule(),
                self.dim,
                color=palette.red,
            )
        )

    def command(
        self,
        command: str,
        *,
        context: str = "",
    ) -> None:
        marker = (
            "›"
            if self.unicode
            else ">"
        )

        self.line(
            f"{self.c(marker, self.bold, color=palette.violet)} "
            f"{self.c(command, self.bold, color=palette.paper)}"
        )

        if context:
            self.line(
                "  "
                + self.c(
                    context,
                    self.dim,
                    color=palette.paper_muted,
                )
            )


TerminalUI = terminal_projection


def terminal(
    application: str = "savant",
    *,
    subtitle: str = "",
    stream: Any = None,
) -> terminal_projection:
    return terminal_projection(
        application=application,
        subtitle=subtitle,
        stream=stream,
    )
