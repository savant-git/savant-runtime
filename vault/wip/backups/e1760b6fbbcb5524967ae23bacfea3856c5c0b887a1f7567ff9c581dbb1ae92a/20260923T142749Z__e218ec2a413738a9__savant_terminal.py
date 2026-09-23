from __future__ import annotations

from dataclasses import dataclass
import os
import re
import shutil
import sys
import time
from typing import Any, Iterable, Sequence


ansi_pattern = re.compile(
    r"\x1b\[[0-9;]*m"
)


@dataclass(
    frozen=True,
    slots=True,
)
class terminal_palette:
    gunmetal_deep: str = "#11151c"
    gunmetal: str = "#171d27"

    gold_deep: str = "#9d7831"
    gold: str = "#d6b45f"

    hot_pink: str = "#ff2f9d"

    paper: str = "#f1e5c7"
    text: str = "#d8dce3"
    muted: str = "#858e9d"


palette = terminal_palette()


def _hex_rgb(
    value: str,
) -> tuple[int, int, int]:
    clean = value.lstrip("#")

    if len(clean) != 6:
        raise ValueError(
            f"invalid rgb color: {value}"
        )

    return tuple(
        int(
            clean[index:index + 2],
            16,
        )
        for index in (
            0,
            2,
            4,
        )
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

    a = _hex_rgb(start)
    b = _hex_rgb(end)

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

    presentation only.

    command semantics, authority,
    source state, execution behavior,
    and command results remain owned
    by their originating systems.
    """

    reset = "\033[0m"
    bold = "\033[1m"
    dim = "\033[2m"
    italic = "\033[3m"

    _wordmark = (
        "███████╗ █████╗ ██╗   ██╗ █████╗ ███╗   ██╗████████╗",
        "██╔════╝██╔══██╗██║   ██║██╔══██╗████╗  ██║╚══██╔══╝",
        "███████╗███████║██║   ██║███████║██╔██╗ ██║   ██║   ",
        "╚════██║██╔══██║╚██╗ ██╔╝██╔══██║██║╚██╗██║   ██║   ",
        "███████║██║  ██║ ╚████╔╝ ██║  ██║██║ ╚████║   ██║   ",
        "╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   ",
    )

    _compact_mark = (
        "   ╱██████╲   ",
        " ╱██╱    ╲██╲ ",
        " ██╲  ╱██╱    ",
        "   ╲██╲  ╲██  ",
        " ╲██╱    ╲██╱ ",
        "   ╲██████╱   ",
    )

    def __init__(
        self,
        *,
        application: str = "savant",
        subtitle: str = "",
        stream: Any = None,
    ) -> None:
        self.application = (
            str(application).strip()
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

        # Contemporary Termux supports 24-bit ANSI even when
        # COLORTERM is absent. Explicit opt-out remains available.
        self.truecolor = (
            self.color
            and os.environ.get(
                "SAVANT_TRUECOLOR",
                "1",
            ).casefold()
            not in {
                "0",
                "false",
                "no",
                "off",
            }
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
        self.last_snapshot = -1
        self.last_line_width = 0

        self._phase_index = 0

    def width(
        self,
    ) -> int:
        return max(
            44,
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
        background: bool = False,
    ) -> str:
        red, green, blue = _hex_rgb(
            color
        )

        return (
            f"\033["
            f"{48 if background else 38};"
            f"2;"
            f"{red};"
            f"{green};"
            f"{blue}m"
        )

    def _fallback_color(
        self,
        color: str,
    ) -> str:
        if color == palette.hot_pink:
            return "\033[38;5;198m"

        if color == palette.gold:
            return "\033[38;5;179m"

        if color == palette.gold_deep:
            return "\033[38;5;136m"

        if color == palette.paper:
            return "\033[38;5;230m"

        if color == palette.text:
            return "\033[38;5;252m"

        if color == palette.muted:
            return "\033[38;5;102m"

        if color == palette.gunmetal:
            return "\033[38;5;239m"

        return "\033[38;5;236m"

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
        background: str | None = None,
    ) -> str:
        text = str(
            value
        )

        if not self.color:
            return text

        prefix = "".join(
            style
            for style in styles
            if style
        )

        if (
            background
            and self.truecolor
        ):
            prefix += self._rgb(
                background,
                background=True,
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
            value,
        )

    def gradient(
        self,
        value: str,
        *,
        start: str = palette.gold_deep,
        end: str = palette.gold,
        bold: bool = False,
    ) -> str:
        if (
            not self.color
            or not self.truecolor
            or len(value) < 2
        ):
            return self.c(
                value,
                self.bold
                if bold
                else "",
                color=start,
            )

        denominator = max(
            1,
            len(value) - 1,
        )

        pieces: list[str] = []

        for index, character in enumerate(
            value
        ):
            red, green, blue = _interpolate(
                start,
                end,
                index / denominator,
            )

            pieces.append(
                (
                    self.bold
                    if bold
                    else ""
                )
                + f"\033[38;2;"
                + f"{red};"
                + f"{green};"
                + f"{blue}m"
                + character
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
        amount = float(
            max(
                0.0,
                value,
            )
        )

        for unit in (
            "B",
            "KiB",
            "MiB",
            "GiB",
            "TiB",
        ):
            if (
                amount < 1024.0
                or unit == "TiB"
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
            int(seconds),
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
        character = (
            character
            or (
                "━"
                if self.unicode
                else "="
            )
        )

        target = (
            width
            if width is not None
            else min(
                self.width(),
                104,
            )
        )

        return (
            character
            * max(
                1,
                target,
            )
        )

    def clear_progress(
        self,
    ) -> None:
        # Snapshot rendering deliberately avoids carriage-return
        # repainting. Some terminal transports preserve every
        # carriage-return frame and corrupt the visible transcript.
        self.last_line_width = 0

    def line(
        self,
        value: str = "",
    ) -> None:
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
            (
                "◈",
                "◆",
                "◇",
                "◊",
            )
            if self.unicode
            else (
                ">",
                "*",
                "+",
                ">",
            )
        )

        return marks[
            self._phase_index
            % len(marks)
        ]

    def _rail(
        self,
        width: int | None = None,
    ) -> str:
        length = max(
            12,
            (
                width
                or min(
                    self.width(),
                    104,
                )
            )
            - 8,
        )

        if not self.unicode:
            return (
                "["
                + "="
                * max(
                    1,
                    length - 2,
                )
                + "]"
            )

        left = max(
            2,
            length // 3,
        )

        right = max(
            2,
            length
            - left
            - 5,
        )

        return (
            "╾"
            + "━" * left
            + "◆━━◆"
            + "━" * right
            + "╼"
        )

    def _panel(
        self,
        lines: Sequence[str],
        *,
        title: str = "",
        accent: str = palette.gold_deep,
    ) -> None:
        width = min(
            self.width(),
            104,
        )

        inner = max(
            8,
            width - 2,
        )

        label = (
            f" {title} "
            if title
            else ""
        )

        if self.unicode:
            top = (
                "╭"
                + label
                + "─"
                * max(
                    0,
                    inner
                    - len(label),
                )
                + "╮"
            )

            bottom = (
                "╰"
                + "─" * inner
                + "╯"
            )

            left = "│"
            right = "│"

        else:
            top = (
                "+"
                + label
                + "-"
                * max(
                    0,
                    inner
                    - len(label),
                )
                + "+"
            )

            bottom = (
                "+"
                + "-" * inner
                + "+"
            )

            left = "|"
            right = "|"

        self.line(
            self.c(
                top,
                self.bold,
                color=accent,
            )
        )

        for raw in lines:
            visible = self.plain(
                raw
            )

            if len(visible) > inner - 2:
                raw = (
                    visible[
                        :inner - 3
                    ]
                    + "…"
                )

                visible = self.plain(
                    raw
                )

            padding = (
                " "
                * max(
                    0,
                    inner
                    - 2
                    - len(visible),
                )
            )

            self.line(
                self.c(
                    left,
                    color=palette.gunmetal,
                )
                + " "
                + raw
                + padding
                + " "
                + self.c(
                    right,
                    color=palette.gunmetal,
                )
            )

        self.line(
            self.c(
                bottom,
                self.bold,
                color=accent,
            )
        )

    def _sigil(
        self,
    ) -> None:
        width = self.width()

        if (
            width >= 72
            and self.unicode
        ):
            for index, row in enumerate(
                self._wordmark
            ):
                if index in {
                    0,
                    5,
                }:
                    rendered = self.gradient(
                        row,
                        start=palette.gold_deep,
                        end=palette.gold,
                        bold=True,
                    )

                elif index == 2:
                    rendered = self.gradient(
                        row,
                        start=palette.gold,
                        end=palette.hot_pink,
                        bold=True,
                    )

                else:
                    rendered = self.c(
                        row,
                        self.bold,
                        color=palette.gold,
                    )

                self.line(
                    "  "
                    + rendered
                )

            return

        if self.unicode:
            for index, row in enumerate(
                self._compact_mark
            ):
                color = (
                    palette.hot_pink
                    if index in {
                        2,
                        3,
                    }
                    else palette.gold
                )

                self.line(
                    " "
                    + self.c(
                        row,
                        self.bold,
                        color=color,
                    )
                )

            self.line(
                " "
                + self.c(
                    "S A V A N T",
                    self.bold,
                    color=palette.gold,
                )
                + self.c(
                    "  //  ",
                    color=palette.gunmetal,
                )
                + self.c(
                    self.application.upper(),
                    self.bold,
                    color=palette.hot_pink,
                )
            )

        else:
            self.line(
                self.c(
                    "[ S A V A N T ]",
                    self.bold,
                    color=palette.gold,
                )
                + " "
                + self.c(
                    self.application.upper(),
                    self.bold,
                    color=palette.hot_pink,
                )
            )

    def banner(
        self,
        target: Any = None,
        *,
        detail: str = "",
        destination: str = "",
    ) -> None:
        self.line()

        self._sigil()

        self.line(
            "  "
            + self.gradient(
                self._rail(),
                start=palette.gunmetal,
                end=palette.gold_deep,
            )
        )

        subtitle = (
            detail
            or self.subtitle
        )

        lines: list[str] = []

        if subtitle:
            lines.append(
                self.c(
                    "projection  ",
                    color=palette.muted,
                )
                + self.c(
                    subtitle,
                    color=palette.text,
                )
            )

        if target is not None:
            lines.append(
                self.c(
                    "target      ",
                    color=palette.muted,
                )
                + self.c(
                    str(target),
                    self.bold,
                    color=palette.paper,
                )
            )

        if destination:
            lines.append(
                self.c(
                    "destination ",
                    color=palette.muted,
                )
                + self.c(
                    destination,
                    color=palette.gold,
                )
            )

        topology = (
            self.c(
                "SOURCE",
                self.bold,
                color=palette.gold,
            )
            + self.c(
                " ━━◆━━ ",
                color=palette.gunmetal,
            )
            + self.c(
                "HASH",
                self.bold,
                color=palette.gold_deep,
            )
            + self.c(
                " ━━◆━━ ",
                color=palette.gunmetal,
            )
            + self.c(
                "PACKAGE",
                self.bold,
                color=palette.gold,
            )
            + self.c(
                " ━━◆━━ ",
                color=palette.gunmetal,
            )
            + self.c(
                "VERIFY",
                self.bold,
                color=palette.hot_pink,
            )
        )

        lines.append(
            topology
        )

        self._panel(
            lines,
            title=(
                "savant // "
                "deterministic projection"
            ),
            accent=palette.gold_deep,
        )

    def phase(
        self,
        name: str,
        detail: str = "",
    ) -> None:
        self.phase_started = time.monotonic()
        self._phase_index += 1
        self.last_snapshot = -1

        marker = self._phase_mark()
        stage = f"{self._phase_index:02d}"

        self.line()

        self.line(
            self.c(
                "╺━━",
                color=palette.gunmetal,
            )
            + self.c(
                f" {marker} ",
                self.bold,
                color=palette.hot_pink,
            )
            + self.c(
                (
                    f"{stage} // "
                    f"{name.casefold()}"
                ),
                self.bold,
                color=palette.gold,
            )
            + (
                self.c(
                    "  ::  ",
                    color=palette.gunmetal,
                )
                + self.c(
                    detail,
                    color=palette.muted,
                )
                if detail
                else ""
            )
        )

        if self.unicode:
            length = max(
                12,
                min(
                    self.width() - 8,
                    88,
                ),
            )

            pulse = min(
                length - 2,
                max(
                    1,
                    (
                        self._phase_index
                        * 13
                    )
                    % length,
                ),
            )

            rail = (
                "━" * pulse
                + "◆"
                + "━"
                * max(
                    0,
                    length
                    - pulse
                    - 1,
                )
            )

            self.line(
                "   "
                + self.gradient(
                    rail,
                    start=palette.gunmetal,
                    end=palette.gold_deep,
                )
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
                palette.gold,
            "good":
                palette.gold,
            "warn":
                palette.hot_pink,
            "bad":
                palette.hot_pink,
            "violet":
                palette.hot_pink,
            "normal":
                palette.text,
        }

        self.line(
            "   "
            + self.c(
                "◆",
                color=palette.gold_deep,
            )
            + " "
            + self.c(
                f"{str(label).casefold():<11}",
                color=palette.muted,
            )
            + self.c(
                "│ ",
                color=palette.gunmetal,
            )
            + self.c(
                value,
                color=colors.get(
                    tone,
                    palette.text,
                ),
            )
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
        self.field(
            label,
            f"{value} {unit}".rstrip(),
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

        partial = ""

        if (
            self.unicode
            and full < width
        ):
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

            partial = partials[
                min(
                    7,
                    int(
                        (
                            exact
                            - full
                        )
                        * 8
                    ),
                )
            ]

        filled = (
            (
                "█"
                if self.unicode
                else "#"
            )
            * full
            + partial
        )

        empty = (
            (
                "░"
                if self.unicode
                else "-"
            )
            * max(
                0,
                width
                - full
                - (
                    1
                    if partial
                    else 0
                ),
            )
        )

        return (
            self.gradient(
                filled,
                start=palette.gold_deep,
                end=palette.hot_pink,
            )
            + self.c(
                empty,
                color=palette.gunmetal,
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

        safe_total = max(
            0,
            int(total),
        )

        safe_current = max(
            0,
            int(current),
        )

        fraction = min(
            1.0,
            max(
                0.0,
                (
                    safe_current
                    / safe_total
                    if safe_total
                    else 1.0
                ),
            ),
        )

        # Twenty deterministic milestones plus the forced terminal
        # frame bounds transcript output without relying on \r.
        bucket = (
            20
            if safe_current
            >= safe_total
            else int(
                fraction
                * 20
            )
        )

        if (
            not force
            and bucket
            == self.last_snapshot
        ):
            return

        if (
            not force
            and now
            - self.last_render
            < 0.35
        ):
            return

        self.last_render = now
        self.last_snapshot = bucket

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

        terminal_width = self.width()

        bar_width = (
            18
            if terminal_width < 64
            else 30
            if terminal_width < 96
            else 42
        )

        percentage = (
            f"{fraction * 100:5.1f}%"
        )

        self.line(
            "   "
            + self.c(
                "◈",
                self.bold,
                color=palette.hot_pink,
            )
            + " "
            + self.c(
                f"{str(label).casefold():<9}",
                self.bold,
                color=palette.gold,
            )
            + " "
            + self.bar(
                fraction,
                bar_width,
            )
            + " "
            + self.c(
                percentage,
                self.bold,
                color=palette.paper,
            )
        )

        telemetry = [
            (
                f"{safe_current:,}/"
                f"{safe_total:,}"
            ),
        ]

        if bytes_total:
            telemetry.append(
                (
                    f"{self.human_bytes(bytes_done)}"
                    f" / "
                    f"{self.human_bytes(bytes_total)}"
                )
            )

        if (
            byte_rate
            and terminal_width >= 70
        ):
            telemetry.append(
                self.rate(
                    byte_rate
                )
            )

        if (
            eta > 0.5
            and safe_current < safe_total
            and terminal_width >= 86
        ):
            telemetry.append(
                (
                    "eta "
                    + self.duration(
                        eta
                    )
                )
            )

        self.line(
            "     "
            + self.c(
                " ┊ ".join(
                    telemetry
                ),
                color=palette.muted,
            )
        )

    def spinner(
        self,
        label: str,
        *,
        detail: str = "",
        frame: int = 0,
    ) -> None:
        frames = (
            (
                "◢",
                "◣",
                "◤",
                "◥",
            )
            if self.unicode
            else (
                "|",
                "/",
                "-",
                "\\",
            )
        )

        marker = frames[
            frame
            % len(frames)
        ]

        self.line(
            "   "
            + self.c(
                marker,
                self.bold,
                color=palette.hot_pink,
            )
            + " "
            + self.c(
                label,
                self.bold,
                color=palette.gold,
            )
            + (
                "  "
                + self.c(
                    detail,
                    color=palette.muted,
                )
                if detail
                else ""
            )
        )

    def sparkline(
        self,
        values: Iterable[float],
        *,
        width: int = 24,
    ) -> str:
        sequence = [
            float(value)
            for value in values
        ][
            -max(
                1,
                width,
            ):
        ]

        if not sequence:
            return ""

        low = min(
            sequence
        )

        high = max(
            sequence
        )

        characters = (
            "▁▂▃▄▅▆▇█"
            if self.unicode
            else ".:-=+*#@"
        )

        span = (
            high
            - low
        )

        rendered = "".join(
            characters[
                0
                if span <= 0
                else min(
                    len(characters) - 1,
                    int(
                        (
                            (
                                value
                                - low
                            )
                            / span
                        )
                        * (
                            len(characters)
                            - 1
                        )
                    ),
                )
            ]
            for value in sequence
        )

        return self.gradient(
            rendered,
            start=palette.gold_deep,
            end=palette.hot_pink,
        )

    def table(
        self,
        rows: Sequence[Sequence[Any]],
        *,
        headers: Sequence[str] | None = None,
    ) -> None:
        data = [
            [
                str(cell)
                for cell in row
            ]
            for row in rows
        ]

        if headers:
            data.insert(
                0,
                [
                    str(cell)
                    for cell in headers
                ],
            )

        if not data:
            return

        columns = max(
            len(row)
            for row in data
        )

        widths = [
            0
        ] * columns

        for row in data:
            for index in range(
                columns
            ):
                cell = (
                    row[index]
                    if index < len(row)
                    else ""
                )

                widths[index] = min(
                    30,
                    max(
                        widths[index],
                        len(cell),
                    ),
                )

        for row_index, row in enumerate(
            data
        ):
            cells: list[str] = []

            for index in range(
                columns
            ):
                cell = (
                    row[index]
                    if index < len(row)
                    else ""
                )[
                    :widths[index]
                ].ljust(
                    widths[index]
                )

                header = (
                    bool(headers)
                    and row_index == 0
                )

                cells.append(
                    self.c(
                        cell,
                        (
                            self.bold
                            if header
                            else ""
                        ),
                        color=(
                            palette.gold
                            if header
                            else palette.text
                        ),
                    )
                )

            self.line(
                "   "
                + self.c(
                    "│",
                    color=palette.gunmetal,
                ).join(
                    cells
                )
            )

            if (
                headers
                and row_index == 0
            ):
                self.line(
                    "   "
                    + self.c(
                        "┼".join(
                            "─" * width
                            for width
                            in widths
                        ),
                        color=palette.gunmetal,
                    )
                )

    def success(
        self,
        *,
        artifact_size: int = 0,
        source_files: int = 0,
        elapsed: float | None = None,
        **fields: Any,
    ) -> None:
        elapsed_value = (
            time.monotonic()
            - self.started
            if elapsed is None
            else elapsed
        )

        seal = (
            self.c(
                "     ╭──────────╮",
                self.bold,
                color=palette.gold,
            )
            + "\n"
            + self.c(
                "     │",
                color=palette.gold_deep,
            )
            + self.c(
                "    ◆     ",
                self.bold,
                color=palette.hot_pink,
            )
            + self.c(
                "│",
                color=palette.gold_deep,
            )
            + "\n"
            + self.c(
                "     │",
                color=palette.gold_deep,
            )
            + self.c(
                " VERIFIED ",
                self.bold,
                color=palette.paper,
            )
            + self.c(
                "│",
                color=palette.gold_deep,
            )
            + "\n"
            + self.c(
                "     ╰──────────╯",
                self.bold,
                color=palette.gold,
            )
        )

        lines = [
            seal,
            self.c(
                (
                    "source ━◆━ hash ━◆━ "
                    "package ━◆━ publish ━◆━ verify"
                ),
                self.bold,
                color=palette.gold,
            ),
        ]

        if source_files:
            lines.append(
                self.c(
                    "source files  ",
                    color=palette.muted,
                )
                + self.c(
                    f"{source_files:,}",
                    color=palette.paper,
                )
            )

        if artifact_size:
            lines.append(
                self.c(
                    "artifact      ",
                    color=palette.muted,
                )
                + self.c(
                    self.human_bytes(
                        artifact_size
                    ),
                    color=palette.gold,
                )
            )

        lines.append(
            self.c(
                "elapsed       ",
                color=palette.muted,
            )
            + self.c(
                self.duration(
                    elapsed_value
                ),
                color=palette.text,
            )
        )

        for key, value in fields.items():
            if value is None:
                continue

            label = str(
                key
            ).replace(
                "_",
                " ",
            )

            lines.append(
                self.c(
                    f"{label:<13}",
                    color=palette.muted,
                )
                + self.c(
                    value,
                    color=palette.text,
                )
            )

        self.line()

        self._panel(
            lines,
            title=(
                "savant // "
                "verified publication"
            ),
            accent=palette.gold,
        )

        self.line(
            "  "
            + self.gradient(
                self._rail(),
                start=palette.gold_deep,
                end=palette.hot_pink,
            )
        )

    def failure(
        self,
        message: str,
        *,
        detail: str = "",
    ) -> None:
        lines = [
            self.c(
                str(message),
                self.bold,
                color=palette.hot_pink,
            ),
        ]

        if detail:
            lines.append(
                self.c(
                    detail,
                    color=palette.muted,
                )
            )

        self.line()

        self._panel(
            lines,
            title="savant // fault",
            accent=palette.hot_pink,
        )

    def command(
        self,
        command: str,
        *,
        detail: str = "",
    ) -> None:
        self.line(
            "   "
            + self.c(
                "❯",
                self.bold,
                color=palette.hot_pink,
            )
            + " "
            + self.c(
                command,
                self.bold,
                color=palette.gold,
            )
            + (
                "  "
                + self.c(
                    detail,
                    color=palette.muted,
                )
                if detail
                else ""
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
