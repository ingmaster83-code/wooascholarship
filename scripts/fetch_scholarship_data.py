#!/usr/bin/env python3
"""
fetch_scholarship_data.py - 한국장학재단 학자금지원정보(대학생/고등학생)를 odcloud Open API로 수집.

이 데이터는 데이터셋 자체가 매달 새로운 uddi로 재등록되는 "월별 스냅샷" 방식이라
(파일데이터/오픈API 상세 페이지의 uddi가 매달 바뀜), 엔드포인트를 하드코딩하지 않고
infuser.odcloud.kr의 swagger 문서를 조회해 매번 최신 uddi를 찾아 사용한다.

출력:
  _rawdata/university_raw.json   - 대학생 학자금지원정보 원본 배열
  _rawdata/highschool_raw.json   - 고등학생 학자금지원정보 원본 배열
"""
import json
import os
import sys
import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "_rawdata")
os.makedirs(RAW_DIR, exist_ok=True)

SERVICE_KEY = os.environ.get("DATA_GO_KR_API_KEY") or "9490b1d34e92aa9e25b32a4cff1438fc7b9c71e5d332413916a391e867f61e86"

DATASETS = {
    "university": {"publicDataPk": "15028252", "out": "university_raw.json"},
    "highschool": {"publicDataPk": "15116988", "out": "highschool_raw.json"},
}


def find_latest_uddi(public_data_pk):
    """swagger 문서에서 가장 최근(마지막) uddi 경로를 찾는다."""
    url = f"https://infuser.odcloud.kr/oas/docs?namespace={public_data_pk}/v1"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    doc = r.json()
    paths = list(doc["paths"].items())
    if not paths:
        raise RuntimeError(f"{public_data_pk}: swagger 문서에 경로가 없음")
    # 등록 순서대로 쌓이므로 마지막 항목이 최신 스냅샷
    path, meta = paths[-1]
    summary = meta["get"]["summary"]
    print(f"  최신 버전: {summary} ({path})")
    return path  # 예: /15028252/v1/uddi:xxxx


def fetch_all(public_data_pk):
    path = find_latest_uddi(public_data_pk)
    url = f"https://api.odcloud.kr/api{path}"
    params = {"page": 1, "perPage": 3000, "serviceKey": SERVICE_KEY}
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    body = r.json()
    if "data" not in body:
        raise RuntimeError(f"{public_data_pk}: 응답에 data 없음 -> {body}")
    total = body.get("totalCount", len(body["data"]))
    rows = body["data"]
    if len(rows) < total:
        # 혹시 perPage 상한에 걸리면 다음 페이지 이어붙임
        page = 2
        while len(rows) < total:
            params["page"] = page
            r = requests.get(url, params=params, timeout=60)
            r.raise_for_status()
            more = r.json().get("data", [])
            if not more:
                break
            rows.extend(more)
            page += 1
    print(f"  수집 완료: {len(rows)}/{total}건")
    return rows


def main():
    for key, cfg in DATASETS.items():
        print(f"[{key}] 수집 시작 (publicDataPk={cfg['publicDataPk']})")
        rows = fetch_all(cfg["publicDataPk"])
        out_path = os.path.join(RAW_DIR, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False)
        print(f"  저장: {out_path}\n")


if __name__ == "__main__":
    main()
