# AI Agent NPC Conversation

AI Agent들이 서로 다른 인격을 가지고 자유롭게 대화를 수행하는 프로젝트입니다.
6명의 AI Agent가 각각 고유한 인격과 시스템 프롬프트를 가지고 인간의 개입 없이 대화를 진행합니다.

## Components

### Example AI Agent Personality

- ./backend/agents.json 파일을 수정하여 원하는 인격으로 설정할 수 있습니다.

#### Expert

- **김코딩 (엔지니어)**: 경험 많은 소프트웨어 개발자, 실무 중심의 현실적 조언 제공
- **박디자인 (예술가)**: 실무 경험이 풍부한 UI/UX 디자이너, 트렌드와 실용적 조언 제공
- **이마케팅 (과학자)**: 실전 경험이 풍부한 마케팅 전문가, 현실적 전략과 조언 제공
- **최프로덕트 (심리학자)**: 프로젝트 실무 중심의 프로덕트 매니저, 문제 해결과 팀워크 조언 제공
- **정학생 (역사가)**: IT/디자인 관심 대학생, 최신 트렌드와 학습 경험 공유
- **한일반 (철학자)**: 다양한 분야에 관심 있는 일반인, 현실적 고민과 일상적 시각 제공

#### Character Agent

- **몽키 D 루피 (철학자)**: 원피스의 주인공, 자유롭고 순수한 성격의 해적왕 지망생
- **카마도 탄지로 (심리학자)**: 귀멸의 칼날의 주인공, 따뜻하고 끈기 있는 귀살대 검사
- **토니 스타크 (엔지니어)**: 마블의 아이언맨, 천재적인 발명가이자 혁신적인 과학자
- **스티브 로저스 (역사가)**: 마블의 캡틴 아메리카, 정의와 자유를 수호하는 진정한 영웅
- **피터 파커 (과학자)**: 마블의 스파이더맨, 똑똑하고 책임감 있는 고등학생 영웅

### Key features

- **다중 AI Agent**: 11명의 고유한 인격을 가진 AI Agent (실무 전문가 + 캐릭터)
- **무제한 대화**: 인간 개입 없이 자동으로 진행되는 대화
- **메모리 시스템**: 대화 히스토리와 컨텍스트 기억
- **실시간 모니터링**: WebSocket을 통한 실시간 대화 관찰
- **스트림 기능**: AI가 실시간으로 타이핑하는 효과 (설정으로 활성화/비활성화 가능)
- **대화 제어**: 시작, 중지 기능
- **다크모드**: 라이트/다크 테마 지원
- **웹 인터페이스**: ChatGPT 스타일의 현대적 UI
- **CLI 모드**: 터미널에서 직접 대화 모니터링

### Tech stack

- **Backend**: FastAPI, Python 3.12+, Pydantic v2
- **Frontend**: Next.js 15, React 18, Tailwind CSS, Radix UI
- **LLM**: vLLM, Ollama, OpenAI API 지원
- **Memory**: 인메모리, Redis, PostgreSQL 지원
- **Real-time**: WebSocket
- **Logging**: ECS Logging 2.2.0

## Requirements

### System Requirements

- Python 3.12+
- Node.js 22.0.0+
- Redis (optional)
- PostgreSQL (optional)

### LLM Requirements

- vLLM server (default)
- Ollama (optional)
- OpenAI API key (optional)

## Installation and Running

### 1. Repository Clone

```bash
git clone https://github.com/sujae-yu/ai-llm-conversation.git
cd ai-llm-conversation
```

### 2. Environment Settings (Required)

**모든 백엔드 환경 변수는 반드시 프로젝트 루트의 `.env` 파일에서만 관리됩니다.**

```bash
# .env.example 파일을 복사하여 .env 파일 생성
cp .env.example .env
```

**예시 .env 파일 주요 항목 및 설명:**

