import argparse
import os
import shutil
import socket
import struct
import subprocess
import time


def parse_args():
    parser = argparse.ArgumentParser(description="Termux camera sender (termux-camera-photo)")
    parser.add_argument("--host", required=True, help="Receiver host/IP")
    parser.add_argument("--port", type=int, default=5001, help="Receiver TCP port")
    parser.add_argument("--token", required=True, help="Shared auth token")
    parser.add_argument("--camera-id", type=int, default=0, help="Android camera index")
    parser.add_argument("--fps", type=float, default=1.0, help="Capture FPS (recommended: 0.5-2)")
    parser.add_argument(
        "--tmp-file",
        default="/data/data/com.termux/files/usr/tmp/cam_frame.jpg",
        help="Temporary file for captured frame",
    )
    parser.add_argument("--connect-timeout", type=float, default=10.0, help="TCP connect timeout")
    parser.add_argument("--retry-delay", type=float, default=2.0, help="Retry delay")
    return parser.parse_args()


def check_deps() -> bool:
    if shutil.which("termux-camera-photo") is None:
        print("termux-camera-photo not found.")
        print("Install: pkg install termux-api")
        print("Also install Android app: Termux:API")
        return False
    return True


def capture_frame(camera_id: int, tmp_file: str) -> bytes:
    if os.path.exists(tmp_file):
        try:
            os.remove(tmp_file)
        except OSError:
            pass

    cmd = ["termux-camera-photo", "-c", str(camera_id), tmp_file]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "capture failed").strip())

    with open(tmp_file, "rb") as f:
        data = f.read()
    if not data:
        raise RuntimeError("empty frame file")
    return data


def stream_forever(args):
    if args.fps <= 0:
        raise ValueError("fps must be > 0")
    frame_interval = 1.0 / args.fps
    os.makedirs(os.path.dirname(args.tmp_file), exist_ok=True)

    while True:
        sock = None
        try:
            print(f"Connecting to {args.host}:{args.port} ...")
            sock = socket.create_connection((args.host, args.port), timeout=args.connect_timeout)
            sock.sendall(f"HELLO {args.token}\n".encode("utf-8"))
            print("Connected. Streaming...")
            sent = 0
            while True:
                t0 = time.time()
                frame = capture_frame(args.camera_id, args.tmp_file)
                sock.sendall(struct.pack(">I", len(frame)))
                sock.sendall(frame)
                sent += 1
                print(f"Sent frame #{sent}, bytes={len(frame)}")
                elapsed = time.time() - t0
                wait = frame_interval - elapsed
                if wait > 0:
                    time.sleep(wait)
        except KeyboardInterrupt:
            print("Stopped by user.")
            return
        except Exception as exc:
            print(f"Stream error: {exc}")
            print(f"Retrying in {args.retry_delay}s...")
            time.sleep(args.retry_delay)
        finally:
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass


def main():
    args = parse_args()
    if not check_deps():
        return
    stream_forever(args)


if __name__ == "__main__":
    main()
