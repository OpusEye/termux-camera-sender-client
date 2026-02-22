# Termux Camera Sender Client

Android/Termux sender for streaming phone camera via ffmpeg (ndroid_camera -> H.264/MPEG-TS over UDP).

## Install

`ash
pkg update
pkg install git python ffmpeg
git clone https://github.com/OpusEye/termux-camera-sender-client.git
cd termux-camera-sender-client
`

## Run

`ash
python sender_termux.py --host <RECEIVER_IP> --port 5001 --camera-id 0 --fps 30 --width 1280 --height 720 --bitrate 4000k
`

## Notes

- For front camera usually use --camera-id 1.
- Grant camera permission to Termux.