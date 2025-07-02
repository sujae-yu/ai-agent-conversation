'use client'

import { useState, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Moon, Sun, Play, Square, Plus, Settings, TestTube, Users, MessageSquare, Activity, ChevronDown, Database, Heart, Zap, X } from 'lucide-react'

interface Agent {
  id: string
  name: string
  personality: string
  description: string
}

interface Message {
  agent_id: string
  content: string
  timestamp: number
  turn_number: number
  agent_name: string
  is_streaming?: boolean
}

interface Conversation {
  id: string
  title: string
  status: string
  agent_ids: string[]
  current_turn: number
  max_turns: number
  messages: Message[]
}



export default function Home() {
  const [isDark, setIsDark] = useState(false)
  const [agents, setAgents] = useState<Agent[]>([])
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [ws, setWs] = useState<WebSocket | null>(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)


  const [selectedAgents, setSelectedAgents] = useState<string[]>([])
  const [maxTurns, setMaxTurns] = useState<number>(10)
  const [isUnlimited, setIsUnlimited] = useState<boolean>(false)
  const [topic, setTopic] = useState<string>('')
  const [isCreatingConversation, setIsCreatingConversation] = useState(false)
  const [activeTab, setActiveTab] = useState<'conversations' | 'create'>('conversations')
  
  // 시스템 기능 상태
  const [systemResults, setSystemResults] = useState<{
    agents?: any
    conversations?: any
    health?: any
    llmTest?: any
    config?: any
  }>({})
  const [isLoadingSystem, setIsLoadingSystem] = useState<string | null>(null)

  // 다크모드 토글
  const toggleDarkMode = () => {
    setIsDark(!isDark)
    document.documentElement.classList.toggle('dark')
  }

  // 자동 스크롤 함수
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  // 스크롤 이벤트 핸들러
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const element = e.currentTarget
    const isAtBottom = element.scrollHeight - element.scrollTop <= element.clientHeight + 100
    setAutoScroll(isAtBottom)
  }

  // 새 메시지가 추가될 때 자동 스크롤
  useEffect(() => {
    if (autoScroll) {
      scrollToBottom()
    }
  }, [currentConversation?.messages, autoScroll])

  // WebSocket 연결
  useEffect(() => {
    const websocket = new WebSocket('ws://localhost:8000/api/ws')
    
    websocket.onopen = () => {
      setIsConnected(true)
      console.log('WebSocket 연결됨')
    }
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data)
      console.log('WebSocket 메시지 수신:', data)
      
      if (data.type === 'new_message') {
        // 삭제된 대화의 메시지는 무시
        setConversations(prev => {
          const conversationExists = prev.some(conv => conv.id === data.conversation_id)
          if (!conversationExists) return prev
          
          return prev.map(conv => 
            conv.id === data.conversation_id 
              ? { ...conv, current_turn: data.message.turn_number }
              : conv
          )
        })
        
        // 새 메시지 추가 - 현재 대화 업데이트 (삭제된 대화가 아닌 경우만)
        setCurrentConversation(prev => {
          if (!prev || prev.id !== data.conversation_id) return prev
          
          // 대화 목록에서 해당 대화가 존재하는지 확인
          const conversationExists = conversations.some(conv => conv.id === data.conversation_id)
          if (!conversationExists) return null
          
          return {
            ...prev,
            messages: [...prev.messages, data.message],
            current_turn: data.message.turn_number
          }
        })
      } else if (data.type === 'stream_update') {
        // 스트림 업데이트 - 현재 대화의 마지막 메시지 업데이트 (삭제된 대화가 아닌 경우만)
        setCurrentConversation(prev => {
          if (!prev || prev.id !== data.conversation_id) return prev
          
          // 대화 목록에서 해당 대화가 존재하는지 확인
          const conversationExists = conversations.some(conv => conv.id === data.conversation_id)
          if (!conversationExists) return null
          
          const updatedMessages = [...prev.messages]
          const lastMessageIndex = updatedMessages.length - 1
          
          if (lastMessageIndex >= 0) {
            // 마지막 메시지가 같은 에이전트의 것인지 확인
            const lastMessage = updatedMessages[lastMessageIndex]
            if (lastMessage.agent_id === data.message.agent_id && 
                lastMessage.turn_number === data.message.turn_number) {
              // 기존 메시지 업데이트
              updatedMessages[lastMessageIndex] = {
                ...lastMessage,
                content: data.message.content,
                is_streaming: data.message.is_streaming
              }
            } else {
              // 새로운 스트림 메시지 추가
              updatedMessages.push({
                ...data.message,
                is_streaming: true
              })
            }
          } else {
            // 첫 번째 메시지
            updatedMessages.push({
              ...data.message,
              is_streaming: true
            })
          }
          
          return {
            ...prev,
            messages: updatedMessages,
            current_turn: data.message.turn_number
          }
        })
      } else if (data.type === 'conversation_updated') {
        // 대화 상태 변경 시 목록 새로고침
        fetch('/api/conversations')
          .then(res => res.json())
          .then(data => setConversations(data))
          .catch(err => console.error('대화 목록 업데이트 오류:', err))
      }
    }
    
    websocket.onclose = () => {
      setIsConnected(false)
      console.log('WebSocket 연결 끊어짐')
    }
    
    setWs(websocket)
    
    return () => {
      websocket.close()
    }
  }, [currentConversation?.id])

  // 현재 대화 폴링 (WebSocket이 작동하지 않을 경우를 대비)
  useEffect(() => {
    if (!currentConversation || currentConversation.status !== 'active') return
    
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/conversations/${currentConversation.id}`)
        if (response.ok) {
          const updatedConversation = await response.json()
          setCurrentConversation(updatedConversation)
          
          // 대화 목록도 업데이트
          setConversations(prev => 
            prev.map(conv => 
              conv.id === currentConversation.id 
                ? { ...conv, current_turn: updatedConversation.current_turn, status: updatedConversation.status }
                : conv
            )
          )
        }
      } catch (err) {
        console.error('대화 폴링 오류:', err)
      }
    }, 2000) // 2초마다 폴링
    
    return () => clearInterval(pollInterval)
  }, [currentConversation?.id, currentConversation?.status])

  // 에이전트 목록 가져오기
  useEffect(() => {
    fetch('/api/agents')
      .then(res => res.json())
      .then(data => setAgents(data))
      .catch(err => console.error('에이전트 로드 오류:', err))
  }, [])

  // 대화 목록 가져오기
  useEffect(() => {
    fetch('/api/conversations')
      .then(res => res.json())
      .then(data => setConversations(data))
      .catch(err => console.error('대화 목록 로드 오류:', err))
  }, [])

  // 대화 목록 폴링 (활성 대화가 있을 때만)
  useEffect(() => {
    const activeConversations = conversations.filter(conv => conv.status === 'active')
    if (activeConversations.length === 0) return
    
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch('/api/conversations')
        if (response.ok) {
          const updatedConversations = await response.json()
          setConversations(updatedConversations)
        }
      } catch (err) {
        console.error('대화 목록 폴링 오류:', err)
      }
    }, 3000) // 3초마다 폴링
    
    return () => clearInterval(pollInterval)
  }, [conversations])

  // 시스템 기능 함수들
  const testLlmConnection = async () => {
    try {
      setIsLoadingSystem('llm')
      const response = await fetch('/api/llm/test')
      const result = await response.json()
      
      setSystemResults({
        llmTest: result
      })
    } catch (error) {
      setSystemResults({
        llmTest: { error: `연결 오류: ${error}` }
      })
    } finally {
      setIsLoadingSystem(null)
    }
  }

  const getAgents = async () => {
    try {
      setIsLoadingSystem('agents')
      const response = await fetch('/api/agents')
      const result = await response.json()
      
      setSystemResults({
        agents: result
      })
    } catch (error) {
      setSystemResults({
        agents: { error: `조회 오류: ${error}` }
      })
    } finally {
      setIsLoadingSystem(null)
    }
  }

  const getConversations = async () => {
    try {
      setIsLoadingSystem('conversations')
      const response = await fetch('/api/conversations')
      const result = await response.json()
      // 현재 선택된 대화가 목록에 없으면 초기화
      if (currentConversation && !result.some((conv: any) => conv.id === currentConversation.id)) {
        setCurrentConversation(null)
      }
      setSystemResults({
        conversations: result
      })
      setConversations(result)
    } catch (error) {
      setSystemResults({
        conversations: { error: `조회 오류: ${error}` }
      })
    } finally {
      setIsLoadingSystem(null)
    }
  }

  const checkHealth = async () => {
    try {
      setIsLoadingSystem('health')
      const response = await fetch('/api/health')
      const result = await response.json()
      
      setSystemResults(prev => ({ ...prev, health: result }))
    } catch (error) {
      setSystemResults(prev => ({ ...prev, health: { error: `헬스 체크 오류: ${error}` } }))
    } finally {
      setIsLoadingSystem(null)
    }
  }

  const getConfig = async () => {
    try {
      setIsLoadingSystem('config')
      const response = await fetch('/api/config')
      const result = await response.json()
      
      setSystemResults(prev => ({ ...prev, config: result }))
    } catch (error) {
      setSystemResults(prev => ({ ...prev, config: { error: `설정 조회 오류: ${error}` } }))
    } finally {
      setIsLoadingSystem(null)
    }
  }

  // 새 대화 생성
  const createConversation = async () => {
    if (selectedAgents.length === 0) {
      alert('최소 하나의 에이전트를 선택해주세요.')
      return
    }

    setIsCreatingConversation(true)
    const request = {
      title: `새로운 AI 대화 - ${topic}`,
      agent_ids: selectedAgents,
      max_turns: isUnlimited ? 0 : maxTurns,
      topic: topic
    }

    try {
      const response = await fetch('/api/conversations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      })
      
      if (response.ok) {
        const result = await response.json()
        console.log('대화 생성됨:', result)
        
        // 대화 목록 새로고침
        const conversationsResponse = await fetch('/api/conversations')
        const conversationsData = await conversationsResponse.json()
        setConversations(conversationsData)
        
        // 생성된 대화 선택 및 자동 시작
        const newConversation = conversationsData.find((conv: Conversation) => conv.id === result.conversation_id)
        if (newConversation) {
          setCurrentConversation(newConversation)
          setActiveTab('conversations')
          // 새 대화 선택 시 자동 스크롤 활성화
          setAutoScroll(true)
          
          // 대화 자동 시작
          setTimeout(async () => {
            try {
              const startResponse = await fetch(`/api/conversations/${result.conversation_id}/start`, {
                method: 'POST'
              })
              
              if (startResponse.ok) {
                console.log('대화 자동 시작됨')
                // 대화 목록 새로고침
                const conversationsResponse = await fetch('/api/conversations')
                const conversationsData = await conversationsResponse.json()
                setConversations(conversationsData)
              } else {
                console.error('대화 자동 시작 실패')
              }
            } catch (err) {
              console.error('대화 자동 시작 오류:', err)
            }
          }, 500) // 0.5초 후 자동 시작
        }
        
        alert('대화가 성공적으로 생성되고 자동으로 시작됩니다!')
      } else {
        const errorData = await response.json()
        alert(`대화 생성 실패: ${errorData.detail}`)
      }
    } catch (err) {
      console.error('대화 생성 오류:', err)
      alert('대화 생성 중 오류가 발생했습니다.')
    } finally {
      setIsCreatingConversation(false)
    }
  }

  // 대화 시작
  const startConversation = async (conversationId: string) => {
    try {
      const response = await fetch(`/api/conversations/${conversationId}/start`, {
        method: 'POST'
      })
      
      if (response.ok) {
        console.log('대화 시작됨')
        // 대화 목록 새로고침
        const conversationsResponse = await fetch('/api/conversations')
        const conversationsData = await conversationsResponse.json()
        setConversations(conversationsData)
      } else {
        const errorData = await response.json()
        alert(`대화 시작 실패: ${errorData.detail}`)
      }
    } catch (err) {
      console.error('대화 시작 오류:', err)
      alert('대화 시작 중 오류가 발생했습니다.')
    }
  }



  // 대화 중지
  const stopConversation = async (conversationId: string) => {
    try {
      const response = await fetch(`/api/conversations/${conversationId}/stop`, {
        method: 'POST'
      })
      
      if (response.ok) {
        console.log('대화 중지됨')
        // 대화 목록 새로고침
        const conversationsResponse = await fetch('/api/conversations')
        const conversationsData = await conversationsResponse.json()
        setConversations(conversationsData)
      } else {
        const errorData = await response.json()
        alert(`대화 중지 실패: ${errorData.detail}`)
      }
    } catch (err) {
      console.error('대화 중지 오류:', err)
      alert('대화 중지 중 오류가 발생했습니다.')
    }
  }

  // 대화 선택
  const selectConversation = async (conversationId: string) => {
    try {
      const response = await fetch(`/api/conversations/${conversationId}`)
      if (response.ok) {
        const conversation = await response.json()
        setCurrentConversation(conversation)
        // 대화 선택 시 자동 스크롤 활성화
        setAutoScroll(true)
      } else {
        alert('대화 로드에 실패했습니다.')
      }
    } catch (err) {
      console.error('대화 로드 오류:', err)
      alert('대화 로드 중 오류가 발생했습니다.')
    }
  }

  // 대화 삭제
  const deleteConversation = async (conversationId: string) => {
    try {
      console.log('대화 삭제 시작:', conversationId)
      
      const response = await fetch(`/api/conversations/${conversationId}`, {
        method: 'DELETE'
      })
      
      console.log('삭제 응답 상태:', response.status)
      
      if (response.ok) {
        console.log('삭제 성공, 응답:', await response.json())
        
        // 현재 선택된 대화가 삭제된 대화라면 선택 해제 및 초기화
        if (currentConversation?.id === conversationId) {
          setCurrentConversation(null)
          setAutoScroll(true)
        }
        // 즉시 로컬 상태에서 제거 (즉시 UI 업데이트)
        setConversations(prev => prev.filter(conv => conv.id !== conversationId))
        // 백그라운드에서 대화 목록 새로고침 (서버 동기화)
        setTimeout(async () => {
          try {
            console.log('대화 목록 새로고침 시작')
            const conversationsResponse = await fetch('/api/conversations')
            if (conversationsResponse.ok) {
              const updatedConversations = await conversationsResponse.json()
              // 삭제된 대화가 현재 선택된 대화라면 초기화
              if (currentConversation && !updatedConversations.some(conv => conv.id === currentConversation.id)) {
                setCurrentConversation(null)
              }
              setConversations(updatedConversations)
            } else {
              console.error('대화 목록 새로고침 실패:', conversationsResponse.statusText)
            }
          } catch (error) {
            console.error('대화 목록 새로고침 오류:', error)
          }
        }, 100)
        
        console.log('대화가 성공적으로 삭제되었습니다.')
      } else {
        const errorText = await response.text()
        console.error('대화 삭제 실패:', response.status, errorText)
      }
    } catch (error) {
      console.error('대화 삭제 오류:', error)
    }
  }

  // 에이전트 선택 토글
  const toggleAgentSelection = (agentId: string) => {
    setSelectedAgents(prev => 
      prev.includes(agentId) 
        ? prev.filter(id => id !== agentId)
        : [...prev, agentId]
    )
  }

  // 시스템 결과가 있는지 확인
  const hasSystemResults = () => {
    return !!(systemResults.agents || systemResults.conversations || systemResults.health || systemResults.llmTest || systemResults.config)
  }

  return (
    <div className={`min-h-screen ${isDark ? 'dark' : ''}`}>
      <div className="flex flex-col lg:flex-row h-screen bg-gray-50 dark:bg-gray-900">
        {/* 사이드바 */}
        <div className="w-full lg:w-80 bg-white dark:bg-gray-800 border-b lg:border-r border-gray-200 dark:border-gray-700">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                AI Agent NPC
              </h1>
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleDarkMode}
                className="text-gray-500 dark:text-gray-400"
              >
                {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
              </Button>
            </div>
          </div>

          {/* 탭 네비게이션 */}
          <div className="p-2 lg:p-4 border-b border-gray-200 dark:border-gray-700">
            <div className="grid grid-cols-2 lg:flex lg:space-x-1 gap-1">
              <Button
                variant={activeTab === 'conversations' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setActiveTab('conversations')}
                className="flex-1 text-xs lg:text-sm"
              >
                <MessageSquare className="h-3 w-3 lg:h-4 lg:w-4 mr-1" />
                <span className="hidden sm:inline">대화</span>
                <span className="sm:hidden">대화</span>
              </Button>
              <Button
                variant={activeTab === 'create' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setActiveTab('create')}
                className="flex-1 text-xs lg:text-sm"
              >
                <Plus className="h-3 w-3 lg:h-4 lg:w-4 mr-1" />
                <span className="hidden sm:inline">생성</span>
                <span className="sm:hidden">생성</span>
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="flex-1 text-xs lg:text-sm"
                  >
                    <Activity className="h-3 w-3 lg:h-4 lg:w-4 mr-1" />
                    <span className="hidden sm:inline">시스템</span>
                    <span className="sm:hidden">시스템</span>
                    <ChevronDown className="h-3 w-3 lg:h-4 lg:w-4 ml-1" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  <DropdownMenuLabel>시스템 기능</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={getAgents} disabled={isLoadingSystem === 'agents'}>
                    <Users className="h-4 w-4 mr-2" />
                    {isLoadingSystem === 'agents' ? '로딩 중...' : '에이전트 조회'}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={getConversations} disabled={isLoadingSystem === 'conversations'}>
                    <Database className="h-4 w-4 mr-2" />
                    {isLoadingSystem === 'conversations' ? '로딩 중...' : '대화 목록 조회'}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={checkHealth} disabled={isLoadingSystem === 'health'}>
                    <Heart className="h-4 w-4 mr-2" />
                    {isLoadingSystem === 'health' ? '로딩 중...' : '헬스 체크'}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={getConfig} disabled={isLoadingSystem === 'config'}>
                    <Settings className="h-4 w-4 mr-2" />
                    {isLoadingSystem === 'config' ? '로딩 중...' : '설정 조회'}
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={testLlmConnection} disabled={isLoadingSystem === 'llm'}>
                    <TestTube className="h-4 w-4 mr-2" />
                    {isLoadingSystem === 'llm' ? '테스트 중...' : 'LLM 연결 테스트'}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          {/* 탭 콘텐츠 */}
          <div className="p-2 lg:p-4 overflow-y-auto max-h-96 lg:max-h-none">
            {!hasSystemResults() && activeTab === 'conversations' && (
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  대화 목록
                </h2>
                {conversations.length > 0 ? (
                  <div className="space-y-2">
                    {conversations.map((conversation) => (
                      <div
                        key={conversation.id}
                        className={`p-2 lg:p-3 rounded-lg border cursor-pointer transition-colors ${
                          currentConversation?.id === conversation.id
                            ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-700'
                            : 'bg-white dark:bg-gray-700 border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600'
                        }`}
                        onClick={() => selectConversation(conversation.id)}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex-1 min-w-0">
                            <h3 className="text-xs lg:text-sm font-medium text-gray-900 dark:text-white truncate">
                              {conversation.title}
                            </h3>
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                              {conversation.current_turn}/{conversation.max_turns === 0 ? '∞' : conversation.max_turns} 턴
                            </p>
                          </div>
                          <div className="flex items-center space-x-1">
                            {conversation.status === 'idle' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  startConversation(conversation.id)
                                }}
                                className="h-5 w-5 lg:h-6 lg:w-6 p-0 text-green-600"
                              >
                                <Play className="h-3 w-3" />
                              </Button>
                            )}
                            {conversation.status === 'active' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  stopConversation(conversation.id)
                                }}
                                className="h-5 w-5 lg:h-6 lg:w-6 p-0 text-red-600"
                              >
                                <Square className="h-3 w-3" />
                              </Button>
                            )}
                            {/* 삭제 버튼 임시 숨김 */}
                            {/* {(conversation.status === 'stopped' || conversation.status === 'idle') && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  if (confirm('정말로 이 대화를 삭제하시겠습니까?')) {
                                    deleteConversation(conversation.id)
                                  }
                                }}
                                className="h-5 w-5 lg:h-6 lg:w-6 p-0 text-gray-500 hover:text-red-600"
                              >
                                <X className="h-3 w-3" />
                              </Button>
                            )} */}
                          </div>
                        </div>
                        <div className="mt-1 lg:mt-2">
                          <span className={`inline-flex items-center px-1 lg:px-2 py-1 rounded-full text-xs font-medium ${
                            conversation.status === 'active' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
                            conversation.status === 'stopped' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' :
                            'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                          }`}>
                            {conversation.status}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                    <MessageSquare className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p className="text-sm">대화가 없습니다</p>
                    <p className="text-xs mt-1">새 대화를 생성해보세요</p>
                  </div>
                )}
              </div>
            )}

            {!hasSystemResults() && activeTab === 'create' && (
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  새 대화 생성
                </h2>
                
                <div className="space-y-3 lg:space-y-4">
                  <div>
                    <label className="block text-xs lg:text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 lg:mb-2">
                      대화 주제
                    </label>
                    <input
                      type="text"
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      className="w-full px-2 lg:px-3 py-1 lg:py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-xs lg:text-sm"
                      placeholder="대화 주제를 입력하세요"
                    />
                  </div>

                  <div>
                    <div className="flex items-center mb-1 lg:mb-2">
                      <input
                        type="checkbox"
                        id="unlimited"
                        checked={isUnlimited}
                        onChange={(e) => setIsUnlimited(e.target.checked)}
                        className="mr-2 rounded border-gray-300 dark:border-gray-600"
                      />
                      <label htmlFor="unlimited" className="text-xs lg:text-sm font-medium text-gray-700 dark:text-gray-300">
                        무제한 대화
                      </label>
                    </div>
                    <div>
                      <label className="block text-xs lg:text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 lg:mb-2">
                        최대 턴 수 (10-50)
                      </label>
                      <input
                        type="number"
                        value={maxTurns}
                        onChange={(e) => setMaxTurns(parseInt(e.target.value) || 10)}
                        disabled={isUnlimited}
                        className={`w-full px-2 lg:px-3 py-1 lg:py-2 border rounded-md text-xs lg:text-sm ${
                          isUnlimited 
                            ? 'border-gray-200 dark:border-gray-600 bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 cursor-not-allowed'
                            : 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white'
                        }`}
                        min="10"
                        max="50"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs lg:text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 lg:mb-2">
                      참여 에이전트 선택 ({selectedAgents.length}개 선택됨)
                    </label>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-2 lg:gap-3 max-h-48 lg:max-h-64 overflow-y-auto">
                      {agents.map((agent) => (
                        <div
                          key={agent.id}
                          className={`p-3 rounded-lg border cursor-pointer transition-all ${
                            selectedAgents.includes(agent.id)
                              ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-700'
                              : 'bg-white dark:bg-gray-700 border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600'
                          }`}
                          onClick={() => toggleAgentSelection(agent.id)}
                        >
                          <div className="flex items-start space-x-3">
                            <input
                              type="checkbox"
                              checked={selectedAgents.includes(agent.id)}
                              onChange={() => toggleAgentSelection(agent.id)}
                              className="mt-1 rounded border-gray-300 dark:border-gray-600"
                            />
                            <div className="flex-1 min-w-0">
                              <h4 className="text-sm font-medium text-gray-900 dark:text-white truncate">
                                {agent.name}
                              </h4>
                              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                                {agent.personality}
                              </p>
                              <p className="text-xs text-gray-600 dark:text-gray-300 line-clamp-2">
                                {agent.description}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <Button
                    onClick={createConversation}
                    disabled={isCreatingConversation || selectedAgents.length === 0}
                    className="w-full text-xs lg:text-sm py-2 lg:py-3"
                  >
                    {isCreatingConversation ? '생성 중...' : '대화 생성'}
                  </Button>
                </div>
              </div>
            )}

            {/* 시스템 결과 표시 영역 */}
            {hasSystemResults() && (
              <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                    시스템 결과
                  </h3>
                  <button
                    onClick={() => setSystemResults({})}
                    className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                  >
                    결과 지우기
                  </button>
                </div>
                <div className="space-y-3 text-xs">
                  {systemResults.agents && (
                    <div>
                      <h4 className="font-medium text-gray-700 dark:text-gray-300 mb-1 flex items-center">
                        <Users className="h-3 w-3 mr-1" />
                        에이전트 조회 결과
                      </h4>
                      <div className="p-2 bg-white dark:bg-gray-800 rounded border max-h-32 overflow-y-auto">
                        <pre className="whitespace-pre-wrap text-gray-900 dark:text-white">
                          {systemResults.agents.error ? 
                            `❌ ${systemResults.agents.error}` : 
                            `✅ ${systemResults.agents.length}개 에이전트 조회됨\n${JSON.stringify(systemResults.agents, null, 2)}`
                          }
                        </pre>
                      </div>
                    </div>
                  )}
                  
                  {systemResults.conversations && (
                    <div>
                      <h4 className="font-medium text-gray-700 dark:text-gray-300 mb-1 flex items-center">
                        <Database className="h-3 w-3 mr-1" />
                        대화 목록 조회 결과
                      </h4>
                      <div className="p-2 bg-white dark:bg-gray-800 rounded border max-h-32 overflow-y-auto">
                        <pre className="whitespace-pre-wrap text-gray-900 dark:text-white">
                          {systemResults.conversations.error ? 
                            `❌ ${systemResults.conversations.error}` : 
                            `✅ ${systemResults.conversations.length}개 대화 조회됨\n${JSON.stringify(systemResults.conversations, null, 2)}`
                          }
                        </pre>
                      </div>
                    </div>
                  )}
                  
                  {systemResults.health && (
                    <div>
                      <h4 className="font-medium text-gray-700 dark:text-gray-300 mb-1 flex items-center">
                        <Heart className="h-3 w-3 mr-1" />
                        헬스 체크 결과
                      </h4>
                      <div className="p-2 bg-white dark:bg-gray-800 rounded border max-h-32 overflow-y-auto">
                        <pre className="whitespace-pre-wrap text-gray-900 dark:text-white">
                          {systemResults.health.error ? 
                            `❌ ${systemResults.health.error}` : 
                            `✅ 서버 정상\n${JSON.stringify(systemResults.health, null, 2)}`
                          }
                        </pre>
                      </div>
                    </div>
                  )}
                  
                  {systemResults.llmTest && (
                    <div>
                      <h4 className="font-medium text-gray-700 dark:text-gray-300 mb-1 flex items-center">
                        <TestTube className="h-3 w-3 mr-1" />
                        LLM 연결 테스트 결과
                      </h4>
                      <div className="p-2 bg-white dark:bg-gray-800 rounded border max-h-32 overflow-y-auto">
                        <pre className="whitespace-pre-wrap text-gray-900 dark:text-white">
                          {systemResults.llmTest.error ? 
                            `❌ ${systemResults.llmTest.error}` : 
                            `✅ LLM 연결 성공\n${JSON.stringify(systemResults.llmTest, null, 2)}`
                          }
                        </pre>
                      </div>
                    </div>
                  )}
                  
                  {systemResults.config && (
                    <div>
                      <h4 className="font-medium text-gray-700 dark:text-gray-300 mb-1 flex items-center">
                        <Settings className="h-3 w-3 mr-1" />
                        설정 정보
                      </h4>
                      <div className="p-2 bg-white dark:bg-gray-800 rounded border max-h-32 overflow-y-auto">
                        <pre className="whitespace-pre-wrap text-gray-900 dark:text-white">
                          {systemResults.config.error ? 
                            `❌ ${systemResults.config.error}` : 
                            `✅ 설정 조회 성공\n${JSON.stringify(systemResults.config, null, 2)}`
                          }
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 메인 콘텐츠 */}
        <div className="flex-1 flex flex-col min-h-0">
          {currentConversation ? (
            <>
              {/* 헤더 */}
              <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-3 lg:p-4">
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-2 lg:space-y-0">
                  <div>
                    <h2 className="text-base lg:text-lg font-semibold text-gray-900 dark:text-white truncate">
                      {currentConversation.title}
                    </h2>
                    <p className="text-xs lg:text-sm text-gray-500 dark:text-gray-400">
                      {currentConversation.current_turn}/{currentConversation.max_turns === 0 ? '∞' : currentConversation.max_turns} 턴
                    </p>
                  </div>
                  <div className="flex items-center justify-between lg:justify-end space-x-2">
                    <div className="flex items-center space-x-1">
                      <div className={`w-2 h-2 rounded-full ${
                        isConnected ? 'bg-green-500' : 'bg-red-500'
                      }`} />
                      <span className="text-xs lg:text-sm text-gray-500 dark:text-gray-400">
                        {isConnected ? '연결됨' : '연결 끊어짐'}
                      </span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <div className={`w-2 h-2 rounded-full ${
                        autoScroll ? 'bg-blue-500' : 'bg-gray-400'
                      }`} />
                      <span className="text-xs text-gray-500 dark:text-gray-400 hidden sm:inline">
                        {autoScroll ? '자동스크롤' : '수동스크롤'}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400 sm:hidden">
                        {autoScroll ? '자동' : '수동'}
                      </span>
                      {!autoScroll && (
                        <button
                          onClick={() => {
                            setAutoScroll(true)
                            scrollToBottom()
                          }}
                          className="ml-1 lg:ml-2 px-1 lg:px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600"
                        >
                          <span className="hidden sm:inline">맨 아래로</span>
                          <span className="sm:hidden">↓</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* 메시지 영역 */}
              <div 
                className="flex-1 overflow-y-auto p-3 lg:p-4 space-y-3 lg:space-y-4"
                onScroll={handleScroll}
              >
                {(currentConversation.messages || []).map((message, index) => (
                  <div
                    key={index}
                    className="flex items-start space-x-2 lg:space-x-3 message-enter"
                  >
                    <div className="flex-shrink-0">
                      <div className="w-6 h-6 lg:w-8 lg:h-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-xs lg:text-sm font-medium">
                        {message.agent_name === 'Unknown' ? '시' : message.agent_name.charAt(0)}
                      </div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-col sm:flex-row sm:items-center sm:space-x-2 mb-1 space-y-1 sm:space-y-0">
                        <span className="text-xs lg:text-sm font-medium text-gray-900 dark:text-white">
                          {message.agent_name === 'Unknown' ? '시스템' : message.agent_name}
                        </span>
                        <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
                          <span>턴 {message.turn_number === 0 ? '시작' : message.turn_number}</span>
                          <span>{new Date(message.timestamp * 1000).toLocaleTimeString()}</span>
                        </div>
                      </div>
                      <div className={`bg-white dark:bg-gray-700 rounded-lg p-2 lg:p-3 border ${
                        message.is_streaming 
                          ? 'border-blue-300 dark:border-blue-600 bg-blue-50 dark:bg-blue-900/20' 
                          : 'border-gray-200 dark:border-gray-600'
                      }`}>
                        <div className="flex items-start justify-between">
                          <p className="text-xs lg:text-sm text-gray-900 dark:text-white whitespace-pre-wrap flex-1">
                            {message.content}
                            {message.is_streaming && (
                              <span className="inline-block ml-1 animate-pulse">▋</span>
                            )}
                          </p>
                          {message.is_streaming && (
                            <div className="flex items-center ml-2 text-blue-500">
                              <div className="flex space-x-1">
                                <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                                <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                                <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center p-4">
              <div className="text-center">
                <h3 className="text-base lg:text-lg font-medium text-gray-900 dark:text-white mb-2">
                  대화를 선택하세요
                </h3>
                <p className="text-xs lg:text-sm text-gray-500 dark:text-gray-400">
                  왼쪽에서 대화를 선택하거나 새 대화를 생성하세요.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
} 