# AI Agent NPC Conversation

A project where AI Agents with different personalities engage in free conversations.
Six AI Agents each have unique personalities and system prompts to conduct conversations without human intervention.

## Components

### Example AI Agent Personality

- You can modify the `./backend/agents.json` file to set desired personalities.

#### Expert

- **Kim Coding (Engineer)**: Experienced software developer providing practical, work-focused advice
- **Park Design (Artist)**: Experienced UI/UX designer providing trend and practical advice
- **Lee Marketing (Scientist)**: Experienced marketing expert providing realistic strategies and advice
- **Choi Product (Psychologist)**: Project-focused product manager providing problem-solving and teamwork advice
- **Jung Student (Historian)**: University student interested in IT/design, sharing latest trends and learning experiences
- **Han General (Philosopher)**: General person interested in various fields, providing realistic concerns and everyday perspectives

#### Character Agent

- **Monkey D. Luffy (Philosopher)**: Protagonist of One Piece, a free and pure pirate king aspirant
- **Kamado Tanjiro (Psychologist)**: Protagonist of Demon Slayer, a warm and persistent demon slayer
- **Tony Stark (Engineer)**: Marvel's Iron Man, a genius inventor and innovative scientist
- **Steve Rogers (Historian)**: Marvel's Captain America, a true hero defending justice and freedom
- **Peter Parker (Scientist)**: Marvel's Spider-Man, a smart and responsible high school hero

### Key features

- **Multiple AI Agents**: 11 AI Agents with unique personalities (experts + characters)
- **Unlimited Conversations**: Automated conversations without human intervention
- **Memory System**: Conversation history and context memory
- **Real-time Monitoring**: Real-time conversation observation via WebSocket
- **Streaming Feature**: Real-time typing effect for AI (configurable enable/disable)
- **Conversation Control**: Start and stop functionality
- **Dark Mode**: Light/dark theme support
- **Web Interface**: Modern ChatGPT-style UI
- **CLI Mode**: Direct conversation monitoring in terminal

### Tech stack

- **Backend**: FastAPI, Python 3.12+, Pydantic v2
- **Frontend**: Next.js 15, React 18, Tailwind CSS, Radix UI
- **LLM**: vLLM, Ollama, OpenAI API support
- **Memory**: In-memory, Redis, PostgreSQL support
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

**All backend environment variables must be managed only in the `.env` file at the project root.**

```bash
# Copy .env.example to create .env file
cp .env.example .env
```

**Example .env file key items and descriptions:**

```env
# LLM Settings
LLM_PROVIDER=vllm  # vllm, ollama, openai
VLLM_URL=your_vllm_url
VLLM_MODEL=your_vllm_load_model

# Memory Settings
MEMORY_TYPE=inmemory  # inmemory, redis, postgresql
REDIS_URL=redis://localhost:6379
POSTGRES_URL=postgresql://user:password@localhost:5432/conversation

# Server Settings
HOST=0.0.0.0
PORT=8000

# Logging Settings
LOG_LEVEL=INFO
LOG_FILE_PATH=./logs/app.log

# Streaming Settings
ENABLE_STREAMING=true  # Enable/disable real-time typing effect

# Conversation History Settings
# CONVERSATION_HISTORY_LIMIT: Maximum number of past messages (history) referenced when generating prompts (e.g., 20)
CONVERSATION_HISTORY_LIMIT=20

# Conversation Context Settings
# CONVERSATION_CONTEXT_LIMIT: Maximum number of context messages passed to LLM (e.g., 10)
CONVERSATION_CONTEXT_LIMIT=10

# Unlimited Conversation Settings
# CONVERSATION_UNLIMITED: true for unlimited turns, false for CONVERSATION_MAX_TURNS only (e.g., true)
CONVERSATION_UNLIMITED=true

# CORS Settings
# CORS_ORIGINS: List of allowed origins (domains), separated by commas. Use * for all (default)
CORS_ORIGINS=*
```

**.env file must be included in .gitignore and should not be exposed externally.**

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
# Start backend server
cd backend
python run_server.py

