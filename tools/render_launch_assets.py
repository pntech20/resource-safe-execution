"""Render deterministic launch assets.

This development helper uses Pillow when it is already available. Pillow is
not part of the skill runtime and is not installed by the skill.
"""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover - local rendering dependency
    raise SystemExit(
        "Pillow is required only to render launch assets; "
        "do not add it to the skill runtime."
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "assets" / "launch"
SOCIAL = ASSET_DIR / "resource-safe-execution-social-preview.png"
DEMO = ASSET_DIR / "resource-safe-execution-demo.gif"

INK = "#f8fafc"
MUTED = "#94a3b8"
SOFT = "#cbd5e1"
CYAN = "#38bdf8"
BACKGROUND = "#07111b"
PANEL = "#0d2433"
BORDER = "#28516a"
GRID = "#173044"
RED = "#fb7185"
GREEN = "#4ade80"


def _font(size: int, *, bold: bool = False, mono: bool = False):
    windows = Path("C:/Windows/Fonts")
    if mono:
        names = (
            "consolab.ttf" if bold else "consola.ttf",
            "DejaVuSansMono-Bold.ttf" if bold else "DejaVuSansMono.ttf",
        )
    elif bold:
        names = ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf")
    else:
        names = ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf")

    candidates: list[str | Path] = []
    for name in names:
        candidates.extend((windows / name, name))
    for candidate in candidates:
        try:
            return ImageFont.truetype(str(candidate), size=size)
        except OSError:
            continue
    raise RuntimeError(f"No suitable local font found for {size}px text")


def _text_width(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def _draw_grid(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    for x in range(0, width + 1, 160):
        draw.line((x, 0, x, height), fill=GRID, width=1)
    for y in range(0, height + 1, 112):
        draw.line((0, y, width, y), fill=GRID, width=1)


def render_social_preview() -> None:
    image = Image.new("RGB", (1280, 640), BACKGROUND)
    draw = ImageDraw.Draw(image)
    _draw_grid(draw, 1280, 640)

    draw.rounded_rectangle((56, 58, 64, 402), radius=4, fill=CYAN)
    for x, filled in ((1068, False), (1124, False), (1180, True)):
        draw.ellipse(
            (x - 18, 66, x + 18, 102),
            fill=CYAN if filled else "#0f2636",
            outline=CYAN,
            width=3,
        )

    draw.text(
        (88, 68),
        "RESOURCE SAFE EXECUTION",
        fill=CYAN,
        font=_font(30, bold=True),
    )
    draw.text(
        (84, 142),
        "Heavy agent jobs.",
        fill=INK,
        font=_font(78, bold=True),
    )
    draw.text(
        (84, 234),
        "Responsive workstation.",
        fill=CYAN,
        font=_font(78, bold=True),
    )
    draw.text(
        (86, 354),
        "Bound concurrency · Verify GPU use · Own process cleanup",
        fill=SOFT,
        font=_font(30),
    )

    pills = (
        ((84, 438, 366, 496), "01 · PREFLIGHT", 112),
        ((384, 438, 636, 496), "02 · BOUND", 412),
        ((654, 438, 922, 496), "03 · CLEAN", 682),
    )
    for rect, text, text_x in pills:
        draw.rounded_rectangle(rect, radius=29, fill=PANEL, outline=BORDER, width=2)
        draw.text((text_x, 449), text, fill=INK, font=_font(30, bold=True))

    draw.text(
        (84, 524),
        "Agent Skill · Windows · macOS · Linux",
        fill=MUTED,
        font=_font(30, bold=True),
    )
    draw.text(
        (84, 570),
        "github.com/pntech20/resource-safe-execution",
        fill=INK,
        font=_font(30, bold=True),
    )

    draw.rectangle((1010, 462, 1200, 558), fill="#0a1b27", outline=BORDER, width=2)
    draw.line(
        ((1040, 528), (1072, 496), (1106, 518), (1166, 454)),
        fill=CYAN,
        width=8,
        joint="curve",
    )

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    image.save(SOCIAL, format="PNG", optimize=True, compress_level=9)


def _frame_base(
    number: int,
    timing: str,
    title: str,
    caption: str,
) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (1200, 675), BACKGROUND)
    draw = ImageDraw.Draw(image)
    _draw_grid(draw, 1200, 675)

    draw.rounded_rectangle((48, 34, 510, 82), radius=24, fill=PANEL, outline=BORDER)
    draw.text(
        (70, 45),
        "RECORDED EVALUATION PLAYBACK",
        fill=CYAN,
        font=_font(24, bold=True),
    )
    draw.text(
        (1110, 45),
        timing,
        fill=MUTED,
        font=_font(24, mono=True),
        anchor="ra",
    )
    draw.text(
        (50, 108),
        f"0{number}",
        fill=CYAN,
        font=_font(34, bold=True, mono=True),
    )
    draw.text((112, 104), title, fill=INK, font=_font(48, bold=True))

    draw.rounded_rectangle((48, 578, 1152, 638), radius=20, fill="#091d2a")
    draw.text((78, 592), caption, fill=SOFT, font=_font(30, bold=True))

    segment_width = 1104 / 7
    for index in range(7):
        x0 = int(48 + index * segment_width)
        x1 = int(48 + (index + 1) * segment_width - 8)
        draw.rounded_rectangle(
            (x0, 652, x1, 660),
            radius=4,
            fill=CYAN if index < number else BORDER,
        )
    return image, draw


def _card(
    draw: ImageDraw.ImageDraw,
    rect: tuple[int, int, int, int],
    heading: str,
    value: str,
    *,
    accent: str = CYAN,
) -> None:
    draw.rounded_rectangle(rect, radius=18, fill=PANEL, outline=BORDER, width=2)
    x0, y0, _, _ = rect
    draw.text((x0 + 22, y0 + 18), heading, fill=MUTED, font=_font(24, bold=True))
    draw.text((x0 + 22, y0 + 58), value, fill=accent, font=_font(32, bold=True))


def _scene_pain() -> Image.Image:
    image, draw = _frame_base(1, "0–4s", "A heavy request arrives", "Agents guess. Your workstation pays.")
    draw.rounded_rectangle((72, 182, 1128, 486), radius=24, fill=PANEL, outline=BORDER, width=2)
    draw.text((104, 214), "REQUEST", fill=CYAN, font=_font(26, bold=True))
    draw.text((104, 266), "8 browser workers", fill=INK, font=_font(48, bold=True))
    draw.text((104, 326), "+ emulator + 2 builds", fill=INK, font=_font(48, bold=True))
    draw.line((770, 230, 770, 438), fill=BORDER, width=2)
    draw.text((814, 246), "INTERACTIVE PC", fill=MUTED, font=_font(26, bold=True))
    draw.text((814, 300), "keep responsive", fill=GREEN, font=_font(36, bold=True))
    draw.text((814, 362), "no blind launch", fill=RED, font=_font(32, bold=True))
    return image


def _scene_preflight() -> Image.Image:
    image, draw = _frame_base(2, "4–10s", "Read-only preflight", "Inspect before launching.")
    _card(draw, (72, 184, 334, 330), "CPU · 12 LOGICAL", "41.7% sampled")
    _card(draw, (350, 184, 628, 330), "MEMORY AVAILABLE", "18.6 / 34.2 GB")
    _card(draw, (644, 184, 906, 330), "DISK FREE", "28.7 GB")
    _card(draw, (922, 184, 1128, 330), "GPU VISIBILITY", "3 visible")
    draw.rounded_rectangle((72, 356, 1128, 492), radius=22, fill="#091d2a", outline=BORDER, width=2)
    draw.text((104, 382), "APPLICATION BACKEND", fill=MUTED, font=_font(26, bold=True))
    draw.text((104, 428), "UNVERIFIED", fill=RED, font=_font(42, bold=True))
    draw.text(
        (420, 430),
        "Fresh aggregate snapshot · values vary by machine",
        fill=SOFT,
        font=_font(28),
    )
    return image


def _scene_bounded() -> Image.Image:
    image, draw = _frame_base(3, "10–17s", "Derive the cap", "Bound concurrency from current headroom.")
    stages = (
        (72, "8 REQUESTED", INK),
        (366, "1-WORKER SMOKE", CYAN),
        (700, "MEASURED CAP", GREEN),
    )
    for x, text, color in stages:
        draw.rounded_rectangle((x, 206, x + 260, 302), radius=18, fill=PANEL, outline=BORDER, width=2)
        draw.text((x + 24, 237), text, fill=color, font=_font(28, bold=True))
    draw.line((334, 254, 354, 254), fill=CYAN, width=5)
    draw.line((628, 254, 688, 254), fill=CYAN, width=5)
    draw.polygon(((354, 254), (340, 244), (340, 264)), fill=CYAN)
    draw.polygon(((688, 254), (674, 244), (674, 264)), fill=CYAN)

    draw.rounded_rectangle((72, 338, 1128, 492), radius=22, fill="#091d2a", outline=BORDER, width=2)
    draw.text(
        (106, 368),
        "W = min(request, CPU cap, memory cap)",
        fill=INK,
        font=_font(36, bold=True, mono=True),
    )
    draw.text(
        (106, 430),
        "No fixed worker count · unknown gate → serialize",
        fill=MUTED,
        font=_font(30),
    )
    return image


def _scene_gpu() -> Image.Image:
    image, draw = _frame_base(4, "17–23s", "Prove acceleration", "Hardware detected ≠ workload accelerated.")
    labels = (
        ("1", "DEVICE", GREEN),
        ("2", "DRIVER / API", CYAN),
        ("3", "APP BACKEND", CYAN),
        ("4", "TEST WORKLOAD", CYAN),
        ("5", "OBSERVE", CYAN),
    )
    x = 58
    for number, label, color in labels:
        draw.rounded_rectangle((x, 210, x + 204, 336), radius=20, fill=PANEL, outline=BORDER, width=2)
        draw.text((x + 20, 230), number, fill=color, font=_font(28, bold=True, mono=True))
        if label == "TEST WORKLOAD":
            draw.text((x + 20, 270), "TEST", fill=INK, font=_font(24, bold=True))
            draw.text((x + 20, 300), "WORKLOAD", fill=INK, font=_font(24, bold=True))
        else:
            draw.text((x + 20, 282), label, fill=INK, font=_font(25, bold=True))
        x += 222
    draw.rounded_rectangle((86, 382, 1114, 490), radius=20, fill="#091d2a", outline=BORDER, width=2)
    draw.text((120, 408), "VISIBLE", fill=GREEN, font=_font(32, bold=True))
    draw.text((304, 408), "≠", fill=CYAN, font=_font(38, bold=True))
    draw.text((380, 408), "BACKEND VERIFIED", fill=RED, font=_font(32, bold=True))
    draw.text((760, 414), "keep unsuitable work on CPU", fill=SOFT, font=_font(25))
    return image


def _scene_ownership() -> Image.Image:
    image, draw = _frame_base(5, "23–31s", "Own every launch", "Track what the agent starts.")
    draw.rounded_rectangle((72, 180, 722, 506), radius=22, fill="#091d2a", outline=BORDER, width=2)
    code = (
        '{',
        '  "root_pid": "<recorded>",',
        '  "start_identity": "<verified>",',
        '  "purpose": "<bounded>",',
        '  "child_group": "<owned>"',
        '}',
    )
    y = 206
    for line in code:
        draw.text((106, y), line, fill=INK if ":" in line else MUTED, font=_font(28, mono=True))
        y += 45

    draw.rounded_rectangle((758, 180, 1128, 322), radius=22, fill="#2a101a", outline=RED, width=3)
    draw.text((792, 210), "REFUSE", fill=RED, font=_font(32, bold=True))
    draw.text((792, 260), "kill by name", fill=INK, font=_font(34, bold=True))
    draw.rounded_rectangle((758, 348, 1128, 506), radius=22, fill=PANEL, outline=BORDER, width=2)
    draw.text((792, 374), "VERIFY", fill=GREEN, font=_font(32, bold=True))
    draw.text((792, 424), "PID + start identity", fill=INK, font=_font(28, bold=True))
    draw.text((792, 462), "before any signal", fill=SOFT, font=_font(25))
    return image


def _scene_cleanup() -> Image.Image:
    image, draw = _frame_base(6, "31–36s", "Clean the owned tree", "Clean up only owned work.")
    steps = (
        ("01", "Re-read PID + start identity"),
        ("02", "Request recorded graceful stop"),
        ("03", "Escalate inside owned group only"),
        ("04", "Verify the root and children exited"),
    )
    y = 184
    for number, text in steps:
        draw.rounded_rectangle((72, y, 1128, y + 76), radius=18, fill=PANEL, outline=BORDER, width=2)
        draw.text((100, y + 20), number, fill=CYAN, font=_font(28, bold=True, mono=True))
        draw.text((180, y + 18), text, fill=INK, font=_font(30, bold=True))
        y += 92
    return image


def _scene_cta() -> Image.Image:
    image, draw = _frame_base(7, "36–38s", "Install the reviewed skill", "Heavy agent jobs. Responsive workstation.")
    draw.rounded_rectangle((72, 180, 1128, 354), radius=22, fill="#091d2a", outline=CYAN, width=3)
    draw.text(
        (102, 200),
        "npx --yes skills@1.5.20 add",
        fill=INK,
        font=_font(30, bold=True, mono=True),
    )
    draw.text(
        (102, 250),
        "pntech20/resource-safe-execution",
        fill=CYAN,
        font=_font(30, bold=True, mono=True),
    )
    draw.text(
        (102, 300),
        "--skill resource-safe-execution --copy",
        fill=INK,
        font=_font(30, bold=True, mono=True),
    )
    draw.rounded_rectangle((72, 384, 1128, 500), radius=22, fill=PANEL, outline=BORDER, width=2)
    draw.text((102, 408), "SKILL RUNTIME", fill=GREEN, font=_font(26, bold=True))
    draw.text((330, 408), "no network · no telemetry", fill=INK, font=_font(27, bold=True))
    draw.text((102, 454), "SKILLS CLI", fill=CYAN, font=_font(26, bold=True))
    draw.text(
        (330, 454),
        "anonymous, opt-out install telemetry",
        fill=SOFT,
        font=_font(27, bold=True),
    )
    return image


def render_demo() -> list[Image.Image]:
    frames = [
        _scene_pain(),
        _scene_preflight(),
        _scene_bounded(),
        _scene_gpu(),
        _scene_ownership(),
        _scene_cleanup(),
        _scene_cta(),
    ]
    durations_ms = [4000, 6000, 7000, 6000, 8000, 5000, 2000]
    assert sum(durations_ms) == 38_000

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        DEMO,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=durations_ms,
        loop=0,
        optimize=True,
        disposal=2,
    )
    return frames


def render_inspection_copies(
    frames: list[Image.Image],
    destination: Path,
) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    social = Image.open(SOCIAL)
    social.resize((640, 320), Image.Resampling.LANCZOS).save(
        destination / "social-preview-640x320.png"
    )

    mobile_frames = []
    for index, frame in enumerate(frames, start=1):
        frame.save(destination / f"demo-frame-{index:02d}.png")
        mobile_frames.append(
            frame.resize((360, 203), Image.Resampling.LANCZOS)
        )

    sheet = Image.new("RGB", (720, 812), BACKGROUND)
    for index, frame in enumerate(mobile_frames):
        x = (index % 2) * 360
        y = (index // 2) * 203
        sheet.paste(frame, (x, y))
    sheet.save(destination / "demo-mobile-contact-sheet.png")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inspection-dir",
        type=Path,
        help="Optional directory for review-only PNG copies.",
    )
    args = parser.parse_args()

    render_social_preview()
    frames = render_demo()
    if args.inspection_dir:
        render_inspection_copies(frames, args.inspection_dir)
    print(
        f"Rendered {SOCIAL.relative_to(ROOT)} "
        f"({SOCIAL.stat().st_size} bytes)"
    )
    print(
        f"Rendered {DEMO.relative_to(ROOT)} "
        f"({DEMO.stat().st_size} bytes)"
    )


if __name__ == "__main__":
    main()
