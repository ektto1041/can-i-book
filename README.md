# can-i-book

`2026-10-03` 체크인 기준으로 빈 방이 생기면 메일을 보내는 간단한 polling 스크립트입니다.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env`에 Gmail 주소와 앱 비밀번호를 넣어주세요.

## Gmail 앱 비밀번호

Gmail을 쓰려면 보통 아래가 필요합니다.

1. Google 계정 2단계 인증 활성화
2. 앱 비밀번호 생성
3. 생성한 비밀번호를 `SMTP_PASSWORD`에 입력

## Run

```bash
python3 monitor.py
```

빈 방이 없으면 로그만 출력하고, 빈 방이 하나라도 있으면 매 주기마다 메일을 보냅니다.

## One-Line Run

터미널에서 아래 한 줄로 실행하고, 멈출 때는 `Ctrl+C`를 누르면 됩니다.

```bash
cd /Users/park/Documents/can-i-book && source .venv/bin/activate && python3 monitor.py
```

Cloud Run Job처럼 1회 실행 후 종료하려면:

```bash
cd /Users/park/Documents/can-i-book && source .venv/bin/activate && python3 monitor.py --once
```

## GitHub Actions

public repository로 운영하면 GitHub-hosted runner를 무료로 쓸 수 있습니다.
이 저장소에는 `5분마다 1회` 실행되는 GitHub Actions workflow가 포함되어 있습니다.

workflow 파일:

- `.github/workflows/monitor.yml`

### GitHub에 넣어야 하는 Secrets

Repository `Settings -> Secrets and variables -> Actions -> Secrets`에 아래 값을 추가하세요.

- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `FROM_EMAIL`
- `TO_EMAIL`

추천 값:

- `SMTP_USERNAME`: `dhkdwk1041@gmail.com`
- `FROM_EMAIL`: `dhkdwk1041@gmail.com`
- `TO_EMAIL`: `dhkdwk1041@gmail.com`

### 선택적으로 넣을 Variables

Repository `Settings -> Secrets and variables -> Actions -> Variables`에 아래 값을 넣을 수 있습니다.
없으면 workflow 기본값을 사용합니다.

- `TARGET_URL`
- `TARGET_DATE`
- `HTTP_TIMEOUT_SECONDS`
- `SMTP_HOST`
- `SMTP_PORT`

기본값은 아래와 같습니다.

- `TARGET_URL`: `https://hub.hotelstory.com/MTAwMDMwMw/calendar?v_caldate=2026-10`
- `TARGET_DATE`: `2026-10-03`
- `HTTP_TIMEOUT_SECONDS`: `10`
- `SMTP_HOST`: `smtp.gmail.com`
- `SMTP_PORT`: `465`

### 시작 방법

1. 이 저장소를 public GitHub repository로 push 합니다.
2. 위 Secrets를 등록합니다.
3. `Actions` 탭에서 workflow 활성화 여부를 확인합니다.
4. `Monitor hotel room` workflow를 `Run workflow`로 한 번 수동 실행해 봅니다.
5. 이후에는 schedule로 자동 실행됩니다.

### 참고

- GitHub Actions의 공식 최소 스케줄 간격은 5분입니다.
- 이 저장소는 `*/5 * * * *` cron으로 5분마다 실행됩니다.
- 스케줄 workflow는 GitHub 부하 상황에 따라 약간 지연될 수 있습니다.

## Environment Variables

- `TARGET_URL`: 감시할 월간 캘린더 URL
- `TARGET_DATE`: 감시할 체크인 날짜 (`YYYY-MM-DD`)
- `CHECK_INTERVAL_SECONDS`: 확인 주기
- `HTTP_TIMEOUT_SECONDS`: HTTP 타임아웃
- `SMTP_HOST`: SMTP 서버
- `SMTP_PORT`: SMTP 포트
- `SMTP_USERNAME`: SMTP 로그인 아이디
- `SMTP_PASSWORD`: SMTP 로그인 비밀번호 또는 앱 비밀번호
- `FROM_EMAIL`: 발신 메일 주소
- `TO_EMAIL`: 수신 메일 주소
- `USER_AGENT`: 선택 사항