# Start frontend development server (new terminal)
cd frontend
npm run dev
```

## Testing and Coverage

### Backend Test

```bash
cd backend
# If PYTHONPATH issues occur, run as follows
PYTHONPATH=./app pytest --cov=app --cov-report=term-missing
```

## Project Structure

```
llm_conversation/
├── .env                  # All backend environment variables (located at root)
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes.py          # API router
│   │   ├── cli/
│   │   │   └── cli_app.py         # CLI application
│   │   ├── models/
│   │   │   ├── agent.py           # Agent model
│   │   │   ├── conversation.py    # Conversation model
│   │   │   └── memory.py          # Memory model
│   │   ├── services/
│   │   │   ├── conversation_service.py  # Conversation service
│   │   │   ├── llm_service.py     # LLM service
│   │   │   ├── memory_service.py  # Memory service
│   │   │   └── logging_service.py # Logging service
│   │   ├── config.py              # Configuration management
│   │   └── main.py                # FastAPI app
│   ├── agents.json                # Agent configuration
│   ├── requirements.txt           # Python dependencies
│   ├── run_cli.py                 # CLI execution script
│   └── run_server.py              # Server execution script
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx           # Main page
│   │   │   ├── layout.tsx         # Layout
│   │   │   └── globals.css        # Global styles
│   │   ├── components/
│   │   │   └── ui/                # UI components
│   │   └── lib/
│   │       └── utils.ts           # Utility functions
│   ├── package.json               # Node.js dependencies
│   ├── tailwind.config.js         # Tailwind configuration
│   └── next.config.js             # Next.js configuration
└── README.md                      # Project documentation
```

## Key Features

### Unlimited Turn Support

- **Unlimited Conversations**: Easily set unlimited conversations with checkbox
- **Limited Conversations**: Choose between 10-50 turns
- Current turn and maximum turn display in system prompt
- Guidelines for deep conversations included
- Frontend default: 10 turns (limited)
- Backend default: 10 turns (limited)

### Real-time Logging

- ECS Logging 2.2.0 based logging system
- Agent conversation messages and LLM request logging
- Conversation start/end event recording
- Custom formatter for Korean language support

### Flexible LLM Engine Support

- vLLM, Ollama, OpenAI API support
- Optimized message formatting for each provider
- Connection testing and detailed information return

### Streaming Feature

- **Real-time Typing Effect**: Effect where AI appears to write text in real-time
- **Configurable**: Enable/disable with `ENABLE_STREAMING` environment variable
- **Performance Optimization**: Faster response processing when streaming is disabled
- **User Experience**: More natural conversation feel when streaming is enabled

**Streaming Settings Example:**

```env
# Enable streaming feature (default)
ENABLE_STREAMING=true

# Disable streaming feature (faster response)
ENABLE_STREAMING=false
```

### Modern UI/UX

- Next.js 15 and React 18 based
- Tailwind CSS and Radix UI components
- Intuitive ChatGPT-style interface
- Light/dark mode support

## Troubleshooting

### Common Issues

1. **LLM Connection Failed**

   - Check vLLM URL and model name
   - Verify network connection status
   - Check API key settings (when using OpenAI)

2. **Memory Error**

   - Check Redis/PostgreSQL connection settings
   - Test with in-memory mode

3. **Frontend Build Error**
   - Check Node.js version (22.0.0 or higher)
   - Reinstall dependencies: `npm install`

### Check logs

```bash
# Backend logs
tail -f backend/logs/app.log

# Frontend development server logs
cd frontend && npm run dev
```

## License

This project is distributed under the MIT License. For more details, see the `LICENSE` file.

## System Diagram

This project includes PlantUML diagrams to help understand the structure and operation of the project.

### Sequence Diagram

- **`sequence_diagram.puml`**: Overall system sequence diagram

  - Complete flow from system initialization to conversation creation, progression, and termination
  - Real-time communication via WebSocket
  - Interaction with LLM service
  - Memory management system

- **`agent_conversation_sequence.puml`**: Agent conversation progression sequence
  - Conversation process between 5 character agents
  - Turn-by-turn speaking order for each agent
  - Context-based response generation
  - History management through memory system

### Architecture Diagram

- **`system_architecture.puml`**: Overall system architecture

  - Frontend, Backend, Service, Model layer structure
  - External service connections (vLLM, Redis, PostgreSQL)
  - Component dependency relationships

- **`agent_data_model.puml`**: Data model structure
  - Agent, Conversation, Message class relationships
  - Memory Interface and implementations
  - Database schema structure

### How to use PlantUML diagrams

PlantUML diagram:

1. **Online Viewer**:

   - [PlantUML Online Server](http://www.plantuml.com/plantuml/uml/)
   - Copy and paste content from each `.puml` file

2. **VS Code Extension**:

   - Install PlantUML extension
   - Open `.puml` file and preview with `Alt+Shift+D`

3. **Local Installation**:
   ```bash
   # Install PlantUML (Java required)
   java -jar plantuml.jar sequence_diagram.puml
   ```

## Support

- If you have any issues or questions, please create an issue.
