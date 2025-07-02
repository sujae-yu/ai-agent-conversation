import asyncio
import json
import os
import sys
from typing import List, Optional
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from app.models.agent import Agent
from app.models.conversation import ConversationRequest
from app.services.conversation_service import ConversationService
from app.config import settings

console = Console()


class CLIConversationViewer:
    """CLI 대화 뷰어"""
    
    def __init__(self):
        self.current_conversation = None
        self.is_running = False
        self.conversation_service = ConversationService()
        self.agents = self._load_agents()
    
    def _load_agents(self) -> List[Agent]:
        """에이전트 설정 로드"""
        try:
            agents_path = os.path.join(project_root, "agents.json")
            with open(agents_path, "r", encoding="utf-8") as f:
                agents_data = json.load(f)
            
            agents = []
            for agent_id, agent_data in agents_data["agents"].items():
                agent = Agent(
                    id=agent_id,
                    name=agent_data["name"],
                    personality=agent_data["personality"],
                    system_prompt=agent_data["system_prompt"],
                    description=agent_data["description"]
                )
                agents.append(agent)
            
            return agents
            
        except Exception as e:
            console.print(f"[red]에이전트 설정 로드 오류: {str(e)}[/red]")
            return []
    
    async def show_main_menu(self):
        """메인 메뉴 표시"""
        while True:
            console.clear()
            console.print(Panel.fit(
                "[bold blue]AI Agent NPC 대화 시스템[/bold blue]\n"
                "[dim]CLI 모드 - AI Agent들이 서로 대화하는 것을 모니터링하세요[/dim]",
                border_style="blue"
            ))
            
            # 현재 상태 표시
            if self.current_conversation:
                status_color = {
                    'idle': 'yellow',
                    'active': 'green',
                    'paused': 'orange',
                    'stopped': 'red',
                    'ended': 'red',
                    'error': 'red'
                }.get(self.current_conversation.status, 'white')
                
                # 턴 정보 표시
                max_turns_display = "무제한" if self.current_conversation.is_unlimited else str(self.current_conversation.max_turns)
                
                try:
                    console.print(Panel(
                        f"[bold]현재 대화:[/bold] {self.current_conversation.topic}\n"
                        f"[bold]상태:[/bold] [{status_color}]{self.current_conversation.status}[/{status_color}]\n"
                        f"[bold]턴:[/bold] {self.current_conversation.current_turn}/{max_turns_display}",
                        border_style=status_color
                    ))
                except Exception as e:
                    console.print(f"[bold]현재 대화:[/bold] {self.current_conversation.topic}")
                    console.print(f"[bold]상태:[/bold] {self.current_conversation.status}")
                    console.print(f"[bold]턴:[/bold] {self.current_conversation.current_turn}/{max_turns_display}")
            
            # 메뉴 옵션
            console.print("\n[bold]메뉴:[/bold]")
            console.print("1. 새 대화 생성")
            console.print("2. 대화 목록 보기")
            console.print("3. 대화 선택")
            console.print("4. 대화 시작/중지")
            console.print("5. 실시간 모니터링")
            console.print("6. 에이전트 정보 보기")
            console.print("7. LLM 연결 테스트")
            console.print("8. 종료")
            
            choice = Prompt.ask("\n선택", choices=["1", "2", "3", "4", "5", "6", "7", "8"])
            
            if choice == "1":
                await self._create_conversation()
            elif choice == "2":
                await self.list_conversations()
            elif choice == "3":
                await self.select_conversation()
            elif choice == "4":
                await self.control_conversation()
            elif choice == "5":
                await self.monitor_conversation()
            elif choice == "6":
                await self.show_agents()
            elif choice == "7":
                await self._test_llm_connection()
            elif choice == "8":
                if Confirm.ask("정말 종료하시겠습니까?"):
                    break
    
    async def _create_conversation(self):
        """새 대화 생성"""
        console.clear()
        console.print(Panel.fit("[bold]새 대화 생성[/bold]", border_style="green"))
        
        # 주제 입력
        console.print("\n[bold]대화 주제 입력[/bold]")
        console.print("[dim]예시: 인공지능의 미래, 게임 개발 이야기, 기술 트렌드 등[/dim]")
        topic = Prompt.ask("대화 주제를 입력하세요", default="AI 기술과 미래")
        if not topic:
            console.print("[red]주제를 입력해주세요.[/red]")
            Prompt.ask("\n계속하려면 Enter를 누르세요")
            return
        
        # 에이전트 선택
        selected_agents = await self._select_agents()
        if not selected_agents:
            console.print("[red]에이전트를 선택해주세요.[/red]")
            Prompt.ask("\n계속하려면 Enter를 누르세요")
            return
        
        # 턴 수 설정
        max_turns = await self._get_turn_count()
        
        # 대화 요청 생성
        request = ConversationRequest(
            topic=topic,
            agent_ids=[agent.id for agent in selected_agents],
            max_turns=max_turns
        )
        
        # 대화 생성
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("대화 생성 중...", total=None)
            conversation = await self.conversation_service.create_conversation(request)
            progress.update(task, completed=True)
        
        console.print(f"\n[green]✅ 대화가 생성되었습니다![/green]")
        console.print(f"대화 ID: {conversation.id}")
        console.print(f"주제: {conversation.topic}")
        console.print(f"참여자: {', '.join([agent.name for agent in selected_agents])}")
        console.print(f"최대 턴: {'무제한' if conversation.is_unlimited else max_turns}")
        
        # 생성 즉시 대화 시작 및 모니터링 모드 진입
        await self._start_conversation(conversation.id, auto_monitor=True)
    
    async def _select_agents(self) -> List[Agent]:
        """에이전트 선택"""
        console.print("\n[bold]에이전트 선택[/bold]")
        console.print("0. 전체 선택")
        console.print("all. 전체 선택 (단축)")
        
        # 에이전트 목록 표시
        agent_table = Table(title="사용 가능한 에이전트")
        agent_table.add_column("ID", style="cyan")
        agent_table.add_column("이름", style="green")
        agent_table.add_column("설명", style="white")
        
        for agent in self.agents:
            agent_table.add_row(agent.id, agent.name, agent.description)
        
        console.print(agent_table)
        
        while True:
            agent_ids_input = Prompt.ask("\n에이전트 ID를 입력하세요 (쉼표로 구분, 0 또는 all로 전체 선택)")
            if agent_ids_input.strip() in ["0", "all"]:
                return self.agents
            
            agent_ids = [aid.strip() for aid in agent_ids_input.split(",") if aid.strip()]
            if all(aid in [agent.id for agent in self.agents] for aid in agent_ids):
                return [agent for agent in self.agents if agent.id in agent_ids]
            
            console.print("[red]잘못된 에이전트 ID가 포함되어 있습니다. 다시 입력하세요.[/red]")
    
    async def _get_turn_count(self) -> int:
        """턴 수 입력"""
        console.print("\n[bold]턴 수 설정[/bold]")
        console.print("0 또는 음수: 무제한")
        console.print("양수: 지정된 턴 수")
        
        try:
            turns = int(Prompt.ask("턴 수를 입력하세요", default="10"))
            return turns
        except ValueError:
            console.print("[yellow]숫자를 입력해주세요. 기본값(10)을 사용합니다.[/yellow]")
            return 10
    
    async def _start_conversation(self, conversation_id: str, auto_monitor: bool = False):
        """대화 시작"""
        console.print(f"\n[green]🚀 대화 시작: {conversation_id}[/green]")
        console.print("-" * 50)
        
        try:
            # 대화 시작
            success = await self.conversation_service.start_conversation(conversation_id)
            if not success:
                console.print("[red]대화 시작에 실패했습니다.[/red]")
                return
            
            # auto_monitor 옵션이 True면 바로 모니터링 진입
            if auto_monitor:
                self.current_conversation = self.conversation_service.get_conversation(conversation_id)
                
                # 자동 대화 진행을 별도 태스크로 실행
                asyncio.create_task(self._auto_continue_conversation(conversation_id))
                
                await self.monitor_conversation()
                return
            
            # 대화 진행
            while True:
                conversation = self.conversation_service.get_conversation(conversation_id)
                if not conversation:
                    console.print("[red]대화를 찾을 수 없습니다.[/red]")
                    break
                
                # 대화 종료 조건 확인
                if conversation.status == "ended":
                    console.print("\n[green]🏁 대화가 종료되었습니다.[/green]")
                    break
                
                # 사용자 입력 확인
                user_input = Prompt.ask("\n다음 턴으로 진행하시겠습니까?", choices=["y", "n", "q"], default="y")
                
                if user_input == 'q':
                    # 대화 종료
                    await self.conversation_service.end_conversation(conversation_id)
                    console.print("[yellow]대화를 종료합니다.[/yellow]")
                    break
                elif user_input == 'y':
                    # 대화 계속
                    success = await self.conversation_service.continue_conversation(conversation_id)
                    if not success:
                        console.print("[red]대화 진행에 실패했습니다.[/red]")
                        break
                else:
                    console.print("[yellow]대화를 일시정지합니다.[/yellow]")
                    break
                    
        except KeyboardInterrupt:
            console.print("\n[yellow]대화를 중단합니다.[/yellow]")
            await self.conversation_service.end_conversation(conversation_id)
        except Exception as e:
            console.print(f"[red]대화 진행 오류: {str(e)}[/red]")
    
    async def _auto_continue_conversation(self, conversation_id: str):
        """자동으로 대화 계속 진행 (별도 태스크)"""
        try:
            while True:
                conversation = self.conversation_service.get_conversation(conversation_id)
                if not conversation:
                    break
                
                # 대화 종료 조건 확인
                if conversation.status == "ended":
                    break
                
                # 대화 간격 설정
                await asyncio.sleep(settings.conversation_turn_interval)
                
                # 대화 계속
                success = await self.conversation_service.continue_conversation(conversation_id)
                if not success:
                    break
                
        except Exception as e:
            logger.error(f"자동 대화 진행 오류: {str(e)}")
            await self.conversation_service.end_conversation(conversation_id)
    
    async def list_conversations(self):
        """대화 목록 표시"""
        console.clear()
        console.print(Panel.fit("[bold]대화 목록[/bold]", border_style="blue"))
        
        conversations = self.conversation_service.get_all_conversations()
        
        if not conversations:
            console.print("[yellow]생성된 대화가 없습니다.[/yellow]")
            Prompt.ask("\n계속하려면 Enter를 누르세요")
            return
        
        table = Table()
        table.add_column("ID", style="cyan", width=36)
        table.add_column("주제", style="green")
        table.add_column("상태", style="yellow")
        table.add_column("턴", style="blue")
        table.add_column("생성일", style="white")
        
        for conv in conversations:
            status_color = {
                'idle': 'yellow',
                'active': 'green',
                'paused': 'orange',
                'stopped': 'red',
                'ended': 'red',
                'error': 'red'
            }.get(conv.status, 'white')
            
            # 턴 정보 표시
            max_turns_display = "무제한" if conv.is_unlimited else str(conv.max_turns)
            
            table.add_row(
                conv.id[:8] + "...",
                conv.topic,
                f"[{status_color}]{conv.status}[/{status_color}]",
                f"{conv.current_turn}/{max_turns_display}",
                conv.created_at.strftime("%Y-%m-%d %H:%M")
            )
        
        console.print(table)
        Prompt.ask("\n계속하려면 Enter를 누르세요 (뒤로가려면 0 또는 b 입력)")
    
    async def select_conversation(self):
        """대화 선택"""
        conversations = self.conversation_service.get_all_conversations()
        
        if not conversations:
            console.print("[yellow]선택할 대화가 없습니다.[/yellow]")
            Prompt.ask("\n계속하려면 Enter를 누르세요")
            return
        
        console.clear()
        console.print(Panel.fit("[bold]대화 선택[/bold]", border_style="green"))
        
        for i, conv in enumerate(conversations, 1):
            console.print(f"{i}. {conv.topic} ({conv.status})")
        console.print("0. 뒤로가기")
        
        while True:
            choice = Prompt.ask("\n선택", choices=[str(i) for i in range(0, len(conversations) + 1)])
            if choice == "0":
                return  # 뒤로가기
            try:
                idx = int(choice)
                self.current_conversation = conversations[idx - 1]
                console.print(f"[green]선택됨: {self.current_conversation.topic}[/green]")
                break
            except (ValueError, IndexError):
                console.print("[red]잘못된 선택입니다.[/red]")
        Prompt.ask("\n계속하려면 Enter를 누르세요")
    
    async def control_conversation(self):
        """대화 제어"""
        if not self.current_conversation:
            console.print("[yellow]먼저 대화를 선택하세요.[/yellow]")
            Prompt.ask("\n계속하려면 Enter를 누르세요")
            return
        
        console.clear()
        console.print(Panel.fit("[bold]대화 제어[/bold]", border_style="blue"))
        console.print(f"현재 대화: {self.current_conversation.topic}")
        console.print(f"상태: {self.current_conversation.status}")
        console.print("0. 뒤로가기")
        
        if self.current_conversation.status == 'idle':
            if Confirm.ask("대화를 시작하시겠습니까?"):
                await self.conversation_service.start_conversation(self.current_conversation.id)
                console.print("[green]대화가 시작되었습니다.[/green]")
        elif self.current_conversation.status == 'active':
            console.print("\n1. 일시정지")
            console.print("2. 중지")
            choice = Prompt.ask("선택", choices=["0", "1", "2"])
            if choice == "0":
                return  # 뒤로가기
            if choice == "1":
                # 일시정지 기능은 현재 구현되지 않음
                console.print("[yellow]일시정지 기능은 현재 지원되지 않습니다.[/yellow]")
            elif choice == "2":
                await self.conversation_service.end_conversation(self.current_conversation.id)
                console.print("[red]대화가 중지되었습니다.[/red]")
        elif self.current_conversation.status == 'paused':
            if Confirm.ask("대화를 재개하시겠습니까?"):
                # 재개 기능은 현재 구현되지 않음
                console.print("[yellow]재개 기능은 현재 지원되지 않습니다.[/yellow]")
        Prompt.ask("\n계속하려면 Enter를 누르세요")
    
    async def monitor_conversation(self):
        """실시간 모니터링"""
        if not self.current_conversation:
            console.print("[yellow]먼저 대화를 선택하세요.[/yellow]")
            Prompt.ask("\n계속하려면 Enter를 누르세요")
            return
        if self.current_conversation.status != 'active':
            console.print("[yellow]대화가 활성 상태가 아닙니다.[/yellow]")
            Prompt.ask("\n계속하려면 Enter를 누르세요")
            return
        
        console.clear()
        console.print(Panel.fit("[bold]실시간 모니터링[/bold]", border_style="green"))
        console.print("[yellow]AI 에이전트들이 자동으로 대화를 진행합니다. Ctrl+C로 종료 가능합니다.[/yellow]\n")
        
        try:
            # 실시간 모니터링 루프
            last_message_count = len(self.current_conversation.messages)
            
            while self.current_conversation.status == 'active':
                await asyncio.sleep(1)
                # 대화 상태 새로고침
                self.current_conversation = self.conversation_service.get_conversation(self.current_conversation.id)
                
                # 새 메시지 확인 및 표시
                current_message_count = len(self.current_conversation.messages)
                if current_message_count > last_message_count:
                    # 새 메시지들 표시
                    for i in range(last_message_count, current_message_count):
                        message = self.current_conversation.messages[i]
                        if message.speaker != "시스템":  # 시스템 메시지는 건너뛰기
                            agent_name = message.speaker
                            timestamp = message.timestamp.strftime("%H:%M:%S")
                            
                            # 메시지 내용에서 발화자 정보 중복 제거
                            content = message.content
                            patterns_to_remove = [
                                f"[{agent_name}]",
                                f"[{agent_name}] ",
                                f"[{agent_name}]:",
                                f"[{agent_name}]: ",
                                f"{agent_name}:",
                                f"{agent_name}: ",
                                f"{agent_name}",
                                f"{agent_name} ",
                                f"[{agent_name}님]",
                                f"[{agent_name}님] ",
                                f"[{agent_name}님]:",
                                f"[{agent_name}님]: ",
                                f"{agent_name}님:",
                                f"{agent_name}님: ",
                                f"{agent_name}님",
                                f"{agent_name}님 ",
                                f"님",
                                f"님 ",
                                f"님:",
                                f"님: "
                            ]
                            
                            for pattern in patterns_to_remove:
                                if content.startswith(pattern):
                                    content = content[len(pattern):].strip()
                                    break
                            
                            # 추가 정리: 줄 시작 부분의 불필요한 문자들 제거
                            content = content.lstrip(": ").lstrip("- ").lstrip("* ")
                            
                            console.print(f"[{timestamp}] {agent_name}: {content}\n")
                    
                    last_message_count = current_message_count
                
                # 대화가 종료되었는지 확인
                if self.current_conversation.status == 'ended':
                    console.print("\n[green]🏁 대화가 종료되었습니다.[/green]")
                    break
                    
        except KeyboardInterrupt:
            console.print("\n[yellow]모니터링이 종료되었습니다.[/yellow]")
        
        # 메인 메뉴로 자동 복귀
        return
    
    async def show_agents(self):
        """에이전트 정보 보기"""
        console.clear()
        agent_table = Table(title="에이전트 정보")
        agent_table.add_column("ID", style="cyan")
        agent_table.add_column("이름", style="green")
        agent_table.add_column("설명", style="white")
        for agent in self.agents:
            agent_table.add_row(agent.id, agent.name, agent.description)
        console.print(agent_table)
        Prompt.ask("\n계속하려면 Enter를 누르세요 (뒤로가려면 0 또는 b 입력)")

    async def _test_llm_connection(self):
        """LLM 연결 테스트"""
        console.clear()
        console.print(Panel.fit("[bold]LLM 연결 테스트[/bold]", border_style="blue"))
        
        try:
            # LLM 서비스 정보 표시
            provider_info = self.conversation_service.llm_service.get_provider_info()
            console.print(f"[bold]현재 LLM 제공자:[/bold] {provider_info['provider']}")
            
            # 설정 정보 표시
            config = provider_info['config']
            console.print(f"[bold]설정 정보:[/bold]")
            for key, value in config.items():
                if key == 'api_key' and value:
                    console.print(f"  {key}: {'*' * 10} (설정됨)")
                else:
                    console.print(f"  {key}: {value}")
            
            console.print("\n[bold]연결 테스트 중...[/bold]")
            
            # 연결 테스트 실행
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("LLM 서버에 연결 중...", total=None)
                result = await self.conversation_service.llm_service.test_connection()
                progress.update(task, completed=True)
            
            # 결과 표시
            if result["success"]:
                console.print(f"\n[green]✅ LLM 연결 성공![/green]")
                console.print(f"[bold]응답:[/bold] {result['details']['response']}")
                
                if 'usage' in result['details']:
                    usage = result['details']['usage']
                    console.print(f"[bold]토큰 사용량:[/bold]")
                    console.print(f"  프롬프트: {usage['prompt_tokens']}")
                    console.print(f"  완성: {usage['completion_tokens']}")
                    console.print(f"  총합: {usage['total_tokens']}")
            else:
                console.print(f"\n[red]❌ LLM 연결 실패![/red]")
                console.print(f"[bold]오류:[/bold] {result['error']}")
                
                # 문제 해결 제안
                console.print(f"\n[yellow]문제 해결 방법:[/yellow]")
                if result["provider"] == "vllm":
                    console.print("  1. vLLM 서버가 실행 중인지 확인")
                    console.print("  2. VLLM_URL이 올바른지 확인")
                    console.print("  3. 네트워크 연결 상태 확인")
                elif result["provider"] == "openai":
                    console.print("  1. OPENAI_API_KEY가 설정되었는지 확인")
                    console.print("  2. API 키가 유효한지 확인")
                    console.print("  3. OpenAI 서비스 상태 확인")
                elif result["provider"] == "ollama":
                    console.print("  1. Ollama가 실행 중인지 확인")
                    console.print("  2. OLLAMA_URL이 올바른지 확인")
                    console.print("  3. 모델이 다운로드되었는지 확인")
                
        except Exception as e:
            console.print(f"[red]❌ LLM 연결 테스트 오류: {str(e)}[/red]")
        
        Prompt.ask("\n계속하려면 Enter를 누르세요")


async def main():
    """메인 함수"""
    viewer = CLIConversationViewer()
    await viewer.show_main_menu()

if __name__ == "__main__":
    asyncio.run(main()) 