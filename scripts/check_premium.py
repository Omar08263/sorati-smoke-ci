#!/usr/bin/env python3
"""Best-effort premium check for the Sorati mod on the emulator.

Reads artifacts/ui-home.xml, looks for a profile/account button,
taps it, dumps the profile screen, and greps both dumps for premium
markers (بريميوم / Premium / 2099). Never fails the job: it only
writes artifacts/premium-check.txt with what it found.
"""
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

OUT = "artifacts/premium-check.txt"
PROFILE_WORDS = ["الملف", "حساب", "بروفايل", "Profile", "أنت", "الإعدادات"]
PREMIUM_WORDS = ["بريميوم", "Premium", "premium", "2099", "2099-12-31"]

log = []


def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout + r.stderr


def find_profile_node(path):
    try:
        tree = ET.parse(path)
    except Exception as e:
        log.append(f"cannot parse {path}: {e}")
        return None
    for node in tree.iter("node"):
        text = (node.get("text") or "") + " " + (node.get("content-desc") or "") + " " + (node.get("resource-id") or "")
        if any(w in text for w in PROFILE_WORDS):
            if node.get("clickable") == "true":
                return node
    return None


def center(node):
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.get("bounds") or "")
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


def grep_premium(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            data = f.read()
    except Exception as e:
        return [f"cannot read {path}: {e}"]
    found = [w for w in PREMIUM_WORDS if w in data]
    return found


def main():
    node = find_profile_node("artifacts/ui-home.xml")
    if node is None:
        log.append("profile button: NOT FOUND in ui-home.xml (best effort only)")
    else:
        c = center(node)
        if c:
            log.append(f"profile button: found, tapping {c}")
            run(f"adb shell input tap {c[0]} {c[1]}")
            time.sleep(6)
            run("adb shell screencap -p /sdcard/profile.png")
            run("adb pull /sdcard/profile.png artifacts/profile.png")
            run("adb shell uiautomator dump /sdcard/ui-profile.xml")
            run("adb pull /sdcard/ui-profile.xml artifacts/ui-profile.xml")
        else:
            log.append("profile button: found but no bounds, cannot tap")
    for path in ["artifacts/ui-home.xml", "artifacts/ui-profile.xml"]:
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                pass
            found = grep_premium(path)
            log.append(f"{path}: premium markers found: {found if found else 'NONE'}")
        except FileNotFoundError:
            log.append(f"{path}: not present")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(log) + "\n")
    print("\n".join(log))
    return 0


if __name__ == "__main__":
    sys.exit(main())
