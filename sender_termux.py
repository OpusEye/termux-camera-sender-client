import argparse
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
        "--camera-mode",
        choices=["auto", "camera_index", "input_index"],
        default="auto",
        help="Camera selection mode for android_camera input",
    )
    parser.add_argument("--retry-delay", type=float, default=2.0, help="Retry delay on error")
    return parser.parse_args()


def check_deps() -> bool:
    if shutil.which("ffmpeg") is None:
        print("ffmpeg not found. Install with: pkg install ffmpeg")
        return False
    return True


def supports_camera_index() -> bool:
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-h", "indev=android_camera"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        text = (result.stdout or "") + "\n" + (result.stderr or "")
        return "camera_index" in text
    except Exception:
        return False


def build_command(args, use_camera_index: bool):
    output_url = f"udp://{args.host}:{args.port}?pkt_size=1316"
    gop = max(args.fps * 2, 1)
    input_part = [
        "-f",
        "android_camera",
        "-framerate",
        str(args.fps),
        "-video_size",
        f"{args.width}x{args.height}",
    ]
    if use_camera_index:
        input_part.extend(["-camera_index", str(args.camera_id), "-i", "0"])
    else:
        input_part.extend(["-i", str(args.camera_id)])

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "warning",
        *input_part,
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
    return command


def stream_forever(args):
    if args.camera_mode == "camera_index":
        use_camera_index = True
    elif args.camera_mode == "input_index":
        use_camera_index = False
    else:
        use_camera_index = supports_camera_index()

    print(
        "Camera mode:",
        "camera_index" if use_camera_index else "input_index",
    )
    while True:
        cmd = build_command(args, use_camera_index)
        print("Starting ffmpeg stream:")
        print(" ".join(cmd))
        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            code = proc.returncode
            if code == 0:
                print("ffmpeg exited normally.")
                return
            stderr = proc.stderr or ""
            if "Unrecognized option 'camera_index'" in stderr or "Unrecognized option 'camer_index'" in stderr:
                if use_camera_index:
                    print("camera_index unsupported; switching to input_index mode.")
                    use_camera_index = False
                    continue
            if stderr.strip():
                print(stderr.strip())
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
    if not check_deps():
        return
    stream_forever(args)


if __name__ == "__main__":
    main()
