#!/usr/bin/env python3
"""
process_data.py - 한국장학재단 학자금지원정보(대학생/고등학생) 원본을 사이트용 스키마로 가공.

입력: _rawdata/university_raw.json, _rawdata/highschool_raw.json
출력: _data/scholarships.json (Jekyll _plugins에서 로드)

주의: Jekyll Page 예약어(name/url/content/path/date/id 등)와 충돌하지 않도록
      필드명을 orgNm/productNm/homepageUrl 등으로 변경함.
"""
import hashlib
import json
import os
import re
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "_rawdata")
DATA_DIR = RAW_DIR
os.makedirs(DATA_DIR, exist_ok=True)

TODAY = date.today().isoformat()

# ── 17개 시도 (전체 표기 우선 매칭) ──────────────────────────────────────
SIDO_FULL = [
    "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시",
    "대전광역시", "울산광역시", "세종특별자치시", "경기도",
    "강원특별자치도", "충청북도", "충청남도", "전북특별자치도",
    "전라남도", "경상북도", "경상남도", "제주특별자치도",
]

SIDO_SLUG = {
    "서울특별시": "seoul", "부산광역시": "busan", "대구광역시": "daegu",
    "인천광역시": "incheon", "광주광역시": "gwangju", "대전광역시": "daejeon",
    "울산광역시": "ulsan", "세종특별자치시": "sejong", "경기도": "gyeonggi",
    "강원특별자치도": "gangwon", "충청북도": "chungbuk", "충청남도": "chungnam",
    "전북특별자치도": "jeonbuk", "전라남도": "jeonnam", "경상북도": "gyeongbuk",
    "경상남도": "gyeongnam", "제주특별자치도": "jeju",
}

# 흔히 쓰이는 축약형 (긴 것부터 매칭되도록 순서 유지)
SIDO_ALIAS = [
    ("서울특별시", "서울특별시"), ("서울시", "서울특별시"),
    ("부산광역시", "부산광역시"), ("부산시", "부산광역시"),
    ("대구광역시", "대구광역시"), ("대구시", "대구광역시"),
    ("인천광역시", "인천광역시"), ("인천시", "인천광역시"),
    ("대전광역시", "대전광역시"), ("대전시", "대전광역시"),
    ("울산광역시", "울산광역시"), ("울산시", "울산광역시"),
    ("세종특별자치시", "세종특별자치시"), ("세종시", "세종특별자치시"),
    ("경기도", "경기도"),
    ("강원특별자치도", "강원특별자치도"), ("강원도", "강원특별자치도"),
    ("충청북도", "충청북도"), ("충북", "충청북도"),
    ("충청남도", "충청남도"), ("충남", "충청남도"),
    ("전북특별자치도", "전북특별자치도"), ("전라북도", "전북특별자치도"), ("전북", "전북특별자치도"),
    ("전라남도", "전라남도"), ("전남", "전라남도"),
    ("경상북도", "경상북도"), ("경북", "경상북도"),
    ("경상남도", "경상남도"), ("경남", "경상남도"),
    ("제주특별자치도", "제주특별자치도"), ("제주도", "제주특별자치도"), ("제주", "제주특별자치도"),
]

# 시/군/구 단위 세부 지명 -> 시도 (전국 검색 롱테일 강화용, 완전 목록은 아니고
# 실제 데이터에 자주 등장하는 지자체장학회 지명 위주로 폭넓게 커버)
SIGUNGU_TO_SIDO = {}


def _add(sido, names):
    for n in names:
        SIGUNGU_TO_SIDO.setdefault(n, sido)


_add("경기도", ["수원시", "성남시", "의정부시", "안양시", "부천시", "광명시", "평택시", "동두천시",
              "안산시", "고양시", "과천시", "구리시", "남양주시", "오산시", "시흥시", "군포시",
              "의왕시", "하남시", "용인시", "파주시", "이천시", "안성시", "김포시", "화성시",
              "양주시", "포천시", "여주시", "연천군", "가평군", "양평군"])
_add("강원특별자치도", ["춘천시", "원주시", "강릉시", "동해시", "태백시", "속초시", "삼척시",
                    "홍천군", "횡성군", "영월군", "평창군", "정선군", "철원군", "화천군",
                    "양구군", "인제군", "양양군"])
_add("충청북도", ["청주시", "충주시", "제천시", "보은군", "옥천군", "영동군", "증평군",
               "진천군", "괴산군", "음성군", "단양군"])
