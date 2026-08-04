# AI QA Draft Generator

QA 실무에서 반복적으로 소요되는 **테스트케이스 초안 작성**과 **버그 이슈 초안 작성** 과정을 LLM(대규모 언어모델)으로 자동화하는 샘플 프로젝트입니다.

실제 QA 조직에서 신규 기능 요구사항 문서와 버그 재현 로그를 바탕으로 테스트케이스/이슈를 매번 처음부터 작성하는 데 걸리는 시간을 줄이기 위해 만든 워크플로우를 재구성한 것입니다. (본 저장소의 코드는 특정 회사의 사내 코드가 아닌, 동일한 아이디어를 처음부터 다시 구현한 포트폴리오용 예제입니다.)

## 왜 만들었나

QA 엔지니어가 매번 반복하는 두 가지 작업이 있습니다.

1. 신규/변경 기능 요구사항 문서를 읽고 테스트케이스를 하나하나 작성하는 것
2. 발견한 버그를 재현 절차·환경 정보·심각도까지 포함해 이슈 트래커(Jira 등)에 등록할 수 있는 형태로 정리하는 것

두 작업 모두 "빈 문서에서 시작"하는 부분이 가장 오래 걸립니다. 이 프로젝트는 LLM이 초안을 먼저 만들고, QA 엔지니어는 그 초안을 검토·수정만 하도록 흐름을 바꿔 초안 작성 시간을 단축하는 것을 목표로 합니다.

## 무엇을 하는가

| 스크립트 | 입력 | 출력 |
|---|---|---|
| `src/generate_test_cases.py` | 기능 요구사항/스펙 텍스트 | 구조화된 테스트케이스 초안 (Given/When/Then, 우선순위, 대상 플랫폼 포함) |
| `src/generate_issue_draft.py` | 버그 재현 메모, 로그, 스크린샷 설명 등 | 이슈 제목, 재현 절차, 기대/실제 결과, 환경 정보, 우선순위 제안이 담긴 이슈 초안 |
| `src/run_pipeline.py` | 테스트 결과가 정리된 시트(CSV, 실제 Google Sheet에 해당) | Fail 건에 대해 이슈 초안을 생성하고, mock Jira에 티켓까지 자동 생성. 이전에 Resolved된 티켓이 있으면 그 상태를 시트에 먼저 반영 (양방향 동기화, end-to-end 데모) |
| `src/resolve_ticket.py` | 티켓 키 (예: QA-1001) | 개발자가 Jira에서 티켓을 Resolved로 바꾸는 상황을 흉내내는 CLI |

앞의 두 스크립트가 "초안 생성" 하나만 보여주는 단위 데모라면, `run_pipeline.py`는 실제 QA 자동화 워크플로우를 양방향으로 재현한 버전입니다.

- **시트 → BTS**: 시트에서 Fail 감지 → 이슈 초안 작성 → 티켓 생성 → 시트에 티켓 번호 기록
- **BTS → 시트**: (개발자가 `resolve_ticket.py`로 티켓을 Resolved 처리하면) 다음 `run_pipeline.py` 실행 시 그 상태를 감지해서 시트의 티켓 칸에 반영

실제 서비스라면 두 번째 방향은 Jira 웹훅 수신이나 주기적 polling으로 처리되는데, 이 데모에서는 `run_pipeline.py`를 실행하는 시점에 상태를 조회해서 반영하는 방식(polling과 동일한 개념)으로 재현했습니다. 실제 Jira 계정이 없어도 로컬 mock 클라이언트로 전체 흐름을 그대로 체험할 수 있습니다.

`data/mock_test_sheet.csv`는 **실제 Google Sheet와 동일하게, 유일한 하나의 파일을 계속 읽고 그 자리에 다시 씁니다** (별도의 "결과 파일"을 만들지 않습니다). 이 파일은 실행할수록 계속 바뀌므로 git에는 커밋하지 않고, 대신 절대 바뀌지 않는 `data/mock_test_sheet_seed.csv`(최초 데모 데이터)를 커밋해두었습니다 — 최초 실행 시 이 파일에서 시트가 자동으로 만들어지고, `--reset` 옵션으로 언제든 티켓 이력까지 지우고 처음 상태로 되돌릴 수 있습니다.

모든 스크립트는 **초안/티켓까지만 생성**하며, 실제 서비스 반영이나 최종 판단은 QA 엔지니어의 검토를 거치는 것을 전제로 설계했습니다. (실제 영향도·비즈니스 맥락은 사람이 판단해야 하는 영역이라고 생각해서, 자동 등록이 아니라 "초안 생성 → 사람 검토 → 등록"의 흐름을 유지했습니다.)

## 폴더 구조

