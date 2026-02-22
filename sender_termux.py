import argparse
import os
import shutil
import subprocess
import time


def parse_args():
    parser = argparse.ArgumentParser(description="Termux 30 FPS camera sender (H264)")
    parser.add_argument("--host", required=True, help="Receiver IP/host")
    parser.add_argument("--port", type=int, default=5001, help="Receiver UDP port")
    parser.add_argument("--camera-id", type=int, default=0, help="Android camera index")
    parser.add_argument("--fps", type=int, default=30, help="Target FPS (e.g. 30)")
    parser.add_argument("--width", type=int, default=1280, help="Capture width")
    parser.add_argument("--height", type=int, default=720, help="Capture height")
    parser.add_argument("--bitrate", default="4000k", help="Video bitrate (example: 4000k)")
    parser.add_argument(
        "--ffmpeg-bin",
        default="ffmpeg",
        help="Path to ffmpeg binary (default: ffmpeg from PATH)",
    )
    parser.add_argument(
        "--camera-mode",
        choices=["auto", "camera_index", "input_index"],
        default="auto",
        help="Camera selection mode for android_camera input",
    )
    parser.add_argument("--retry-delay", type=float, default=2.0, help="Retry delay on error")
    return parser.parse_args()


def check_deps(ffmpeg_bin: str) -> bool:
    if "/" in ffmpeg_bin:
        exists = shutil.which(ffmpeg_bin) is not None or os.path.exists(ffmpeg_bin)
    else:
        exists = shutil.which(ffmpeg_bin) is not None
    if not exists:
        print(f"ffmpeg binary not found: {ffmpeg_bin}")
        print("Install with: pkg install ffmpeg")
        return False
    return True


def run_cmd(cmd, timeout=None):
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=timeout,
    )


def supports_camera_index(ffmpeg_bin: str) -> bool:
    try:
        result = run_cmd([ffmpeg_bin, "-hide_banner", "-h", "indev=android_camera"])
        text = (result.stdout or "") + "\n" + (result.stderr or "")
        return "camera_index" in text
    except Exception:
        return False


def get_input_variants(args):
    camera_variants = [
        ["-camera_index", str(args.camera_id), "-i", "0"],
        ["-camera_index", str(args.camera_id), "-i", "dummy"],
    ]
    input_variants = [
        ["-i", str(args.camera_id)],
        ["-i", "0"],
        ["-i", "0:0"],
    ]

    if args.camera_mode == "camera_index":
        return camera_variants
    if args.camera_mode == "input_index":
        return input_variants

    if supports_camera_index(args.ffmpeg_bin):
        return camera_variants + input_variants
    return input_variants + camera_variants


def unique_resolutions(width, height):
    candidates = [(width, height), (960, 540), (640, 480)]
    seen = set()
    result = []
    for item in candidates:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def probe_input_settings(args):
    variants = get_input_variants(args)
    resolutions = unique_resolutions(args.width, args.height)
    errors = []

    for w, h in resolutions:
        for input_args in variants:
            cmd = [
                args.ffmpeg_bin,
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "android_camera",
                "-framerate",
                str(args.fps),
                "-video_size",
                f"{w}x{h}",
                *input_args,
                "-t",
                "1",
                "-an",
                "-f",
                "null",
                "-",
            ]
            try:
                result = run_cmd(cmd, timeout=12)
            except Exception as exc:
                errors.append(f"{input_args} @ {w}x{h}: {exc}")
                continue

            if result.returncode == 0:
                return input_args, w, h

            stderr = (result.stderr or "").strip()
            if "Unknown input format: 'android_camera'" in stderr:
                raise RuntimeError(
                    "Your ffmpeg build does not support android_camera input. "
                    "Install a Termux ffmpeg build with android_camera enabled."
                )
            errors.append(f"{input_args} @ {w}x{h}: {stderr or 'unknown error'}")

    details = "\n".join(errors[-6:])
    raise RuntimeError(f"Failed to open Android camera.\nRecent probe errors:\n{details}")


def build_stream_command(args, input_args, width, height):
    output_url = f"udp://{args.host}:{args.port}?pkt_size=1316"
    gop = max(args.fps * 2, 1)
    return [
        args.ffmpeg_bin,
        "-hide_banner",
        "-loglevel",
        "warning",
        "-f",
        "android_camera",
        "-framerate",
        str(args.fps),
        "-video_size",
        f"{width}x{height}",
        *input_args,
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-tune",
        "zerolatency",
        "-pix_fmt",
        "yuv420p",
        "-g",
        str(gop),
        "-b:v",
        args.bitrate,
        "-maxrate",
        args.bitrate,
        "-bufsize",
        args.bitrate,
        "-f",
        "mpegts",
        output_url,
    ]


def stream_forever(args):
    try:
        input_args, real_w, real_h = probe_input_settings(args)
    except Exception as exc:
        print(str(exc))
        return

    print(f"Selected camera args: {' '.join(input_args)}")
    print(f"Selected resolution: {real_w}x{real_h}")

    while True:
        cmd = build_stream_command(args, input_args, real_w, real_h)
        print("Starting ffmpeg stream:")
        print(" ".join(cmd))
        try:
            proc = run_cmd(cmd)
            code = proc.returncode
            if code == 0:
                print("ffmpeg exited normally.")
                return
            stderr = (proc.stderr or "").strip()
            if stderr:
                print(stderr)
            print(f"ffmpeg exited with code {code}. Retrying in {args.retry_delay}s...")
            time.sleep(args.retry_delay)
        except KeyboardInterrupt:
            print("Stopped by user.")
            return
        except Exception as exc:
            print(f"Failed to start stream: {exc}")
            print(f"Retrying in {args.retry_delay}s...")
            time.sleep(args.retry_delay)


def main():
    args = parse_args()
    if not check_deps(args.ffmpeg_bin):
        return
    stream_forever(args)


if __name__ == "__main__":
    main()
