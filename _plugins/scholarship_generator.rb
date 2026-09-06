require 'json'

module Jekyll
  module SchUtil
    def self.rawdata_dir(site)
      File.join(site.source, '_rawdata')
    end
  end

  # ── 데이터 로드 (한 번만) ──────────────────────────────
  class ScholarshipDataGenerator < Generator
    safe true
    priority :highest

    def generate(site)
      return if site.data['scholarship_all']

      path = File.join(SchUtil.rawdata_dir(site), 'scholarships.json')
      raw = JSON.parse(File.read(path, encoding: 'utf-8'))
      items = raw['items']

      by_sido = Hash.new { |h, k| h[k] = [] }
      items.each do |it|
        key = it['sido'].nil? || it['sido'].empty? ? 'nationwide' : it['sidoSlug']
        by_sido[key] << it
      end

      site.data['scholarship_all'] = items
      site.data['scholarship_by_sido'] = by_sido
      site.data['scholarship_meta'] = {
        'totalCount' => raw['totalCount'],
        'universityCount' => raw['universityCount'],
        'highschoolCount' => raw['highschoolCount'],
        'nationwideCount' => raw['nationwideCount'],
        'regionSummary' => raw['regionSummary'],
        'generatedAt' => raw['generatedAt'],
      }
      Jekyll.logger.info "ScholarshipGenerator:", "총 #{items.size}건 로드 (#{by_sido.size}개 지역 그룹)"
    end
  end

  REGION_LABEL = {
    'nationwide' => '전국(지역무관)',
  }.freeze

  LEVEL_LABEL = { 'university' => '대학생', 'highschool' => '고등학생' }.freeze

  # ── 지역 개요 페이지 (/region/{slug}/) ───────────────────
  class RegionOverviewGenerator < Generator
    safe true
    priority :normal

    def generate(site)
      by_sido = site.data['scholarship_by_sido'] || {}
      by_sido.each do |slug, items|
        site.pages << RegionOverviewPage.new(site, slug, items)
      end
      Jekyll.logger.info "ScholarshipGenerator:", "지역 개요 페이지 #{by_sido.size}개 생성"
    end
  end

  class RegionOverviewPage < Page
    def initialize(site, slug, items)
      @site = site
      @base = site.source
      @dir  = "region/#{slug}"
      @name = 'index.html'
      self.process(@name)
      self.read_yaml(File.join(@base, '_layouts'), 'region.html')

      sido_name = items.first ? (items.first['sido'] || '전국') : (REGION_LABEL[slug] || slug)
      uni_count = items.count { |it| it['targetLevel'] == 'university' }
      hs_count = items.count { |it| it['targetLevel'] == 'highschool' }

      self.data['sidoSlug'] = slug
      self.data['sidoName'] = sido_name
      self.data['universityCount'] = uni_count
      self.data['highschoolCount'] = hs_count
      self.data['layout'] = 'region'
      self.data['title'] = "#{sido_name} 대학생·고등학생 장학금 (#{items.size}건)"
      self.data['description'] = "#{sido_name} 지역 대학생 장학금 #{uni_count}건, 고등학생 장학금 #{hs_count}건의 신청기간·지원금액·자격조건을 확인하세요."
    end
  end

  # ── 지역×학교급 목록 페이지 (/region/{slug}/{level}/) ─────
  class RegionLevelListGenerator < Generator
    safe true
    priority :normal

    def generate(site)
      by_sido = site.data['scholarship_by_sido'] || {}
      count = 0
      by_sido.each do |slug, items|
        %w[university highschool].each do |level|
          list = items.select { |it| it['targetLevel'] == level }
          next if list.empty?
          site.pages << RegionLevelListPage.new(site, slug, level, list)
          count += 1
        end
      end
      Jekyll.logger.info "ScholarshipGenerator:", "지역×학교급 목록 페이지 #{count}개 생성"
    end
  end

  class RegionLevelListPage < Page
    def initialize(site, slug, level, items)
      @site = site
      @base = site.source
      @dir  = "region/#{slug}/#{level}"
      @name = 'index.html'
      self.process(@name)
      self.read_yaml(File.join(@base, '_layouts'), 'region-level.html')

      sido_name = items.first['sido'] || (REGION_LABEL[slug] || slug)
      level_label = LEVEL_LABEL[level]

      sorted = items.sort_by { |it| [it['status'] == 'open' ? 0 : (it['status'] == 'upcoming' ? 1 : 2), it['endDate'].to_s] }

      self.data['sidoSlug'] = slug
      self.data['sidoName'] = sido_name
      self.data['level'] = level
      self.data['levelLabel'] = level_label
      self.data['items'] = sorted
      self.data['totalCount'] = items.size
      self.data['layout'] = 'region-level'
      self.data['title'] = "#{sido_name} #{level_label} 장학금 #{items.size}건 모음"
      self.data['description'] = "#{sido_name} #{level_label}을 위한 장학금 #{items.size}건 — 지원자격, 지원금액, 신청기간을 한눈에 비교하세요."
    end
  end

  # ── 학교급 전체 인덱스 (/university/, /highschool/) ───────
  class LevelIndexGenerator < Generator
    safe true
    priority :normal

    def generate(site)
      %w[university highschool].each do |level|
        site.pages << LevelIndexPage.new(site, level)
      end
      Jekyll.logger.info "ScholarshipGenerator:", "학교급 인덱스 페이지 2개 생성"
    end
  end

  class LevelIndexPage < Page
    def initialize(site, level)
      @site = site
      @base = site.source
      @dir  = level
      @name = 'index.html'
      self.process(@name)
      self.read_yaml(File.join(@base, '_layouts'), 'level.html')

      by_sido = site.data['scholarship_by_sido'] || {}
      region_rows = REGION_ORDER.map do |slug, sido_name|
        items = by_sido[slug] || []
        cnt = items.count { |it| it['targetLevel'] == level }
        { 'slug' => slug, 'name' => sido_name, 'count' => cnt }
      end

      meta = site.data['scholarship_meta'] || {}
      total = level == 'university' ? meta['universityCount'] : meta['highschoolCount']
      level_label = LEVEL_LABEL[level]

      self.data['level'] = level
      self.data['levelLabel'] = level_label
      self.data['regionRows'] = region_rows
      self.data['totalCount'] = total
      self.data['layout'] = 'level'
      self.data['title'] = "#{level_label} 장학금 전국 #{total}건 — 지역별 모음"
      self.data['description'] = "전국 #{level_label} 장학금 #{total}건을 지역별로 확인하세요. 지자체·민간재단·대학의 신청기간·지원금액·자격조건을 한눈에 비교할 수 있어요."
    end
  end

  REGION_ORDER = [
    ['seoul', '서울특별시'], ['busan', '부산광역시'], ['daegu', '대구광역시'],
    ['incheon', '인천광역시'], ['gwangju', '광주광역시'], ['daejeon', '대전광역시'],
    ['ulsan', '울산광역시'], ['sejong', '세종특별자치시'], ['gyeonggi', '경기도'],
    ['gangwon', '강원특별자치도'], ['chungbuk', '충청북도'], ['chungnam', '충청남도'],
    ['jeonbuk', '전북특별자치도'], ['jeonnam', '전라남도'], ['gyeongbuk', '경상북도'],
    ['gyeongnam', '경상남도'], ['jeju', '제주특별자치도'], ['nationwide', '전국(지역무관)'],
  ].freeze

  # ── 개별 장학금 상세 페이지 (/scholarship/{slug}/) ─────────
  class ScholarshipPageGenerator < Generator
    safe true
    priority :normal

    def generate(site)
      items = site.data['scholarship_all'] || []
      items.each { |it| site.pages << ScholarshipPage.new(site, it) }
      Jekyll.logger.info "ScholarshipGenerator:", "장학금 상세 페이지 #{items.size}개 생성"
    end
  end

  class ScholarshipPage < Page
    def initialize(site, it)
      @site = site
      @base = site.source
      @dir  = "scholarship/#{it['slug']}"
      @name = 'index.html'
      self.process(@name)
      self.read_yaml(File.join(@base, '_layouts'), 'scholarship.html')
      self.data.merge!(it)
      self.data['layout'] = 'scholarship'
      level_label = LEVEL_LABEL[it['targetLevel']]
      region_label = it['sido'] || '전국'
      self.data['title'] = "#{it['productNm']} — #{it['orgNm']} (#{region_label} #{level_label} 장학금)"
      amount = it['supportDetail'].to_s.gsub(/[○\n]/, ' ').strip
      amount = amount[0, 60] if amount.length > 60
      self.data['description'] = "#{it['orgNm']}의 #{level_label} 장학금 '#{it['productNm']}'. #{amount}"
    end
  end
end
