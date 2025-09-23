#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -x "$SCRIPT_DIR/davinciauto-cli" ]; then
  ROOT_DIR="$SCRIPT_DIR"
  RUNNER="$SCRIPT_DIR/gui_launcher_run.sh"
elif [ -x "$SCRIPT_DIR/../davinciauto-cli" ]; then
  ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
  RUNNER="$ROOT_DIR/scripts/gui_launcher_run.sh"
else
  ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
  RUNNER="$ROOT_DIR/scripts/gui_launcher_run.sh"
fi
CLI="$ROOT_DIR/davinciauto-cli"

if [ ! -x "$CLI" ]; then
  osascript <<'OSA'
display dialog "davinciauto-cli が見つかりません。アプリ一式が揃っているフォルダから起動してください。" buttons {"OK"} default button "OK" with icon stop
OSA
  exit 1
fi

choose_mode=$(osascript <<'OSA'
set modeList to {"Self-Check", "Fake-TTS", "Full Run"}
set userChoice to choose from list modeList with prompt "実行モードを選択してください" default items {"Fake-TTS"}
if userChoice is false then
  return "CANCEL"
else
  return item 1 of userChoice
end if
OSA
)

if [ "$choose_mode" = "CANCEL" ]; then
  exit 0
fi

KEY_SERVICE="DavinciAuto Azure Speech Key"
REGION_SERVICE="DavinciAuto Azure Speech Region"

get_keychain() {
  security find-generic-password -a "$USER" -s "$1" -w 2>/dev/null || true
}

set_keychain() {
  security add-generic-password -a "$USER" -s "$1" -w "$2" -U >/dev/null 2>&1 || true
}

prompt_dialog() {
  local prompt="$1"
  local default_answer="$2"
  local hidden_flag="$3"
  osascript -e 'on run argv' \
            -e 'set promptText to item 1 of argv' \
            -e 'set defaultAnswer to item 2 of argv' \
            -e 'set hiddenFlag to item 3 of argv' \
            -e 'try' \
            -e 'if hiddenFlag is "hidden" then' \
            -e 'set dialogResult to display dialog promptText default answer defaultAnswer with hidden answer buttons {"Cancel", "OK"} default button "OK"' \
            -e 'else' \
            -e 'set dialogResult to display dialog promptText default answer defaultAnswer buttons {"Cancel", "OK"} default button "OK"' \
            -e 'end if' \
            -e 'set userText to text returned of dialogResult' \
            -e 'set buttonName to button returned of dialogResult' \
            -e 'return buttonName & "::" & userText' \
            -e 'on error number -128' \
            -e 'return "CANCEL::"' \
            -e 'end try' \
            -e 'end run' -- "$prompt" "$default_answer" "$hidden_flag"
}

existing_key="$(get_keychain "$KEY_SERVICE")"
azure_key=""
while [ -z "$azure_key" ]; do
  if [ -n "$existing_key" ]; then
    prompt_msg="Azure Speech APIキーを入力してください (空欄で保存済みキーを使用)"
  else
    prompt_msg="Azure Speech APIキーを入力してください"
  fi
  result=$(prompt_dialog "$prompt_msg" "" "hidden")
  button=${result%%::*}
  value=${result#*::}
  if [ "$button" = "CANCEL" ]; then
    exit 0
  fi
  if [ -n "$value" ]; then
    azure_key="$value"
  elif [ -n "$existing_key" ]; then
    azure_key="$existing_key"
  else
    osascript -e 'display alert "APIキーが必要です" message "Azure Speech APIキーを入力してください。" as warning buttons {"OK"} default button "OK"'
  fi
  if [ -n "$azure_key" ]; then
    if [ "$azure_key" != "$existing_key" ]; then
      set_keychain "$KEY_SERVICE" "$azure_key"
    fi
    break
  fi
done

existing_region="$(get_keychain "$REGION_SERVICE")"
default_region=${existing_region:-"eastus2"}
region_input=""
while [ -z "$region_input" ]; do
  result=$(prompt_dialog "Azure Speech リージョンを入力してください (例: japaneast, eastus2)" "$default_region" "visible")
  button=${result%%::*}
  value=${result#*::}
  if [ "$button" = "CANCEL" ]; then
    exit 0
  fi
  trimmed=$(printf '%s' "$value" | tr -d ' \t')
  if [ -n "$trimmed" ]; then
    region_input="$trimmed"
  else
    region_input="$default_region"
  fi
  if [ "$region_input" != "$existing_region" ]; then
    set_keychain "$REGION_SERVICE" "$region_input"
  fi
  break
done

if [ "$choose_mode" != "Self-Check" ]; then
  script_path=$(osascript <<'OSA'
set theFile to choose file with prompt "台本ファイルを選択してください"
return POSIX path of theFile
OSA
)

  output_dir=$(osascript <<'OSA'
set theFolder to choose folder with prompt "出力フォルダを選択してください"
return POSIX path of theFolder
OSA
)
else
  script_path=""
  output_dir=""
fi

if [ "$choose_mode" = "Fake-TTS" ]; then
  provider="azure"
else
  provider="azure"
fi

target=$(osascript <<'OSA'
set targetList to {"resolve", "premiere"}
set choice to choose from list targetList with prompt "出力ターゲットを選択してください" default items {"resolve"}
if choice is false then
  return "resolve"
else
  return item 1 of choice
end if
OSA
)

export AZURE_SPEECH_KEY="$azure_key"
export AZURE_SPEECH_REGION="$region_input"
export DAVINCIAUTO_FFMPEG=${DAVINCIAUTO_FFMPEG:-"$ROOT_DIR/_internal/bin/ffmpeg"}
export DAVINCIAUTO_FFPROBE=${DAVINCIAUTO_FFPROBE:-"$ROOT_DIR/_internal/bin/ffprobe"}
export DAVA_FFMPEG_PATH="$DAVINCIAUTO_FFMPEG"
export DAVA_FFPROBE_PATH="$DAVINCIAUTO_FFPROBE"

case "$choose_mode" in
  "Self-Check")
    "$RUNNER" self-check
    ;;
  "Fake-TTS")
    "$RUNNER" fake-run "$script_path" "$output_dir" "$provider" "$target"
    ;;
  "Full Run")
    "$RUNNER" full-run "$script_path" "$output_dir" "$provider" "$target"
    ;;
 esac
