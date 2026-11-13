#!/usr/bin/env bash
# Sorati mod smoke test: install, launch, screenshot, UI dump,
# best-effort profile navigation + premium text check, crash scan.
# v2: two capture rounds (25s + 60s) + foreground-activity record, so a slow
# WebView first load still yields evidence; all captures best-effort, never fail job.
set -u
mkdir -p artifacts
APK="app/Sorati-v43.3-premium.apk"
PKG="com.hark.calories"
ACT="com.hark.calories/.MainActivity"

capture() {
  local tag="$1"
  adb shell screencap -p "/sdcard/${tag}.png" 2>/dev/null
  adb pull "/sdcard/${tag}.png" "artifacts/${tag}.png" 2>/dev/null || true
  adb shell uiautomator dump "/sdcard/ui-${tag}.xml" 2>/dev/null
  adb pull "/sdcard/ui-${tag}.xml" "artifacts/ui-${tag}.xml" 2>/dev/null || true
  # retry the UI dump once if the pull produced nothing (WebView apps are slow)
  if [ ! -s "artifacts/ui-${tag}.xml" ]; then
    sleep 5
    adb shell uiautomator dump "/sdcard/ui-${tag}.xml" 2>/dev/null
    adb pull "/sdcard/ui-${tag}.xml" "artifacts/ui-${tag}.xml" 2>/dev/null || true
  fi
}

echo "== installing APK =="
adb install -r "$APK" | tee artifacts/install.log

echo "== launching $ACT =="
adb shell am start -n "$ACT"
sleep 25
capture home
echo "== foreground after 25s =="
adb shell dumpsys activity activities 2>/dev/null | grep -i "mResumedActivity\|mFocusedApp" | head -4 | tee artifacts/foreground.txt || true
sleep 35
capture home2
echo "== foreground after 60s =="
adb shell dumpsys activity activities 2>/dev/null | grep -i "mResumedActivity\|mFocusedApp" | head -4 | tee -a artifacts/foreground.txt || true
adb logcat -d > artifacts/logcat.txt || true

echo "== profile navigation + premium check (best effort) =="
python3 scripts/check_premium.py || true

echo "== crash scan (app process only) =="
# A FATAL EXCEPTION belongs to our app only if the following line says
# "Process: com.hark.calories" (the process name is on the NEXT line).
if awk '/FATAL EXCEPTION/{f=1; next} f==1 && /Process: com\.hark\.calories/{found=1; exit} f==1 && /FATAL EXCEPTION/{f=0} END{exit !found}' artifacts/logcat.txt; then
  echo "CRASH FOUND (com.hark.calories)" | tee artifacts/verdict.txt
  grep -A18 "FATAL EXCEPTION" artifacts/logcat.txt | grep -B2 -A15 "Process: com.hark.calories" | head -40 >> artifacts/verdict.txt
else
  echo "NO FATAL CRASH in logcat (com.hark.calories)" | tee -a artifacts/verdict.txt
fi
echo "== done =="
ls -la artifacts/
