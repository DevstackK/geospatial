#!/usr/bin/env bash
set -euo pipefail

ffmpeg -y \
  -f lavfi -i "color=c=0x191919:s=1920x1080:d=107.2:r=30" \
  -i assets/tutorial/geoflow-walkthrough-voiceover.mp3 \
  -vf "drawbox=x=0:y=0:w=1920:h=18:color=0xd71920:t=fill,drawbox=x=0:y=1062:w=1920:h=18:color=0xd71920:t=fill,subtitles=assets/tutorial/geoflow-walkthrough.ass" \
  -c:v libx264 -preset veryfast -crf 22 -pix_fmt yuv420p \
  -c:a aac -b:a 160k -shortest \
  assets/tutorial/geoflow-iq-studio-walkthrough.mp4
