#!/data/data/com.termux/files/usr/bin/bash
# PocketMind — one-shot Termux setup.
# Run this INSIDE Termux on the phone (not over adb shell — Termux's own
# user space isn't reachable that way; open the Termux app itself).
#
# What this does, in order:
#   1. Installs build tools and Python.
#   2. Builds the real llama.cpp llama-server binary from source (same
#      binary validated on the laptop — not llama-cpp-python's server,
#      which has a different HTTP API; this script and engine/llama_client.py
#      must stay matched to the native llama.cpp server).
#   3. Downloads the Qwen2.5-0.5B-Instruct Q4_K_M GGUF (~400MB — this will
#      take a while and use real mobile data if not on Wi-Fi; it pauses to
#      ask first). 0.5B is the default: on-device benchmarking (phone:
#      Redmi 24116RNC1I, 3.5GB RAM) showed it answers the same grounded
#      rephrase task in ~15s vs 42-83s for 1.5B, with no quality loss found
#      — the architecture never lets the model invent facts, it only
#      rephrases pre-verified retrieved content, so the smaller model's
#      weaker open-ended reasoning doesn't hurt this specific task.
#   4. Starts llama-server on :8080 and the PocketMind demo app on :8090.
#   5. Takes a wake-lock so Android doesn't kill the process mid-demo.
set -euo pipefail

echo "=== PocketMind Termux setup ==="

echo "--- 1/5: installing packages ---"
pkg update -y
pkg install -y python git cmake clang make openssl binutils termux-api python-pillow python-numpy

echo "--- 2/5: wake lock (stops Android suspending Termux mid-demo) ---"
termux-wake-lock || echo "termux-wake-lock failed — install Termux:API app from F-Droid if missing."

PM_DIR="$HOME/pocketmind"
mkdir -p "$PM_DIR"

echo "--- 3/5: building llama.cpp (takes several minutes on a phone CPU) ---"
if [ ! -x "$PM_DIR/llama.cpp/build/bin/llama-server" ]; then
  cd "$PM_DIR"
  if [ ! -d llama.cpp ]; then
    git clone --depth 1 https://github.com/ggerganov/llama.cpp.git
  fi
  cd llama.cpp
  cmake -B build -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=Release
  cmake --build build --config Release -j"$(nproc)" --target llama-server
else
  echo "llama-server already built, skipping."
fi

echo "--- 4/5: downloading Qwen2.5-0.5B-Instruct (Q4_K_M, ~400MB) ---"
MODEL_DIR="$PM_DIR/models"
MODEL_FILE="$MODEL_DIR/Qwen2.5-0.5B-Instruct-Q4_K_M.gguf"
mkdir -p "$MODEL_DIR"
if [ ! -f "$MODEL_FILE" ]; then
  echo "About to download ~400MB. Make sure you're on Wi-Fi. Press Enter to continue, Ctrl+C to abort."
  read -r _
  curl -L -o "$MODEL_FILE" \
    "https://huggingface.co/bartowski/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/Qwen2.5-0.5B-Instruct-Q4_K_M.gguf"
else
  echo "Model already downloaded, skipping."
fi

echo "--- 5/5: starting llama-server (port 8080) ---"
pkill -f llama-server 2>/dev/null || true
nohup "$PM_DIR/llama.cpp/build/bin/llama-server" \
  --model "$MODEL_FILE" \
  --host 127.0.0.1 --port 8080 \
  --ctx-size 2048 --threads "$(nproc)" \
  > "$PM_DIR/llama-server.log" 2>&1 < /dev/null &
disown
sleep 3
echo "llama-server starting in background — log: $PM_DIR/llama-server.log"
echo ""
echo "Next: copy this project's engine/, agrilens/, advice_bank/, learnloop/"
echo "folders onto the phone (next to this script, i.e. into $PM_DIR), then run:"
echo "  cd $PM_DIR && pkill -f 'engine/app.py'; nohup python3 engine/app.py > app.log 2>&1 < /dev/null & disown"
echo "Then open http://127.0.0.1:8090 in the phone's own browser."
echo ""
echo "To test offline: turn on airplane mode, keep Wi-Fi/mobile data off,"
echo "and confirm both pages still answer — that's proof #2 in PROOF_AND_PILOT_PLAN.md."
