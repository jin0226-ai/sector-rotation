# Sector Rotation System

Fidelity 스타일 섹터 로테이션 모델을 기반으로 한 매크로 경제 지표 분석 및 섹터 투자 추천 시스템입니다.

## 주요 기능

- **매크로 데이터 수집**: FRED API를 통한 30+ 경제 지표 자동 수집
- **섹터 ETF 분석**: S&P 500 11개 섹터 ETF 일일 데이터 수집 및 분석
- **ML 기반 스코어링**: 머신러닝 모델을 활용한 섹터 성과 예측
- **비즈니스 사이클 감지**: 경기 순환 단계 자동 판단
- **대시보드**: 실시간 시각화 및 모니터링
- **백테스팅**: 20년 역사적 데이터를 활용한 전략 검증

## 시스템 구조

```
sector-rotation-system/
├── backend/                 # FastAPI Python 백엔드
│   ├── app/
│   │   ├── api/routes/     # API 엔드포인트
│   │   ├── models/         # 데이터베이스 모델
│   │   ├── services/       # 비즈니스 로직
│   │   │   ├── data_collection/   # 데이터 수집
│   │   │   ├── data_processing/   # 데이터 처리
│   │   │   ├── ml/               # 머신러닝 모델
│   │   │   └── backtesting/      # 백테스팅 엔진
│   │   └── core/           # 상수 및 설정
│   ├── scripts/            # 자동화 스크립트
│   └── data/               # SQLite DB 및 모델 파일
│
└── frontend/               # React TypeScript 프론트엔드
    └── src/
        ├── components/     # UI 컴포넌트
        ├── pages/          # 페이지 컴포넌트
        ├── services/       # API 클라이언트
        └── types/          # TypeScript 타입
```

## 설치 및 실행

### 1. 사전 요구사항

- Python 3.10+
- Node.js 18+
- FRED API Key (무료): https://fred.stlouisfed.org/docs/api/api_key.html

### 2. 백엔드 설정

```bash
cd backend

# 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
copy .env.example .env
# .env 파일에서 FRED_API_KEY 설정
```

### 3. 초기 데이터 로드

```bash
# 20년치 역사적 데이터 로드 (최초 1회)
python scripts/init_historical.py

# 스코어 계산
python scripts/daily_update.py
```

### 4. 백엔드 서버 실행

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 프론트엔드 설정 및 실행

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

### 6. 접속

- 프론트엔드: http://localhost:5173
- API 문서: http://localhost:8000/docs

## 자동 업데이트 설정 (Windows Task Scheduler)

```bash
# 관리자 권한으로 실행
cd backend\scripts
setup_scheduler.bat
```

이렇게 하면 매일 오후 6시(미국 시장 마감 후)에 자동으로 데이터가 업데이트됩니다.

## 주요 매크로 지표

| 카테고리 | 지표 |
|---------|------|
| 성장 | GDP, 산업생산, 소매판매, 내구재주문 |
| 노동 | 실업률, 비농업고용, 신규실업수당 |
| 인플레이션 | CPI, Core CPI, PCE, PPI, WTI 원유 |
| 금리 | 기준금리, 10년물, 2년물, 수익률곡선 |
| 심리 | 소비자신뢰지수, ISM PMI |
| 주택 | 주택착공, 건축허가, Case-Shiller |

## 섹터 ETF

| 섹터 | 심볼 | 경기 사이클 선호도 |
|------|------|-------------------|
| Technology | XLK | Mid Cycle |
| Healthcare | XLV | Recession (방어적) |
| Financials | XLF | Early Cycle |
| Consumer Discretionary | XLY | Early Cycle |
| Consumer Staples | XLP | Recession (방어적) |
| Energy | XLE | Late Cycle |
| Industrials | XLI | Early/Mid Cycle |
| Materials | XLB | Late Cycle |
| Utilities | XLU | Recession (방어적) |
| Real Estate | XLRE | Early Cycle |
| Communication Services | XLC | Mid Cycle |

## 스코어링 시스템

각 섹터의 종합 점수는 다음 요소로 구성됩니다:

- **ML 점수 (40%)**: 머신러닝 모델의 상대 수익률 예측
- **사이클 점수 (25%)**: 현재 경기 단계에서의 역사적 성과
- **모멘텀 점수 (20%)**: 기술적 지표 (RSI, 이동평균, 수익률)
- **매크로 민감도 점수 (15%)**: 현재 거시경제 환경에 대한 민감도

## API 엔드포인트

### 대시보드
- `GET /api/dashboard/` - 전체 대시보드 데이터

### 매크로 데이터
- `GET /api/macro/variables` - 모든 매크로 변수 목록
- `GET /api/macro/variables/{id}/history` - 변수 히스토리
- `GET /api/macro/business-cycle` - 비즈니스 사이클

### 섹터
- `GET /api/sectors/` - 모든 섹터 데이터
- `GET /api/sectors/{symbol}` - 특정 섹터 상세

### 스코어
- `GET /api/scores/rankings` - 섹터 랭킹
- `GET /api/scores/heatmap` - 변수×섹터 히트맵
- `GET /api/scores/trends` - 점수 추이

### 백테스팅
- `POST /api/backtest/run` - 백테스트 실행
- `GET /api/backtest/default` - 기본 백테스트 결과

## 라이선스

MIT License

## 참고 자료

- [Fidelity Business Cycle Approach](https://www.fidelity.com/viewpoints/investing-ideas/sector-investing-business-cycle)
- [FRED API Documentation](https://fred.stlouisfed.org/docs/api/fred/)
- [Select Sector SPDR ETFs](https://www.ssga.com/us/en/intermediary/capabilities/equities/sector-investing/select-sector-etfs)
