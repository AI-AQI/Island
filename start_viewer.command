#!/bin/zsh
cd "${0:A:h}"
open 'http://127.0.0.1:8765/viewer/'
python3 -m http.server 8765 --bind 127.0.0.1