```
ai-qa-draft-generator/
├── README.md
├── requirements.txt
├── .env.example
├── src/
│   ├── llm_client.py          # Anthropic / OpenAI 겸용 LLM 호출 래퍼
│   ├── prompts.py              # 프롬프트 템플릿
│   ├── generate_test_cases.py  # 테스트케이스 초안 생성 CLI
│   ├── generate_issue_draft.py # 이슈 초안 생성 CLI
│   ├── mock_jira_client.py     # 실제 Jira API 대신 로컬에 티켓을 생성·상태 관리하는 mock 클라이언트
│   ├── resolve_ticket.py       # 개발자가 티켓을 Resolved로 바꾸는 상황을 흉내내는 CLI
│   └── run_pipeline.py         # 시트 <-> BTS 양방향 동기화 end-to-end 데모
├── data/
│   └── mock_test_sheet_seed.csv  # 최초 데모 데이터 (git 추적됨, 파이프라인이 절대 수정 안 함)
│                                   # mock_test_sheet.csv는 최초 실행 시 여기서 자동 생성되는
│                                   # "살아있는 시트"라 계속 갱신되므로 git에는 올리지 않음
└── examples/
    ├── sample_requirement.md       # 입력 예시 (기능 요구사항)
    ├── sample_output_testcases.md  # 출력 예시 (테스트케이스 초안)
    ├── sample_bug_report.md        # 입력 예시 (버그 재현 메모)
    └── sample_output_issue.md      # 출력 예시 (이슈 초안)
```

## 빠른 실행 (다운로드 후 설정 없이 바로 실행)

```bash
git clone <이 저장소 URL>
cd ai-qa-draft-generator
pip install -r requirements.txt

python src/run_pipeline.py
```

API 키를 설정하지 않아도 바로 실행됩니다. 최초 실행 시 `data/mock_test_sheet_seed.csv`에서 `data/mock_test_sheet.csv`(살아있는 시트)를 자동으로 만들고, 그 안에서 Fail 건을 찾아 이슈 초안(템플릿 기반)을 만든 뒤 `tickets/QA-1001.md` 형태로 mock 티켓을 생성하고, 티켓 번호를 같은 시트 파일에 다시 채워 넣습니다. 실행 결과는 터미널에 아래처럼 출력됩니다.

```
생성됨: QA-1001  (iOS / 출금 한도 알림 - 한도 100% 초과 시 버튼 비활성화)
생성됨: QA-1002  (AOS / 자정 기준 초기화 - 자정 경과 시 누적액 초기화)
...
동기화된 티켓 상태: 0건 / 새로 생성한 이슈 티켓: 5건
```

**LLM로 업그레이드하려면**: `.env`에 `ANTHROPIC_API_KEY` 또는 `OPENAI_API_KEY`를 넣고 다시 실행하면, 템플릿 대신 LLM이 재현 절차 정리·우선순위 제안까지 포함한 이슈 초안을 생성합니다.

```bash
cp .env.example .env   # 키 입력 후
python src/run_pipeline.py
```

**양방향 동기화(BTS → 시트)를 체험하려면**: 위 실행으로 티켓이 생성된 뒤, 개발자가 그중 하나를 고쳤다고 가정하고 Resolved로 바꿔보세요.

```bash
python src/resolve_ticket.py QA-1001 --note "디바운스 로직 추가로 수정 완료"
python src/run_pipeline.py   # 다시 실행하면 QA-1001이 Resolved로 동기화됨
```

두 번째 실행 후 시트(`data/mock_test_sheet.csv`)의 `iOS Ticket` 칸이 `QA-1001`에서 `QA-1001 (Resolved)`로 바뀐 것을 확인할 수 있습니다.

**처음부터 다시 보고 싶다면** 티켓 이력을 모두 지우고 시트를 데모 데이터로 되돌리는 옵션을 쓰세요.

```bash
python src/run_pipeline.py --reset
```

개별 기능만 테스트하고 싶다면 (이 두 스크립트는 `run_pipeline.py`와 달리 템플릿 fallback이 없어서 `.env`에 API 키 설정이 필요합니다. 키 없이 결과물 형태만 보고 싶다면 `examples/` 폴더의 출력 예시를 참고하세요):

```bash
# 테스트케이스 초안 생성
python src/generate_test_cases.py --input examples/sample_requirement.md --platform "Android,iOS,Web"

# 이슈 초안 생성
python src/generate_issue_draft.py --input examples/sample_bug_report.md
```

`examples/` 폴더에는 API 키 없이도 결과물의 형태를 바로 확인할 수 있도록 입력/출력 예시를 함께 넣어두었습니다.

## 실제 업무 적용 시 확인된 효과 (참고)

동일한 컨셉을 실무 워크플로우에 적용했을 때 기준으로,

- 테스트케이스 설계 시간 약 40% 단축
- 반복적인 이슈 리포팅 시간 약 30% 감소

를 확인했습니다. (수치는 실제 업무 환경에서의 측정값이며, 이 저장소는 그 개념을 보여주기 위한 재구현 예제입니다.)

## 기술 스택

Python 3.10+, Anthropic/OpenAI API, argparse 기반 CLI

## 라이선스

MIT