_add("충청남도", ["천안시", "공주시", "보령시", "아산시", "서산시", "논산시", "계룡시",
               "당진시", "금산군", "부여군", "서천군", "청양군", "홍성군", "예산군", "태안군"])
_add("전북특별자치도", ["전주시", "군산시", "익산시", "정읍시", "남원시", "김제시", "완주군",
                    "진안군", "무주군", "장수군", "임실군", "순창군", "고창군", "부안군"])
_add("전라남도", ["목포시", "여수시", "순천시", "나주시", "광양시", "담양군", "곡성군", "구례군",
               "고흥군", "보성군", "화순군", "장흥군", "강진군", "해남군", "영암군", "무안군",
               "함평군", "영광군", "장성군", "완도군", "진도군", "신안군"])
_add("경상북도", ["포항시", "경주시", "김천시", "안동시", "구미시", "영주시", "영천시",
               "상주시", "문경시", "경산시", "의성군", "청송군", "영양군", "영덕군",
               "청도군", "고령군", "성주군", "칠곡군", "예천군", "봉화군", "울진군", "울릉군"])
_add("경상남도", ["창원시", "진주시", "통영시", "사천시", "김해시", "밀양시", "거제시",
               "양산시", "의령군", "함안군", "창녕군", "남해군", "하동군", "산청군",
               "함양군", "거창군", "합천군"])
_add("제주특별자치도", ["제주시", "서귀포시"])
# 고성군은 강원/경남 중복 -> 별도 처리 없이 강원 우선(더 흔한 사용례)
SIGUNGU_TO_SIDO.setdefault("고성군", "강원특별자치도")

# 서울/광역시 자치구는 구 이름만으로 시도가 갈리는 경우가 많아, 상위 시도명이
# 텍스트에 함께 있을 때만 사용 (아래 detect_region에서 처리)
GU_HINT = {
    "서울특별시": ["종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구", "성북구",
                "강북구", "도봉구", "노원구", "은평구", "서대문구", "마포구", "양천구", "강서구",
                "구로구", "금천구", "영등포구", "동작구", "관악구", "서초구", "강남구", "송파구", "강동구"],
    "부산광역시": ["서구", "동구", "영도구", "부산진구", "동래구", "남구", "북구", "해운대구",
                "사하구", "금정구", "강서구", "연제구", "수영구", "사상구", "기장군"],
    "대구광역시": ["동구", "서구", "남구", "북구", "수성구", "달서구", "달성군", "군위군"],
    "인천광역시": ["중구", "동구", "미추홀구", "연수구", "남동구", "부평구", "계양구", "서구",
                "강화군", "옹진군"],
    "광주광역시": ["동구", "서구", "남구", "북구", "광산구"],
    "대전광역시": ["동구", "중구", "서구", "유성구", "대덕구"],
    "울산광역시": ["중구", "남구", "동구", "북구", "울주군"],
}


def clean(text):
    if not text:
        return ""
    t = str(text).strip()
    if t in ("해당없음", "기관확인필요", "※ 기관확인필요", "-"):
        return ""
    return t


def detect_region(row, org_field, region_field):
    """지역거주여부 상세내용 + 운영기관명에서 시도/시군구를 추정."""
    combined = f"{region_field or ''} {org_field or ''}"

    # 광주(광역시) vs 경기 광주시 특수 처리
    if "경기" in combined and "광주" in combined and "광주광역시" not in combined:
        pass  # 경기 광주로 취급되도록 아래 일반 로직에 맡김
    elif "광주" in combined:
        for gu in GU_HINT["광주광역시"]:
            if gu in combined:
                return "광주광역시", gu

    # 전체 표기/축약형 시도명
    for alias, sido in SIDO_ALIAS:
        if alias in combined:
            # 시/군/구 이름도 같이 찾아서 세부지명 확보 시도
            for name, s in SIGUNGU_TO_SIDO.items():
                if s == sido and name in combined:
                    return sido, name
            if sido in GU_HINT:
                for gu in GU_HINT[sido]:
                    if gu in combined:
                        return sido, gu
            return sido, None

    # 시/군 단위 세부지명만으로 매칭 (예: "거창군장학회")
    for name, sido in SIGUNGU_TO_SIDO.items():
        if name in combined:
            return sido, name

    return None, None


def make_slug(target, org, product, idx):
    raw = f"{target}-{org}-{product}-{idx}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


