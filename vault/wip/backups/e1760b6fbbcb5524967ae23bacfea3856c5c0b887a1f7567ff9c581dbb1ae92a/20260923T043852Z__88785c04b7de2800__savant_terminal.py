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
    gunmetal_dark: str = "#121212"
    gunmetal_light: str = "#1a1a1a"
    gunmetal_legacy: str = "#3d444d"

    gold: str = "#e6c03b"
    gold_deep: str = "#d8a200"

    pink: str = "#ff4068"

    text: str = "#f4f4ef"
    text_soft: str = "#a3a39f"

    good: str = "#e6c03b"
    warn: str = "#ff4068"
    bad: str = "#ff4068"


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
    shared savant terminal presentation.

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

        color_term = os.environ.get(
            "COLORTERM",
            "",
        ).casefold()

        self.truecolor = (
            self.color
            and (
                "truecolor"
                in color_term
                or "24bit"
                in color_term
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
        if color == palette.pink:
            return "\033[95m"

        if color in {
            palette.gold,
            palette.gold_deep,
        }:
            return "\033[93m"

        if color == palette.text:
            return "\033[97m"

        if color == palette.text_soft:
            return "\033[37m"

        return "\033[90m"

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
            or len(
                value
            )
            < 2
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
                "━"
                if self.unicode
                else "="
            )

        target_width = (
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
                target_width,
            )
        )

    def clear_progress(
        self,
    ) -> None:
        """
        progress is snapshot based.

        carriage-return erasure is
        deliberately not used because
        some terminal transports preserve
        every intermediate carriage-return
        frame as visible output.
        """

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
        if not self.unicode:
            return ">"

        marks = (
            "◈",
            "◆",
            "◇",
            "◊",
        )

        return marks[
            self._phase_index
            % len(
                marks
            )
        ]

    def _box(
        self,
        lines: Sequence[str],
        *,
        accent: str = palette.gold,
        title: str = "",
    ) -> None:
        width = min(
            self.width(),
            104,
        )

        inner = max(
            8,
            width
            - 2,
        )

        top_label = (
            f" {title} "
            if title
            else ""
        )

        remainder = max(
            0,
            inner
            - len(
                top_label
            ),
        )

        if self.unicode:
            top = (
                "╭"
                + top_label
                + (
                    "─"
                    * remainder
                )
                + "╮"
            )

            bottom = (
                "╰"
                + (
                    "─"
                    * inner
                )
                + "╯"
            )

            left = "│"
            right = "│"

        else:
            top = (
                "+"
                + top_label
                + (
                    "-"
                    * remainder
                )
                + "+"
            )

            bottom = (
                "+"
                + (
                    "-"
                    * inner
                )
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

            clipped = visible[
                :max(
                    0,
                    inner
                    - 2,
                )
            ]

            rendered = (
                raw
                if len(
                    visible
                )
                <= inner
                - 2
                else clipped
            )

            padding = max(
                0,
                inner
                - 2
                - len(
                    self.plain(
                        rendered
                    )
                ),
            )

            self.line(
                self.c(
                    left,
                    color=palette.gunmetal_legacy,
                )
                + " "
                + rendered
                + (
                    " "
                    * padding
                )
                + " "
                + self.c(
                    right,
                    color=palette.gunmetal_legacy,
                )
            )

        self.line(
            self.c(
                bottom,
                self.bold,
                color=accent,
            )
        )

    def banner(
        self,
        target: Any = None,
        *,
        detail: str = "",
        destination: str = "",
    ) -> None:
        width = self.width()

        self.line()

        if (
            width >= 72
            and self.unicode
        ):
            for index, row in enumerate(
                self._wordmark
            ):
                color = (
                    palette.gold_deep
                    if index
                    in {
                        0,
                        5,
                    }
                    else palette.gold
                )

                self.line(
                    "  "
                    + self.c(
                        row,
                        self.bold,
                        color=color,
                    )
                )

            self.line(
                "  "
                + self.c(
                    "◆",
                    self.bold,
                    color=palette.pink,
                )
                + " "
                + self.c(
                    (
                        f"{self.application.upper()} "
                        f"// TERMINAL PROJECTION"
                    ),
                    self.bold,
                    color=palette.text,
                )
            )

        else:
            self.line(
                self.c(
                    "◆ SAVANT",
                    self.bold,
                    color=palette.gold,
                )
                + " "
                + self.c(
                    (
                        f"// "
                        f"{self.application}"
                    ),
                    self.bold,
                    color=palette.pink,
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
                    subtitle,
                    color=palette.text_soft,
                )
            )

        if target is not None:
            lines.append(
                self.c(
                    "target      ",
                    self.dim,
                    color=palette.text_soft,
                )
                + self.c(
                    str(
                        target
                    ),
                    color=palette.text,
                )
            )

        if destination:
            lines.append(
                self.c(
                    "projection  ",
                    self.dim,
                    color=palette.text_soft,
                )
                + self.c(
                    destination,
                    color=palette.gold,
                )
            )

        self._box(
            lines
            or [
                "",
            ],
            accent=palette.gold_deep,
            title="savant // active",
        )

        if (
            self.unicode
            and width >= 72
        ):
            rail = (
                "━━"
                + "◆"
                + (
                    "━"
                    * max(
                        8,
                        min(
                            width
                            - 12,
                            76,
                        ),
                    )
                )
                + "◆"
                + "━━"
            )

            self.line(
                "  "
                + self.gradient(
                    rail,
                    start=palette.gunmetal_legacy,
                    end=palette.pink,
                )
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

        stage = (
            f"{self._phase_index:02d}"
        )

        title = self.c(
            (
                f"{stage} / "
                f"{name.casefold()}"
            ),
            self.bold,
            color=palette.gold,
        )

        suffix = ""

        if detail:
            suffix = (
                "  "
                + self.c(
                    detail,
                    color=palette.text_soft,
                )
            )

        self.line()

        self.line(
            self.c(
                marker,
                self.bold,
                color=palette.pink,
            )
            + " "
            + title
            + suffix
        )

        length = max(
            8,
            min(
                self.width()
                - 6,
                86,
            ),
        )

        if self.unicode:
            self.line(
                "  "
                + self.c(
                    (
                        "╺"
                        + (
                            "━"
                            * length
                        )
                        + "╸"
                    ),
                    color=palette.gunmetal_legacy,
                )
            )

        else:
            self.line(
                "  "
                + (
                    "-"
                    * length
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
                palette.pink,
            "bad":
                palette.pink,
            "violet":
                palette.pink,
            "normal":
                palette.text,
        }

        bullet = self.c(
            (
                "◆"
                if self.unicode
                else ">"
            ),
            color=palette.gunmetal_legacy,
        )

        rendered_label = self.c(
            str(
                label
            ).casefold(),
            self.dim,
            color=palette.text_soft,
        )

        rendered_value = self.c(
            value,
            color=colors.get(
                tone,
                palette.text,
            ),
        )

        self.line(
            f"  {bullet} "
            f"{rendered_label:<18} "
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
                end=palette.gold,
            )
            + self.c(
                empty,
                self.dim,
                color=palette.gunmetal_legacy,
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

        bucket = (
            100
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
            and now
            - self.last_render
            < 1.0
        ):
            return

        if (
            not force
            and now
            - self.last_render
            < 0.25
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
            else 28
            if terminal_width < 96
            else 40
        )

        pieces = [
            self.c(
                str(
                    label
                ).casefold(),
                self.bold,
                color=palette.gold,
            ),
            self.bar(
                fraction,
                bar_width,
            ),
            self.c(
                f"{fraction * 100:5.1f}%",
                self.bold,
                color=palette.pink,
            ),
            self.c(
                (
                    f"{safe_current:,}/"
                    f"{safe_total:,}"
                ),
                color=palette.text_soft,
            ),
        ]

        if (
            bytes_total
            and terminal_width >= 72
        ):
            pieces.append(
                self.c(
                    (
                        f"{self.human_bytes(bytes_done)}"
                        f"/"
                        f"{self.human_bytes(bytes_total)}"
                    ),
                    color=palette.text,
                )
            )

        if (
            byte_rate
            and terminal_width >= 86
        ):
            pieces.append(
                self.c(
                    self.rate(
                        byte_rate
                    ),
                    color=palette.gold,
                )
            )

        if (
            eta > 0.5
            and safe_current < safe_total
            and terminal_width >= 100
        ):
            pieces.append(
                self.c(
                    (
                        f"eta "
                        f"{self.duration(eta)}"
                    ),
                    color=palette.text_soft,
                )
            )

        self.line(
            "  "
            + "  ".join(
                pieces
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
            % len(
                frames
            )
        ]

        suffix = ""

        if detail:
            suffix = (
                "  "
                + self.c(
                    detail,
                    color=palette.text_soft,
                )
            )

        self.line(
            "  "
            + self.c(
                marker,
                self.bold,
                color=palette.pink,
            )
            + " "
            + self.c(
                label,
                self.bold,
                color=palette.gold,
            )
            + suffix
        )

    def sparkline(
        self,
        values: Iterable[float],
        *,
        width: int = 24,
    ) -> str:
        sequence = [
            float(
                value
            )
            for value in values
        ]

        if not sequence:
            return ""

        sequence = sequence[
            -max(
                1,
                width,
            ):
        ]

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

        rendered = ""

        for value in sequence:
            index = (
                0
                if span <= 0
                else min(
                    len(
                        characters
                    )
                    - 1,
                    int(
                        (
                            (
                                value
                                - low
                            )
                            / span
                        )
                        * (
                            len(
                                characters
                            )
                            - 1
                        )
                    ),
                )
            )

            rendered += characters[
                index
            ]

        return self.gradient(
            rendered,
            start=palette.gold_deep,
            end=palette.pink,
        )

    def table(
        self,
        rows: Sequence[Sequence[Any]],
        *,
        headers: Sequence[str] | None = None,
    ) -> None:
        data = [
            [
                str(
                    cell
                )
                for cell in row
            ]
            for row in rows
        ]

        if headers:
            data.insert(
                0,
                [
                    str(
                        cell
                    )
                    for cell in headers
                ],
            )

        if not data:
            return

        columns = max(
            len(
                row
            )
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
                    if index < len(
                        row
                    )
                    else ""
                )

                widths[index] = min(
                    30,
                    max(
                        widths[index],
                        len(
                            cell
                        ),
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
                    if index < len(
                        row
                    )
                    else ""
                )

                cell = cell[
                    :widths[index]
                ].ljust(
                    widths[index]
                )

                is_header = (
                    bool(
                        headers
                    )
                    and row_index == 0
                )

                cells.append(
                    self.c(
                        cell,
                        (
                            self.bold
                            if is_header
                            else ""
                        ),
                        color=(
                            palette.gold
                            if is_header
                            else palette.text
                        ),
                    )
                )

            self.line(
                "  "
                + self.c(
                    "│",
                    color=palette.gunmetal_legacy,
                ).join(
                    cells
                )
            )

            if (
                headers
                and row_index == 0
            ):
                self.line(
                    "  "
                    + self.c(
                        "┼".join(
                            "─"
                            * width
                            for width in widths
                        ),
                        color=palette.gunmetal_legacy,
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

        lines = [
            self.c(
                "VERIFIED PROJECTION",
                self.bold,
                color=palette.gold,
            ),
            self.c(
                (
                    "◆ source  "
                    "◆ hash  "
                    "◆ package  "
                    "◆ publish  "
                    "◆ verify"
                ),
                self.bold,
                color=palette.pink,
            ),
        ]

        if source_files:
            lines.append(
                self.c(
                    "source files  ",
                    color=palette.text_soft,
                )
                + self.c(
                    f"{source_files:,}",
                    color=palette.text,
                )
            )

        if artifact_size:
            lines.append(
                self.c(
                    "artifact      ",
                    color=palette.text_soft,
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
                color=palette.text_soft,
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
                    color=palette.text_soft,
                )
                + self.c(
                    value,
                    color=palette.text,
                )
            )

        self.line()

        self._box(
            lines,
            accent=palette.gold,
            title="◆ savant // complete",
        )

        self.line(
            "  "
            + self.c(
                "◆",
                self.bold,
                color=palette.pink,
            )
            + " "
            + self.c(
                (
                    f"{self.application} "
                    f"complete"
                ),
                self.bold,
                color=palette.gold,
            )
        )

        self.line(
            self.c(
                self.rule(),
                color=palette.gunmetal_legacy,
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
                str(
                    message
                ),
                self.bold,
                color=palette.pink,
            ),
        ]

        if detail:
            lines.append(
                self.c(
                    detail,
                    color=palette.text_soft,
                )
            )

        self.line()

        self._box(
            lines,
            accent=palette.pink,
            title="◆ savant // fault",
        )

    def command(
        self,
        command: str,
        *,
        detail: str = "",
    ) -> None:
        suffix = ""

        if detail:
            suffix = (
                "  "
                + self.c(
                    detail,
                    color=palette.text_soft,
                )
            )

        self.line(
            "  "
            + self.c(
                "$",
                self.bold,
                color=palette.pink,
            )
            + " "
            + self.c(
                command,
                self.bold,
                color=palette.gold,
            )
            + suffix
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