```env
# LLM 설정
LLM_PROVIDER=vllm  # vllm, ollama, openai
VLLM_URL=your_vllm_url
VLLM_MODEL=your_vllm_load_model

# 메모리 설정
MEMORY_TYPE=inmemory  # inmemory, redis, postgresql
REDIS_URL=redis://localhost:6379
POSTGRES_URL=postgresql://user:password@localhost:5432/conversation

# 서버 설정
HOST=0.0.0.0
PORT=8000

# 로깅 설정
LOG_LEVEL=INFO
LOG_FILE_PATH=./logs/app.log

# 스트림 설정
ENABLE_STREAMING=true  # 실시간 타이핑 효과 활성화/비활성화

# 대화 히스토리 설정
# CONVERSATION_HISTORY_LIMIT: 프롬프트 생성 시 참고하는 과거 메시지(히스토리) 최대 개수 (예: 20)
CONVERSATION_HISTORY_LIMIT=20

# 대화 컨텍스트 설정
# CONVERSATION_CONTEXT_LIMIT: LLM에 전달하는 컨텍스트 메시지 최대 개수 (예: 10)
CONVERSATION_CONTEXT_LIMIT=10

# 무제한 대화 설정
# CONVERSATION_UNLIMITED: true면 턴 수 무제한, false면 CONVERSATION_MAX_TURNS만큼만 대화 (예: true)
CONVERSATION_UNLIMITED=true

# CORS 설정
# CORS_ORIGINS: 허용할 오리진(도메인) 목록, 쉼표(,)로 구분. 전체 허용은 * (기본값)
CORS_ORIGINS=*
```

**.env 파일은 반드시 .gitignore에 포함되어야 하며, 외부에 유출되지 않도록 주의하세요.**

### 3. Backend Dependency Installation

```bash
cd backend
pip install -r requirements.txt
```

### 4. Frontend Dependency Installation

```bash
cd frontend
npm install
```

### 5. Running

#### CLI mode (terminal conversation monitoring)

```bash
cd backend
python run_cli.py
```

#### Server Mode (Web UI)

```bash
# 백엔드 서버 시작
cd backend
python run_server.py

# 프론트엔드 개발 서버 시작 (새 터미널)
cd frontend
npm run dev
```

## Testing and Coverage

### Backend Test

```bash
cd backend
# PYTHONPATH 문제 발생 시 아래와 같이 실행
PYTHONPATH=./app pytest --cov=app --cov-report=term-missing
```

## Project Structure

```
llm_conversation/
├── .env                  # 모든 백엔드 환경 변수 관리 (루트에 위치)
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes.py          # API 라우터
│   │   ├── cli/
│   │   │   └── cli_app.py         # CLI 애플리케이션
│   │   ├── models/
│   │   │   ├── agent.py           # 에이전트 모델
│   │   │   ├── conversation.py    # 대화 모델
│   │   │   └── memory.py          # 메모리 모델
│   │   ├── services/
│   │   │   ├── conversation_service.py  # 대화 서비스
│   │   │   ├── llm_service.py     # LLM 서비스
│   │   │   ├── memory_service.py  # 메모리 서비스
│   │   │   └── logging_service.py # 로깅 서비스
│   │   ├── config.py              # 설정 관리
│   │   └── main.py                # FastAPI 앱
│   ├── agents.json                # 에이전트 설정
│   ├── requirements.txt           # Python 의존성
│   ├── run_cli.py                 # CLI 실행 스크립트
│   └── run_server.py              # 서버 실행 스크립트
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx           # 메인 페이지
│   │   │   ├── layout.tsx         # 레이아웃
│   │   │   └── globals.css        # 전역 스타일
│   │   ├── components/
│   │   │   └── ui/                # UI 컴포넌트
│   │   └── lib/
│   │       └── utils.ts           # 유틸리티 함수
│   ├── package.json               # Node.js 의존성
│   ├── tailwind.config.js         # Tailwind 설정
│   └── next.config.js             # Next.js 설정
└── README.md                      # 프로젝트 문서
```

## Key Features

### Unlimited Turn Support

- **무제한 대화**: 체크박스로 간편하게 무제한 대화 설정
- **제한 대화**: 10-50턴 사이에서 선택 가능
- 시스템 프롬프트에 현재 턴수와 최대 턴수 표시
- 깊이 있는 대화를 위한 지침 포함
- 프론트엔드 기본값: 10턴 (제한)
- 백엔드 기본값: 10턴 (제한)

