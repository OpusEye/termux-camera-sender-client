# Termux Camera Sender Client

Android/Termux sender for streaming phone camera via ffmpeg (ndroid_camera -> H.264/MPEG-TS over UDP).

## Important

Termux official fmpeg package usually does **not** include ndroid_camera input device.
If you see:

Unknown input format: 'android_camera'

you must use a custom ffmpeg binary that has ndroid_camera enabled.

## Run

`ash
python sender_termux.py --host <RECEIVER_IP> --port 5001 --camera-id 0 --fps 30 --width 1280 --height 720 --bitrate 4000k
`

With custom ffmpeg binary:

`ash
python sender_termux.py --ffmpeg-bin /data/data/com.termux/files/usr/opt/ffmpeg-cam/bin/ffmpeg --host <RECEIVER_IP> --port 5001 --camera-id 0 --fps 30
`

## Notes

- For front camera usually use --camera-id 1.
- Grant camera permission to Termux.