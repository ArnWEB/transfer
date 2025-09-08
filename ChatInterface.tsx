import React, { useState, useEffect, useRef } from 'react';
import { Send, Shield, Lock, User, Bot, Terminal, AlertTriangle, Eye, Zap, ThumbsUp, ThumbsDown, LogOut, Search, BookOpen, History, X, ChevronRight, Brain, Lightbulb, FileText } from 'lucide-react';
import DialogBox from './DialogBox';
import { DialogConfig } from '../types/auth';

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  feedback?: 'like' | 'dislike' | null;
  dialogConfig?: DialogConfig;
}

interface ResearchMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  topic?: string;
  sources?: string[];
}

interface Session {
  id: string;
  openingMessage: string;
}

interface User {
  id: number;
  email: string;
  created_at: Date;
  updated_at: Date;
}

interface ChatInterfaceProps {
  user: User;
  token: string;
  onLogout: () => void;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ user, token, onLogout }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [session, setSession] = useState<Session | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [isResearchMode, setIsResearchMode] = useState(false);
  const [researchMessages, setResearchMessages] = useState<ResearchMessage[]>([]);
  const [researchInput, setResearchInput] = useState('');
  const [isResearchLoading, setIsResearchLoading] = useState(false);
  const [activeResearchTopic, setActiveResearchTopic] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const researchMessagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const researchInputRef = useRef<HTMLInputElement>(null);
  const [showDialog,setShowDialog]=useState(false)
  const [currentDialogConfig,setCurrentDialogConfig] =useState()

  // Scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const scrollResearchToBottom = () => {
    researchMessagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isThinking]);

  useEffect(() => {
    scrollResearchToBottom();
  }, [researchMessages]);

  // Initialize session on component mount
  useEffect(() => {
    initializeSession();
  }, []);

  const initializeSession = async () => {
    setIsInitializing(true);
    
    // Mock session initialization
    const mockSession = {
      id: 'demo-session-' + Date.now(),
      openingMessage: "🛡️ CyberGuard AI initialized. I'm your cybersecurity assistant. How can I help secure your digital environment today?\n\n💡 **Try typing 'show' to see a demo dialog box!**"
    };
    setSession(mockSession);
    
    const openingMessage: Message = {
      id: 'opening-' + Date.now(),
      content: mockSession.openingMessage,
      role: 'assistant',
      timestamp: new Date(),
    };
    
    setMessages([openingMessage]);
    setIsInitializing(false);
  };
  // Parse AI response for dialog trigger
  const parseAIResponse = (content: string): { cleanContent: string; dialogConfig?: DialogConfig } => {
    try {
      // Look for dialog configuration in the response
      const dialogMatch = content.match(/```dialog\s*\n([\s\S]*?)\n```/);
      if (dialogMatch) {
        const dialogConfigStr = dialogMatch[1];
        const dialogConfig = JSON.parse(dialogConfigStr);
        const cleanContent = content.replace(/```dialog\s*\n[\s\S]*?\n```/, '').trim();
        return { cleanContent, dialogConfig };
      }
      
      // Alternative: Look for dialog = True pattern
      if (content.includes('dialog = True') || content.includes('"dialog": true')) {
        // Create a default dialog configuration
        const defaultDialogConfig: DialogConfig = {
          title: 'Security Assessment Form',
          description: 'Please provide the following information for security analysis',
          fields: [
            {
              id: 'system_type',
              type: 'select',
              label: 'System Type',
              required: true,
              options: ['Web Application', 'Mobile App', 'Desktop Software', 'Network Infrastructure', 'Cloud Service']
            },
            {
              id: 'security_concern',
              type: 'textarea',
              label: 'Describe your security concern',
              placeholder: 'Please describe the specific security issue or vulnerability you need help with...',
              required: true
            },
            {
              id: 'urgency',
              type: 'radio',
              label: 'Urgency Level',
              required: true,
              options: ['Low - General inquiry', 'Medium - Potential issue', 'High - Active threat', 'Critical - Immediate response needed']
            },
            {
              id: 'contact_email',
              type: 'email',
              label: 'Contact Email',
              placeholder: 'your.email@company.com',
              required: false
            }
          ],
          submitText: 'Submit Security Assessment'
        };
        
        const cleanContent = content.replace(/dialog\s*=\s*True/gi, '').replace(/"dialog":\s*true/gi, '').trim();
        return { cleanContent, dialogConfig: defaultDialogConfig };
      }
    } catch (error) {
      console.error('Error parsing dialog configuration:', error);
    }
    
    return { cleanContent: content };
  };

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading || !session) return;

    const userMessage: Message = {
      id: 'user-' + Date.now(),
      content: inputValue.trim(),
      role: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    const currentInput = inputValue.trim();
    setInputValue('');
    setIsLoading(true);
    setIsThinking(true);

    // Mock AI response based on user input
    let mockResponse = "";
    
    if (currentInput.toLowerCase() === 'show') {
      mockResponse = "I'll demonstrate our interactive security assessment form. This dialog will help me understand your security environment better.\n\n```dialog\n{\n  \"title\": \"Security Assessment Form\",\n  \"description\": \"Please provide information about your security environment\",\n  \"fields\": [\n    {\n      \"id\": \"system_type\",\n      \"type\": \"select\",\n      \"label\": \"System Type\",\n      \"required\": true,\n      \"options\": [\"Web Application\", \"Mobile App\", \"Desktop Software\", \"Network Infrastructure\", \"Cloud Service\"]\n    },\n    {\n      \"id\": \"security_concern\",\n      \"type\": \"textarea\",\n      \"label\": \"Describe your security concern\",\n      \"placeholder\": \"Please describe the specific security issue or vulnerability you need help with...\",\n      \"required\": true\n    },\n    {\n      \"id\": \"urgency\",\n      \"type\": \"radio\",\n      \"label\": \"Urgency Level\",\n      \"required\": true,\n      \"options\": [\"Low - General inquiry\", \"Medium - Potential issue\", \"High - Active threat\", \"Critical - Immediate response needed\"]\n    },\n    {\n      \"id\": \"contact_email\",\n      \"type\": \"email\",\n      \"label\": \"Contact Email\",\n      \"placeholder\": \"your.email@company.com\",\n      \"required\": false\n    },\n    {\n      \"id\": \"has_backups\",\n      \"type\": \"checkbox\",\n      \"label\": \"I have regular data backups in place\",\n      \"required\": false\n    }\n  ],\n  \"submitText\": \"Submit Security Assessment\"\n}\n```";
    } else {
      // Default responses for other inputs
      const responses = [
        "🛡️ I've analyzed your security concern. Based on current threat intelligence, I recommend implementing multi-layered security protocols including network segmentation, endpoint protection, and continuous monitoring.",
        "🔍 Your query indicates potential vulnerabilities. I suggest conducting a comprehensive security audit, updating all systems, and implementing zero-trust architecture principles.",
        "⚠️ Security assessment complete. I've identified several areas for improvement: access control hardening, encryption upgrades, and incident response planning.",
        "🎯 Based on your input, I recommend: 1) Regular penetration testing, 2) Employee security training, 3) Multi-factor authentication deployment, 4) Security information and event management (SIEM) implementation.",
        "🔐 Threat analysis indicates medium risk level. Immediate actions: patch management, firewall configuration review, and backup verification. Would you like detailed implementation steps?"
      ];
      mockResponse = responses[Math.floor(Math.random() * responses.length)];
    }
    
    // Parse response for dialog configuration
    const { cleanContent, dialogConfig } = parseAIResponse(mockResponse);
    
    const assistantMessage: Message = {
      id: 'assistant-' + Date.now(),
      content: cleanContent,
      role: 'assistant',
      timestamp: new Date(),
      feedback: null,
      dialogConfig: dialogConfig,
    };

    // Simulate thinking delay
    setTimeout(() => {
      setIsThinking(false);
      setMessages(prev => [...prev, assistantMessage]);
      
      // Show dialog if configuration exists
      if (dialogConfig) {
        setCurrentDialogConfig(dialogConfig);
        setShowDialog(true);
      }
    }, 1500);
    
    setIsLoading(false);
  };

  const sendResearchMessage = async () => {
    if (!researchInput.trim() || isResearchLoading) return;

    const userMessage: ResearchMessage = {
      id: 'research-user-' + Date.now(),
      content: researchInput.trim(),
      role: 'user',
      timestamp: new Date(),
      topic: activeResearchTopic || 'General Research'
    };

    setResearchMessages(prev => [...prev, userMessage]);
    setResearchInput('');
    setIsResearchLoading(true);
    setActiveResearchTopic(userMessage.content.slice(0, 50) + '...');

    // Simulate research response
    setTimeout(() => {
      const researchResponse: ResearchMessage = {
        id: 'research-assistant-' + Date.now(),
        content: `Based on my research analysis of "${userMessage.content}", I've found several key insights:\n\n🔍 **Primary Findings:**\n• Advanced threat detection mechanisms are evolving rapidly\n• Zero-trust architecture is becoming the industry standard\n• AI-powered security solutions show 85% improvement in threat detection\n\n📊 **Statistical Analysis:**\n• 67% reduction in security incidents with proper implementation\n• ROI improvement of 340% within first year\n• 24/7 automated monitoring capabilities\n\n🎯 **Recommendations:**\n• Implement multi-layered security protocols\n• Regular security audits and penetration testing\n• Employee training on cybersecurity best practices\n\nWould you like me to dive deeper into any specific aspect of this research?`,
        role: 'assistant',
        timestamp: new Date(),
        topic: activeResearchTopic,
        sources: [
          'NIST Cybersecurity Framework 2.0',
          'SANS Institute Research Papers',
          'Gartner Security Reports 2024',
          'IEEE Security & Privacy Journal'
        ]
      };

      setResearchMessages(prev => [...prev, researchResponse]);
      setIsResearchLoading(false);
    }, 2000);
  };

  const handleResearchKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendResearchMessage();
    }
  };

  const toggleResearchMode = () => {
    setIsResearchMode(!isResearchMode);
    if (!isResearchMode && researchMessages.length === 0) {
      // Add welcome message for research
      const welcomeMessage: ResearchMessage = {
        id: 'research-welcome-' + Date.now(),
        content: "🔬 **Research Agent Activated**\n\nI'm your dedicated research assistant for cybersecurity topics. I can help you:\n\n• **Deep dive** into security frameworks and methodologies\n• **Analyze** threat landscapes and attack vectors\n• **Research** compliance requirements and standards\n• **Compare** security solutions and technologies\n• **Investigate** emerging threats and vulnerabilities\n\nWhat would you like to research today?",
        role: 'assistant',
        timestamp: new Date(),
        topic: 'Research Agent Introduction'
      };
      setResearchMessages([welcomeMessage]);
    }
  };
  const handleDialogSubmit = (formData: Record<string, any>) => {
    // Format the form data as a user message
    let messageContent = "Here's the information you requested:\n\n";
    
    Object.entries(formData).forEach(([key, value]) => {
      const field = currentDialogConfig?.fields.find(f => f.id === key);
      const label = field?.label || key;
      
      if (value !== '' && value !== false) {
        if (typeof value === 'boolean') {
          messageContent += `✓ ${label}: ${value ? 'Yes' : 'No'}\n`;
        } else {
          messageContent += `• **${label}**: ${value}\n`;
        }
      }
    });
    
    // Add the formatted response as a user message
    const userMessage: Message = {
      id: 'dialog-response-' + Date.now(),
      content: messageContent,
      role: 'user',
      timestamp: new Date(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    
    // Generate AI response to the form submission
    setTimeout(() => {
      const responseMessage: Message = {
        id: 'dialog-followup-' + Date.now(),
        content: "Thank you for providing that information! Based on your responses, I can now provide more targeted security recommendations. Let me analyze your specific situation and suggest appropriate countermeasures.",
        role: 'assistant',
        timestamp: new Date(),
        feedback: null,
      };
      
      setMessages(prev => [...prev, responseMessage]);
    }, 1000);
  };

  const handleDialogClose = () => {
    setShowDialog(false);
    setCurrentDialogConfig(null);
  };

  const handleFeedback = async (messageId: string, feedbackType: 'like' | 'dislike') => {
    const message = messages.find(m => m.id === messageId);
    if (!message || !session) return;

    // Update UI immediately
    setMessages(prev => prev.map(m => 
      m.id === messageId 
        ? { ...m, feedback: m.feedback === feedbackType ? null : feedbackType }
        : m
    ));

    // Mock feedback saving (no backend needed)
    console.log('Feedback saved:', { messageId, feedbackType, userId: user.id });
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const ThinkingAnimation = () => (
    <div className="flex items-center space-x-2 p-4 bg-gray-900/90 border border-cyan-500/30 rounded-2xl shadow-lg max-w-xs backdrop-blur-sm">
      <div className="flex items-center justify-center w-8 h-8 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-full animate-pulse">
        <Bot className="w-4 h-4 text-white" />
      </div>
      <div className="flex space-x-1">
        <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse"></div>
        <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
        <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
      </div>
      <span className="text-xs text-cyan-300 font-mono">Analyzing...</span>
    </div>
  );

  const ResearchThinkingAnimation = () => (
    <div className="flex items-center space-x-2 p-4 bg-purple-900/90 border border-purple-500/30 rounded-2xl shadow-lg max-w-xs backdrop-blur-sm">
      <div className="flex items-center justify-center w-8 h-8 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-full animate-pulse">
        <Brain className="w-4 h-4 text-white" />
      </div>
      <div className="flex space-x-1">
        <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse"></div>
        <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
        <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
      </div>
      <span className="text-xs text-purple-300 font-mono">Researching...</span>
    </div>
  );

  if (isInitializing) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-4 border-cyan-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-cyan-300 font-mono">Initializing CyberGuard AI...</p>
          <p className="text-gray-400 text-sm mt-2">Establishing secure connection...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black flex overflow-hidden relative">
      {/* Sidebar */}
      <div className={`hidden lg:flex ${isResearchMode ? 'lg:w-48' : 'lg:w-64'} bg-gradient-to-b from-black via-gray-900 to-gray-800 border-r border-cyan-500/20 p-6 flex-col transition-all duration-300`}>
        <div className="flex items-center space-x-3 mb-8">
          <div className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-cyan-500/25">
            <Shield className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-xl font-semibold text-white tracking-tight">CyberGuard AI</h1>
        </div>
        
        {/* Research Toggle */}
        <button
          onClick={toggleResearchMode}
          className={`w-full mb-6 p-3 rounded-xl border transition-all duration-200 ${
            isResearchMode
              ? 'bg-gradient-to-r from-purple-500/20 to-indigo-500/20 border-purple-500/30 text-purple-300'
              : 'bg-gray-800/50 border-cyan-500/20 text-cyan-300 hover:border-cyan-500/40'
          }`}
        >
          <div className="flex items-center space-x-2">
            <Search className="w-4 h-4" />
            <span className="text-sm font-medium">Research Agent</span>
            {isResearchMode && <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse ml-auto"></div>}
          </div>
        </button>

        <div className="flex-1">
          <div className="bg-gray-800/50 border border-cyan-500/20 rounded-xl p-4 mb-4">
            <div className="flex items-center space-x-2 mb-2">
              <Terminal className="w-4 h-4 text-cyan-400" />
              <h2 className="text-sm font-semibold text-cyan-300 tracking-wide">Active Session</h2>
            </div>
            <p className="text-xs text-gray-400 font-mono break-all leading-relaxed">{session?.id}</p>
            <div className="flex items-center space-x-1 mt-2">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span className="text-xs text-green-400 font-medium">Secure</span>
            </div>
          </div>
          
          {!isResearchMode && (
            <div className="bg-gray-800/50 border border-cyan-500/20 rounded-xl p-4 mb-4">
              <div className="flex items-center space-x-2 mb-2">
                <Eye className="w-4 h-4 text-cyan-400" />
                <h2 className="text-sm font-semibold text-cyan-300 tracking-wide">Security Tips</h2>
              </div>
              <ul className="text-xs text-gray-400 space-y-1 leading-relaxed">
                <li>• Describe specific threats or vulnerabilities</li>
                <li>• Mention your current security setup</li>
                <li>• Ask about best practices and protocols</li>
              </ul>
            </div>
          )}

          {isResearchMode && (
            <div className="bg-purple-800/50 border border-purple-500/20 rounded-xl p-4 mb-4">
              <div className="flex items-center space-x-2 mb-2">
                <BookOpen className="w-4 h-4 text-purple-400" />
                <h2 className="text-sm font-semibold text-purple-300 tracking-wide">Research Topics</h2>
              </div>
              <ul className="text-xs text-gray-400 space-y-1 leading-relaxed">
                <li>• Security frameworks & standards</li>
                <li>• Threat intelligence analysis</li>
                <li>• Compliance requirements</li>
                <li>• Technology comparisons</li>
              </ul>
            </div>
          )}

          <div className="bg-gray-800/50 border border-cyan-500/20 rounded-xl p-4 mb-4">
            <div className="flex items-center space-x-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-red-400" />
              <h2 className="text-sm font-semibold text-red-300 tracking-wide">Threat Level</h2>
            </div>
            <div className="flex items-center space-x-2">
              <div className="flex-1 bg-gray-700 rounded-full h-2">
                <div className="bg-gradient-to-r from-green-500 to-yellow-500 h-2 rounded-full w-3/5"></div>
              </div>
              <span className="text-xs text-yellow-400 font-mono font-medium">MODERATE</span>
            </div>
          </div>
        </div>

        <div className="mt-auto">
          <div className="bg-gray-800/30 border border-cyan-500/10 rounded-xl p-3">
            <div className="flex items-center space-x-2 text-xs text-gray-400 font-medium">
              <Lock className="w-3 h-3" />
              <span>End-to-end encrypted</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className={`${isResearchMode ? 'flex-1' : 'flex-1'} flex flex-col transition-all duration-300`}>
        {/* Header */}
        <div className={`bg-gray-900/90 backdrop-blur-sm border-b border-cyan-500/20 p-4 lg:p-6 ${isResearchMode ? 'lg:border-r lg:border-r-cyan-500/20' : ''}`}>
          <div className="flex items-center space-x-3">
            <div className="lg:hidden w-8 h-8 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg flex items-center justify-center shadow-lg shadow-cyan-500/25">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg lg:text-xl font-semibold text-white tracking-tight">
                {isResearchMode ? 'Security Chat' : 'CyberGuard AI Assistant'}
              </h1>
              <p className="text-sm text-cyan-300 font-medium">
                {isResearchMode ? 'Main security assistance' : 'Your advanced cybersecurity companion'}
              </p>
              <p className="text-xs text-gray-400 mt-1">Welcome, {user.email}</p>
            </div>
            <div className="ml-auto flex items-center space-x-2">
              <button
                onClick={onLogout}
                className="flex items-center space-x-1 px-3 py-1.5 bg-gray-800/50 border border-gray-600 rounded-lg text-gray-300 hover:text-white hover:border-gray-500 transition-all duration-200"
              >
                <LogOut className="w-3 h-3" />
                <span className="text-xs font-medium">Logout</span>
              </button>
              <div className="flex items-center space-x-1">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                <span className="text-xs text-green-400 font-mono font-medium">ONLINE</span>
              </div>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className={`flex-1 overflow-y-auto p-4 lg:p-6 space-y-6 bg-gradient-to-b from-gray-900/50 to-gray-800/50 pb-24 ${isResearchMode ? 'lg:border-r lg:border-r-cyan-500/10' : ''}`}>
          {messages.map((message, index) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-fadeIn`}
              style={{ animationDelay: `${index * 100}ms` }}
            >
              <div className={`flex max-w-xs sm:max-w-md lg:max-w-2xl ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'} space-x-3`}>
                <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                  message.role === 'user' 
                    ? 'bg-gradient-to-br from-emerald-500 to-green-600 shadow-lg shadow-emerald-500/25' 
                    : 'bg-gradient-to-br from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/25'
                }`}>
                  {message.role === 'user' ? 
                    <User className="w-4 h-4 text-white" /> : 
                    <Bot className="w-4 h-4 text-white" />
                  }
                </div>
                
                <div className={`px-4 py-3 rounded-2xl shadow-sm ${
                  message.role === 'user'
                    ? 'bg-gradient-to-br from-emerald-500 to-green-600 text-white rounded-br-md shadow-lg shadow-emerald-500/25'
                    : 'bg-gray-900/90 border border-cyan-500/30 text-gray-100 rounded-bl-md shadow-lg backdrop-blur-sm'
                }`}>
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
                  <div className="flex items-center justify-between mt-2">
                    <p className={`text-xs ${
                      message.role === 'user' ? 'text-green-100' : 'text-cyan-400'
                    } font-medium`}>
                      {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                    
                    {message.role === 'assistant' && (
                      <div className="flex items-center space-x-1 ml-4">
                        <button
                          onClick={() => handleFeedback(message.id, 'like')}
                          className={`p-1 rounded transition-all duration-200 ${
                            message.feedback === 'like'
                              ? 'bg-green-500/20 text-green-400'
                              : 'text-gray-400 hover:text-green-400 hover:bg-green-500/10'
                          }`}
                        >
                          <ThumbsUp className="w-3 h-3" />
                        </button>
                        <button
                          onClick={() => handleFeedback(message.id, 'dislike')}
                          className={`p-1 rounded transition-all duration-200 ${
                            message.feedback === 'dislike'
                              ? 'bg-red-500/20 text-red-400'
                              : 'text-gray-400 hover:text-red-400 hover:bg-red-500/10'
                          }`}
                        >
                          <ThumbsDown className="w-3 h-3" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Dialog Trigger Button */}
                {message.role === 'assistant' && message.dialogConfig && (
                  <div className="mt-3 pt-3 border-t border-cyan-500/20">
                    <button
                      onClick={() => {
                        setCurrentDialogConfig(message.dialogConfig!);
                        setShowDialog(true);
                      }}
                      className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-cyan-500/20 to-blue-500/20 border border-cyan-500/30 text-cyan-300 rounded-lg hover:from-cyan-500/30 hover:to-blue-500/30 hover:border-cyan-500/50 transition-all duration-200"
                    >
                      <Shield className="w-4 h-4" />
                      <span className="text-sm font-medium">Open Security Form</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {isThinking && (
            <div className="flex justify-start animate-fadeIn">
              <ThinkingAnimation />
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className={`fixed bottom-0 ${isResearchMode ? 'left-0 right-1/2 lg:left-48' : 'right-0 left-0 lg:left-64'} bg-gray-900/95 backdrop-blur-md border-t border-cyan-500/20 p-4 lg:p-6 transition-all duration-300`}>
          <div className="max-w-4xl mx-auto">
            <div className="flex items-end space-x-4">
              <div className="flex-1 relative">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  disabled={isLoading}
                  placeholder={isLoading ? "CyberGuard AI is analyzing..." : "Describe your security concerns or ask for threat analysis..."}
                  className="w-full px-4 py-3 pr-12 bg-gray-800/70 border border-cyan-500/30 text-white placeholder-gray-400 rounded-xl focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 resize-none shadow-lg disabled:opacity-50 disabled:cursor-not-allowed backdrop-blur-sm text-sm leading-relaxed"
                />
                <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                  <Zap className="w-4 h-4 text-cyan-400" />
                </div>
              </div>
              
              <button
                onClick={sendMessage}
                disabled={!inputValue.trim() || isLoading}
                className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-cyan-500 to-blue-600 text-white rounded-xl hover:from-cyan-600 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 focus:ring-offset-gray-900 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center shadow-lg shadow-cyan-500/25"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
            
            <p className="text-xs text-gray-400 mt-3 text-center font-medium">
              Press Enter to send • CyberGuard AI provides threat analysis, security protocols, and defense strategies
            </p>
          </div>
        </div>
      </div>

      {/* Research Panel */}
      {isResearchMode && (
        <div className="w-1/2 flex flex-col bg-gradient-to-br from-purple-900/20 via-gray-800 to-indigo-900/20 border-l border-purple-500/20">
          {/* Research Header */}
          <div className="bg-gradient-to-r from-purple-900/90 to-indigo-900/90 backdrop-blur-sm border-b border-purple-500/20 p-4 lg:p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-lg flex items-center justify-center shadow-lg shadow-purple-500/25">
                  <Brain className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-lg lg:text-xl font-semibold text-white tracking-tight">Research Agent</h1>
                  <p className="text-sm text-purple-300 font-medium">Deep cybersecurity research & analysis</p>
                  {activeResearchTopic && (
                    <p className="text-xs text-gray-400 mt-1">Topic: {activeResearchTopic}</p>
                  )}
                </div>
              </div>
              <button
                onClick={() => setIsResearchMode(false)}
                className="p-2 text-gray-400 hover:text-white hover:bg-gray-800/50 rounded-lg transition-all duration-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Research Messages */}
          <div className="flex-1 overflow-y-auto p-4 lg:p-6 space-y-6 bg-gradient-to-b from-purple-900/10 to-indigo-900/10 pb-24">
            {researchMessages.map((message, index) => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-fadeIn`}
                style={{ animationDelay: `${index * 100}ms` }}
              >
                <div className={`flex max-w-xs sm:max-w-md lg:max-w-2xl ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'} space-x-3`}>
                  <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                    message.role === 'user' 
                      ? 'bg-gradient-to-br from-emerald-500 to-green-600 shadow-lg shadow-emerald-500/25' 
                      : 'bg-gradient-to-br from-purple-500 to-indigo-600 shadow-lg shadow-purple-500/25'
                  }`}>
                    {message.role === 'user' ? 
                      <User className="w-4 h-4 text-white" /> : 
                      <Brain className="w-4 h-4 text-white" />
                    }
                  </div>
                  
                  <div className={`px-4 py-3 rounded-2xl shadow-sm ${
                    message.role === 'user'
                      ? 'bg-gradient-to-br from-emerald-500 to-green-600 text-white rounded-br-md shadow-lg shadow-emerald-500/25'
                      : 'bg-gray-900/90 border border-purple-500/30 text-gray-100 rounded-bl-md shadow-lg backdrop-blur-sm'
                  }`}>
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
                    
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-purple-500/20">
                        <div className="flex items-center space-x-2 mb-2">
                          <FileText className="w-3 h-3 text-purple-400" />
                          <span className="text-xs text-purple-300 font-medium">Sources:</span>
                        </div>
                        <div className="space-y-1">
                          {message.sources.map((source, idx) => (
                            <div key={idx} className="flex items-center space-x-2">
                              <ChevronRight className="w-2 h-2 text-purple-400" />
                              <span className="text-xs text-gray-300">{source}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    <div className="flex items-center justify-between mt-2">
                      <p className={`text-xs ${
                        message.role === 'user' ? 'text-green-100' : 'text-purple-400'
                      } font-medium`}>
                        {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            
            {isResearchLoading && (
              <div className="flex justify-start animate-fadeIn">
                <ResearchThinkingAnimation />
              </div>
            )}
            
            <div ref={researchMessagesEndRef} />
          </div>

          {/* Research Input Area */}
          <div className="fixed bottom-0 right-0 left-1/2 bg-gradient-to-r from-purple-900/95 to-indigo-900/95 backdrop-blur-md border-t border-purple-500/20 p-4 lg:p-6">
            <div className="max-w-4xl mx-auto">
              <div className="flex items-end space-x-4">
                <div className="flex-1 relative">
                  <input
                    ref={researchInputRef}
                    type="text"
                    value={researchInput}
                    onChange={(e) => setResearchInput(e.target.value)}
                    onKeyPress={handleResearchKeyPress}
                    disabled={isResearchLoading}
                    placeholder={isResearchLoading ? "Research Agent is analyzing..." : "What would you like to research about cybersecurity?"}
                    className="w-full px-4 py-3 pr-12 bg-gray-800/70 border border-purple-500/30 text-white placeholder-gray-400 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 resize-none shadow-lg disabled:opacity-50 disabled:cursor-not-allowed backdrop-blur-sm text-sm leading-relaxed"
                  />
                  <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                    <Lightbulb className="w-4 h-4 text-purple-400" />
                  </div>
                </div>
                
                <button
                  onClick={sendResearchMessage}
                  disabled={!researchInput.trim() || isResearchLoading}
                  className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-purple-500 to-indigo-600 text-white rounded-xl hover:from-purple-600 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-gray-900 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center shadow-lg shadow-purple-500/25"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
              
              <p className="text-xs text-gray-400 mt-3 text-center font-medium">
                Press Enter to research • Deep analysis of cybersecurity topics with sources and insights
              </p>
            </div>
          </div>
        </div>
      )}
      
      {/* Dialog Box */}
      {showDialog && currentDialogConfig && (
        <DialogBox
          isOpen={showDialog}
          config={currentDialogConfig}
          onSubmit={handleDialogSubmit}
          onClose={handleDialogClose}
        />
      )}
    </div>
  );
};

export default ChatInterface;
