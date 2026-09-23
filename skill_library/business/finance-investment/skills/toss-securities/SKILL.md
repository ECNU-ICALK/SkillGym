---
name: toss-securities
description: 토스증권 조회형 질문에 대해 tossinvest-cli의 tossctl을 설치/로그인한 뒤 계좌 요약, 포트폴리오, 시세, 주문내역, 관심종목을 안전한 read-only 흐름으로 조회한다.
license: MIT
metadata:
  category: finance
  locale: ko-KR
  phase: v1
---

# Toss Securities

## What this skill does

`JungHoonGhae/tossinvest-cli` 의 `tossctl` 을 이용해 토스증권 **조회 전용(read-only)** 흐름을 실행한다.

- 계좌 목록 / 요약
- 포트폴리오 보유 종목 / 비중
- 단일 종목 / 다중 종목 시세
- 미체결 주문 / 월간 체결 내역
- 관심 종목

## When to use

- "토스증권 계좌 요약 보여줘"
- "토스증권 TSLA 시세 확인해줘"
- "관심종목 목록 보여줘"
- "이번 달 체결 내역 조회해줘"

## Prerequisites

- macOS + Homebrew
- `tossctl` 설치
- `tossctl auth login` 으로 브라우저 세션 확보
- Node.js 18+

## Workflow

### 0. Install `tossctl` first when missing

```bash
brew tap JungHoonGhae/tossinvest-cli
brew install tossctl
tossctl doctor
tossctl auth doctor
tossctl auth login
```

로그인 세션이 없으면 먼저 위 흐름을 끝낸다. 다른 비공식 크롤링이나 임의 HTTP 재구현으로 우회하지 않는다.

### 1. Prefer the read-only `tossctl` surface

지원하는 기본 명령:

- `tossctl account list --output json`
- `tossctl account summary --output json`
- `tossctl portfolio positions --output json`
- `tossctl portfolio allocation --output json`
- `tossctl quote get TSLA --output json`
- `tossctl quote batch TSLA 005930 VOO --output json`
- `tossctl orders list --output json`
- `tossctl orders completed --market all --output json`
- `tossctl watchlist list --output json`

### 2. Use the local package wrapper when scripting helps

```js
const {
  getAccountSummary,
  getQuote,
  listWatchlist
} = require("toss-securities");

async function main() {
  const summary = await getAccountSummary();
  const quote = await getQuote("TSLA");
  const watchlist = await listWatchlist();

  console.log(summary.data);
  console.log(quote.data);
  console.log(watchlist.data);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
```

### 3. Answer conservatively

- 계좌번호/민감정보는 꼭 필요한 범위만 노출한다.
- 사용자가 "오늘" 같은 상대 날짜를 말하면 절대 날짜로 풀어 답한다.
- 이 스킬은 조회 전용이다. 실거래 mutation 은 범위 밖이라고 분명히 말한다.

## Done when

- `tossctl` 설치/로그인 상태가 확인되었다.
- 요청에 맞는 read-only 명령을 실행했다.
- 결과를 한국어로 짧게 정리했다.

## Failure modes

- `tossctl auth login` 전이면 계좌/포트폴리오 조회가 실패할 수 있다.
- upstream 웹 API 구조가 바뀌면 `tossctl` 자체 업데이트가 필요할 수 있다.
- 계좌/주문 정보는 민감하므로 출력 범위를 과도하게 넓히지 않는다.
