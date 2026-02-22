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
    parser.add_argument("--retry-delay", type=float, default=2.0, help="Retry delay on error")
    return parser.parse_args()


def check_deps() -> bool:
    if shutil.which("ffmpeg") is None:
        print("ffmpeg not found. Install with: pkg install ffmpeg")
        return False
    return True


def build_command(args):
    output_url = f"udp://{args.host}:{args.port}?pkt_size=1316"
    gop = max(args.fps * 2, 1)
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-f",
        "android_camera",
        "-camera_index",
        str(args.camera_id),
        "-framerate",
        str(args.fps),
        "-video_size",
        f"{args.width}x{args.height}",
        "-i",
        "0",
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
    while True:
        cmd = build_command(args)
        print("Starting ffmpeg stream:")
        print(" ".join(cmd))
        try:
            proc = subprocess.Popen(cmd)
            code = proc.wait()
            if code == 0:
                print("ffmpeg exited normally.")
                return
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
