#!/usr/bin/env python3
"""Totally legit mainframe access."""
import random
import sys
import time

TARGET = "mainframe.gov"


def progress(label, seconds=1.2):
    for pct in range(0, 101, 4):
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        sys.stdout.write(f"\r\033[32m{label:<14}\033[0m [{bar}] {pct:3d}%")
        sys.stdout.flush()
        time.sleep(seconds / 25)
    print()


def main():
    print(f"\033[1;36m[*] Connecting to {TARGET}...\033[0m")
    time.sleep(0.5)
    progress("Bypassing")
    progress("Decrypting")
    for _ in range(6):
        key = "".join(random.choice("0123456789abcdef") for _ in range(32))
        print(f"\033[33m[+] key\033[0m {key}")
        time.sleep(0.1)
    print("\033[1;32m[✓] ACCESS GRANTED\033[0m")


if __name__ == "__main__":
    main()