def compute_status(start, end):
    if not start or not end:
        return "unknown"
    try:
        if end < TODAY:
            return "closed"
        if start > TODAY:
            return "upcoming"
        return "open"
    except Exception:
        return "unknown"


def normalize(row, idx, target_level):
    org = clean(row.get("운영기관명"))
    product = clean(row.get("상품명"))
    region_text = clean(row.get("지역거주여부 상세내용"))
    sido, sigungu = detect_region(row, org, region_text)

    start = clean(row.get("모집시작일"))
    end = clean(row.get("모집종료일"))

    homepage = clean(row.get("홈페이지 주소") or row.get("홈페이지주소"))
    if homepage and not re.match(r"^https?://", homepage):
        homepage = "https://" + homepage

    school_type = clean(row.get("대학구분") or row.get("학교구분"))

    return {
        "slug": make_slug(target_level, org, product, idx),
        "targetLevel": target_level,
        "orgNm": org,
        "productNm": product,
        "orgType": clean(row.get("운영기관구분")),
        "productType": clean(row.get("상품구분")),
        "fundType": clean(row.get("학자금유형구분")),
        "schoolType": school_type,
        "gradeType": clean(row.get("학년구분")),
        "majorType": clean(row.get("학과구분")),
        "gradeCriteria": clean(row.get("성적기준 상세내용")),
        "incomeCriteria": clean(row.get("소득기준 상세내용")),
        "supportDetail": clean(row.get("지원내역 상세내용")),
        "qualCriteria": clean(row.get("특정자격 상세내용")),
        "regionCriteria": region_text,
        "selectMethod": clean(row.get("선발방법 상세내용")),
        "selectCount": clean(row.get("선발인원 상세내용")),
        "restrictions": clean(row.get("자격제한 상세내용")),
        "recommendNeeded": clean(row.get("추천필요여부 상세내용")),
        "docsNeeded": clean(row.get("제출서류 상세내용")),
        "homepageUrl": homepage,
        "startDate": start,
        "endDate": end,
        "status": compute_status(start, end),
        "sido": sido,
        "sidoSlug": SIDO_SLUG.get(sido, "nationwide"),
        "sigungu": sigungu,
    }


def main():
    all_items = []

    for target_level, fname in (("university", "university_raw.json"), ("highschool", "highschool_raw.json")):
        path = os.path.join(RAW_DIR, fname)
        if not os.path.exists(path):
            print(f"[경고] {path} 없음 - 건너뜀")
            continue
        rows = json.load(open(path, encoding="utf-8"))
        for i, row in enumerate(rows):
            all_items.append(normalize(row, i, target_level))
        print(f"{target_level}: {len(rows)}건 처리")

    # 지역별 집계
    by_sido = {}
    for it in all_items:
        key = it["sido"] or "전국"
        by_sido.setdefault(key, []).append(it["slug"])

    region_summary = []
    for sido in SIDO_FULL:
        cnt = len(by_sido.get(sido, []))
        region_summary.append({
            "sido": sido, "slug": SIDO_SLUG[sido], "count": cnt,
        })
    nationwide_cnt = len(by_sido.get("전국", []))

    out = {
        "generatedAt": TODAY,
        "totalCount": len(all_items),
        "universityCount": sum(1 for it in all_items if it["targetLevel"] == "university"),
        "highschoolCount": sum(1 for it in all_items if it["targetLevel"] == "highschool"),
        "nationwideCount": nationwide_cnt,
        "regionSummary": region_summary,
        "items": all_items,
    }

    out_path = os.path.join(DATA_DIR, "scholarships.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)

    # 홈페이지 검색용 경량 인덱스 (Fuse.js)
    search_index = [
        {
            "n": it["productNm"], "o": it["orgNm"],
            "l": it["sido"] or "전국", "t": "대학생" if it["targetLevel"] == "university" else "고등학생",
            "s": it["slug"],
        }
        for it in all_items
    ]
    search_out = os.path.join(ROOT, "search_index.json")
    with open(search_out, "w", encoding="utf-8") as f:
        json.dump(search_index, f, ensure_ascii=False)

    print(f"\n총 {len(all_items)}건 저장 -> {out_path}")
    print(f"검색 인덱스 저장 -> {search_out}")
    print(f"지역 매칭: 전국(미상) {nationwide_cnt}건 / 시도 매칭 {len(all_items) - nationwide_cnt}건")
    print("시도별 건수:", {r['sido']: r['count'] for r in region_summary if r['count'] > 0})


if __name__ == "__main__":
    main()