### Real-time Logging

- ECS Logging 2.2.0 기반 로그 시스템
- 에이전트 대화 메시지와 LLM 요청 로깅
- 대화 시작/종료 이벤트 기록
- 한글 지원을 위한 커스텀 포맷터

### Flexible LLM Engine Support

- vLLM, Ollama, OpenAI API 지원
- 각 제공업체별 최적화된 메시지 포맷팅
- 연결 테스트 및 상세 정보 반환

### Streaming Feature

- **실시간 타이핑 효과**: AI가 실시간으로 글을 작성하는 것처럼 보이는 효과
- **설정 가능**: `ENABLE_STREAMING` 환경 변수로 활성화/비활성화 가능
- **성능 최적화**: 스트림 비활성화 시 더 빠른 응답 처리
- **사용자 경험**: 스트림 활성화 시 더 자연스러운 대화 느낌

**Streaming Settings Example:**

```env
# 스트림 기능 활성화 (기본값)
ENABLE_STREAMING=true

# 스트림 기능 비활성화 (더 빠른 응답)
ENABLE_STREAMING=false
```

### Modern UI/UX

- Next.js 15와 React 18 기반
- Tailwind CSS와 Radix UI 컴포넌트
- ChatGPT 스타일의 직관적 인터페이스
- 라이트/다크 모드 지원

## Troubleshooting

### Common Issues

1. **LLM Connection Failed**

   - vLLM URL과 모델명 확인
   - 네트워크 연결 상태 확인
   - API 키 설정 확인 (OpenAI 사용 시)

2. **Memory Error**

   - Redis/PostgreSQL 연결 설정 확인
   - 인메모리 모드로 테스트

3. **Frontend Build Error**
   - Node.js 버전 확인 (22.0.0 이상)
   - 의존성 재설치: `npm install`

### Check logs

```bash
# 백엔드 로그
tail -f backend/logs/app.log

# 프론트엔드 개발 서버 로그
cd frontend && npm run dev
```

## License

This project is distributed under the MIT License. For more details, see the `LICENSE` file.

## System Diagram

This project includes PlantUML diagrams to help understand the structure and operation of the project.

### Sequence Diagram

- **`sequence_diagram.puml`**: 전체 시스템의 시퀀스 다이어그램

  - 시스템 초기화부터 대화 생성, 진행, 종료까지의 전체 플로우
  - WebSocket을 통한 실시간 통신
  - LLM 서비스와의 상호작용
  - 메모리 관리 시스템

- **`agent_conversation_sequence.puml`**: 에이전트 대화 진행 시퀀스
  - 5명의 캐릭터 에이전트 간 대화 진행 과정
  - 각 에이전트의 턴별 발화 순서
  - 컨텍스트 기반 응답 생성
  - 메모리 시스템을 통한 히스토리 관리

### Architecture Diagram

- **`system_architecture.puml`**: 시스템 전체 아키텍처

  - Frontend, Backend, Service, Model 레이어 구조
  - 외부 서비스 (vLLM, Redis, PostgreSQL) 연결
  - 컴포넌트 간 의존성 관계

- **`agent_data_model.puml`**: 데이터 모델 구조
  - Agent, Conversation, Message 클래스 관계
  - Memory Interface와 구현체들
  - 데이터베이스 스키마 구조

### How to use PlantUML diagrams

PlantUML diagram:

1. **Online Viewer**:

   - [PlantUML Online Server](http://www.plantuml.com/plantuml/uml/)
   - 각 `.puml` 파일의 내용을 복사하여 붙여넣기

2. **VS Code Extension**:

   - PlantUML 확장 설치
   - `.puml` 파일을 열고 `Alt+Shift+D`로 미리보기

3. **Local Installation**:
   ```bash
   # PlantUML 설치 (Java 필요)
   java -jar plantuml.jar sequence_diagram.puml
   ```

## Support

- If you have any issues or questions, please create an issue.
