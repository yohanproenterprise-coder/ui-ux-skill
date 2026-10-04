import argparse
import core

p = argparse.ArgumentParser(description="YouTube -> Shorts / TikTok")
p.add_argument("url")
p.add_argument("-n", type=int, default=5, help="nombre de clips")
p.add_argument("-l", "--length", type=int, default=35, help="durée (s)")
p.add_argument("--mode", choices=["blur", "crop"], default="blur")
p.add_argument("--no-captions", action="store_true")
a = p.parse_args()
for m in core.process(a.url, a.n, a.length, a.mode, not a.no_captions):
    print(f"{m['start']:.0f}s-{m['end']:.0f}s  {m['file']}  ({m['reason']})")
