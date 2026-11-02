#!/usr/bin/env python3
"""seed_slug_registry.py - 1회용. 주소 고정 도입 전의 git 이력으로 두 파일을 만든다.

  _rawdata/slug_registry.json  현재 라이브 주소(10-26 스냅샷)를 (학교급, 기관명, 상품명)에 고정
  _rawdata/old_slugs.json      과거 스냅샷에서 쓰였던 옛 주소 -> [학교급, 기관명, 상품명]
                               (Jekyll 플러그인이 옛 주소를 현재 주소로 넘기는 안내 페이지를 만든다)

실행 전에 _rawdata/scholarships.json 이 고정 도입 전 마지막 스냅샷(라이브와 같은 것)이어야 한다.
사용: python scripts/seed_slug_registry.py
"""
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "_rawdata")


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def load_rev(rev):
    return json.loads(git("show", f"{rev}:_rawdata/scholarships.json").decode("utf-8"))["items"]


def main():
    cur = json.load(open(os.path.join(RAW, "scholarships.json"), encoding="utf-8"))["items"]

    registry, seen = {}, {}
    for it in cur:
        k = (it["targetLevel"], it["orgNm"], it["productNm"])
        n = seen.get(k, 0)
        seen[k] = n + 1
        registry["\t".join(k) + "\t%d" % n] = it["slug"]
    live = set(registry.values())

    old = {}
    revs = git("log", "--format=%h", "--reverse", "--", "_rawdata/scholarships.json").decode().split()
    for rev in revs:
        for it in load_rev(rev):
            if it["slug"] in live or it["slug"] in old:
                continue
            old[it["slug"]] = [it["targetLevel"], it["orgNm"], it["productNm"]]

    with open(os.path.join(RAW, "slug_registry.json"), "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, sort_keys=True)
    with open(os.path.join(RAW, "old_slugs.json"), "w", encoding="utf-8") as f:
        json.dump(old, f, ensure_ascii=False, sort_keys=True)

    keys = {tuple(v) for v in old.values()}
    live_keys = {(it["targetLevel"], it["orgNm"], it["productNm"]) for it in cur}
    print(f"고정 주소 {len(registry)}건 / 옛 주소 {len(old)}건 (현재 장학금으로 이어지는 것 {sum(1 for v in old.values() if tuple(v) in live_keys)}건)")
    print(f"이력 스냅샷 {len(revs)}개 검사")


if __name__ == "__main__":
    main()
