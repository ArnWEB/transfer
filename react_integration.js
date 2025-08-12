// Update your existing React component with these functions and state management

// Add these new state variables to your existing component
const [researchSessions, setResearchSessions] = useState(new Map());
const [activeResearchSession, setActiveResearchSession] = useState(null);
const [researchWebSocket, setResearchWebSocket] = useState(null);

// Research API configuration
const RESEARCH_API_BASE_URL = 'http://localhost:8000'; // Adjust for your backend URL

// Enhanced research message sending function
const sendResearchMessage = async () => {
  if (!researchInput.trim() || isResearchLoading) return;

  const userMessage = {
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

  try {
    // Start research with backend
    const response = await fetch(`${RESEARCH_API_BASE_URL}/api/research/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: userMessage.content,
        max_results: 8,
        search_depth: 'advanced',
        focus_areas: ['cybersecurity', 'threat intelligence', 'security frameworks']
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const researchSession = await response.json();
    setActiveResearchSession(researchSession);
    
    // Store session in state
    setResearchSessions(prev => {
      const updated = new Map(prev);
      updated.set(researchSession.id, {
        ...researchSession,
        userQuery: userMessage.content,
        startTime: new Date()
      });
      return updated;
    });

    // Establish WebSocket connection for real-time updates
    connectToResearchWebSocket(researchSession.id);

  } catch (error) {
    console.error('Error starting research:', error);
    
    // Fallback to mock response
    setTimeout(() => {
      const mockResponse = {
        id: 'research-assistant-' + Date.now(),
        content: `🔍 **Research Analysis**: "${userMessage.content}"\n\n**Connection Issue**: Unable to reach research backend. Showing cached analysis:\n\n**Key Findings:**\n• Advanced threat detection mechanisms are evolving rapidly\n• Zero-trust architecture becoming industry standard\n• AI-powered solutions show significant improvements\n\n**Recommendations:**\n• Implement multi-layered security protocols\n• Regular security audits recommended\n• Consider AI-enhanced monitoring systems\n\n*Note: Live research unavailable. Please check backend connection.*`,
        role: 'assistant',
        timestamp: new Date(),
        topic: activeResearchTopic,
        sources: [
          'Cached Security Framework Analysis',
          'Baseline Threat Intelligence Report'
        ]
      };

      setResearchMessages(prev => [...prev, mockResponse]);
      setIsResearchLoading(false);
    }, 2000);
  }
};

// WebSocket connection for real-time research updates
const connectToResearchWebSocket = (researchId) => {
  try {
    const wsUrl = `ws://localhost:8000/api/research/ws/${researchId}`;
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log(`WebSocket connected for research ${researchId}`);
      setResearchWebSocket(ws);
    };

    ws.onmessage = (event) => {
      const statusUpdate = JSON.parse(event.data);
      handleResearchStatusUpdate(statusUpdate);
    };

    ws.onclose = (event) => {
      console.log('Research WebSocket closed:', event.code, event.reason);
      setResearchWebSocket(null);
    };

    ws.onerror = (error) => {
      console.error('Research WebSocket error:', error);
    };

  } catch (error) {
    console.error('Error establishing WebSocket connection:', error);
  }
};

// Handle real-time research status updates
const handleResearchStatusUpdate = (statusUpdate) => {
  const { id, status, progress, current_step } = statusUpdate;
  
  // Update session in state
  setResearchSessions(prev => {
    const updated = new Map(prev);
    if (updated.has(id)) {
      updated.set(id, {
        ...updated.get(id),
        status,
        progress,
        current_step,
        lastUpdate: new Date()
      });
    }
    return updated;
  });

  // Update UI with progress
  if (status === 'running') {
    // Show progress in research messages
    setResearchMessages(prev => {
      const filtered = prev.filter(msg => !msg.id.includes('progress-update'));
      return [...filtered, {
        id: `progress-update-${Date.now()}`,
        content: `🔬 **Research Progress**: ${current_step}\n\nProgress: ${Math.round(progress * 100)}%`,
        role: 'assistant',
        timestamp: new Date(),
        isProgress: true
      }];
    });
  }

  // Handle completion
  if (status === 'completed') {
    fetchResearchResults(id);
  } else if (status === 'failed') {
    setIsResearchLoading(false);
    setResearchMessages(prev => [...prev, {
      id: `error-${Date.now()}`,
      content: `❌ **Research Failed**: ${statusUpdate.message || 'Unknown error occurred'}`,
      role: 'assistant',
      timestamp: new Date(),
      isError: true
    }]);
  }
};

// Fetch completed research results
const fetchResearchResults = async (researchId) => {
  try {
    const response = await fetch(`${RESEARCH_API_BASE_URL}/api/research/result/${researchId}`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const results = await response.json();
    
    // Remove progress messages
    setResearchMessages(prev => 
      prev.filter(msg => !msg.isProgress)
    );

    // Format and display results
    const formattedContent = formatResearchResults(results);
    
    const resultMessage = {
      id: `research-result-${Date.now()}`,
      content: formattedContent,
      role: 'assistant',
      timestamp: new Date(results.timestamp),
      topic: activeResearchTopic,
      sources: results.sources.map(source => source.title),
      metadata: results.metadata
    };

    setResearchMessages(prev => [...prev, resultMessage]);
    setIsResearchLoading(false);

    // Close WebSocket
    if (researchWebSocket) {
      researchWebSocket.close();
      setResearchWebSocket(null);
    }

  } catch (error) {
    console.error('Error fetching research results:', error);
    setIsResearchLoading(false);
    
    setResearchMessages(prev => [...prev, {
      id: `fetch-error-${Date.now()}`,
      content: `⚠️ **Error**: Could not retrieve research results. Please try again.`,
      role: 'assistant',
      timestamp: new Date(),
      isError: true
    }]);
  }
};

// Format research results for display
const formatResearchResults = (results) => {
  const { summary, key_findings, recommendations, sources, metadata } = results;
  
  let formatted = `🎯 **Research Analysis**: "${results.query}"\n\n`;
  
  // Key findings
  if (key_findings && key_findings.length > 0) {
    formatted += `🔍 **Key Findings:**\n`;
    key_findings.forEach(finding => {
      formatted += `• ${finding}\n`;
    });
    formatted += `\n`;
  }

  // Recommendations
  if (recommendations && recommendations.length > 0) {
    formatted += `💡 **Recommendations:**\n`;
    recommendations.forEach(rec => {
      formatted += `• ${rec}\n`;
    });
    formatted += `\n`;
  }

  // Summary (truncated if too long)
  if (summary && summary.length > 100) {
    formatted += `📊 **Detailed Analysis:**\n`;
    formatted += summary.length > 500 ? 
      summary.substring(0, 500) + '...\n\n' : 
      summary + '\n\n';
  }

  // Metadata
  if (metadata) {
    formatted += `📈 **Research Stats:**\n`;
    formatted += `• Sources analyzed: ${metadata.total_sources || 0}\n`;
    formatted += `• Findings extracted: ${metadata.findings_count || 0}\n`;
    formatted += `• Recommendations generated: ${metadata.recommendations_count || 0}\n`;
  }

  return formatted;
};

// Enhanced research thinking animation with progress
const ResearchThinkingAnimation = ({ progress = 0, currentStep = "Analyzing..." }) => (
  <div className="flex flex-col space-y-2 p-4 bg-purple-900/90 border border-purple-500/30 rounded-2xl shadow-lg max-w-md backdrop-blur-sm">
    <div className="flex items-center space-x-2">
      <div className="flex items-center justify-center w-8 h-8 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-full animate-pulse">
        <Brain className="w-4 h-4 text-white" />
      </div>
      <div className="flex space-x-1">
        <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse"></div>
        <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
        <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
      </div>
      <span className="text-xs text-purple-300 font-mono">{currentStep}</span>
    </div>
    
    {/* Progress Bar */}
    <div className="w-full bg-purple-900/50 rounded-full h-2">
      <div 
        className="bg-gradient-to-r from-purple-400 to-indigo-400 h-2 rounded-full transition-all duration-300 ease-out"
        style={{ width: `${Math.round(progress * 100)}%` }}
      ></div>
    </div>
    
    <div className="text-xs text-purple-200 text-center">
      {Math.round(progress * 100)}% Complete
    </div>
  </div>
);

// Cleanup function for WebSocket connections
const cleanupResearchWebSocket = () => {
  if (researchWebSocket && researchWebSocket.readyState === WebSocket.OPEN) {
    researchWebSocket.close();
  }
  setResearchWebSocket(null);
};

// Enhanced research message component with metadata
const ResearchMessageComponent = ({ message, index }) => (
  <div
    key={message.id}
    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-fadeIn`}
    style={{ animationDelay: `${index * 100}ms` }}
  >
    <div className={`flex max-w-xs sm:max-w-md lg:max-w-2xl ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'} space-x-3`}>
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
        message.role === 'user' 
          ? 'bg-gradient-to-br from-emerald-500 to-green-600 shadow-lg shadow-emerald-500/25' 
          : message.isProgress
          ? 'bg-gradient-to-br from-amber-500 to-orange-600 shadow-lg shadow-amber-500/25'
          : message.isError
          ? 'bg-gradient-to-br from-red-500 to-rose-600 shadow-lg shadow-red-500/25'
          : 'bg-gradient-to-br from-purple-500 to-indigo-600 shadow-lg shadow-purple-500/25'
      }`}>
        {message.role === 'user' ? 
          <User className="w-4 h-4 text-white" /> : 
          message.isProgress ? 
          <Search className="w-4 h-4 text-white animate-spin" /> :
          message.isError ?
          <AlertTriangle className="w-4 h-4 text-white" /> :
          <Brain className="w-4 h-4 text-white" />
        }
      </div>
      
      <div className={`px-4 py-3 rounded-2xl shadow-sm ${
        message.role === 'user'
          ? 'bg-gradient-to-br from-emerald-500 to-green-600 text-white rounded-br-md shadow-lg shadow-emerald-500/25'
          : message.isProgress
          ? 'bg-gradient-to-br from-amber-900/90 to-orange-900/90 border border-amber-500/30 text-amber-100 rounded-bl-md shadow-lg backdrop-blur-sm'
          : message.isError
          ? 'bg-gradient-to-br from-red-900/90 to-rose-900/90 border border-red-500/30 text-red-100 rounded-bl-md shadow-lg backdrop-blur-sm'
          : 'bg-gray-900/90 border border-purple-500/30 text-gray-100 rounded-bl-md shadow-lg backdrop-blur-sm'
      }`}>
        <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        
        {message.sources && message.sources.length > 0 && !message.isProgress && !message.isError && (
          <div className="mt-3 pt-3 border-t border-purple-500/20">
            <div className="flex items-center space-x-2 mb-2">
              <FileText className="w-3 h-3 text-purple-400" />
              <span className="text-xs text-purple-300 font-medium">Sources:</span>
            </div>
            <div className="space-y-1">
              {message.sources.slice(0, 5).map((source, idx) => (
                <div key={idx} className="flex items-center space-x-2">
                  <ChevronRight className="w-2 h-2 text-purple-400" />
                  <span className="text-xs text-gray-300 truncate">{source}</span>
                </div>
              ))}
              {message.sources.length > 5 && (
                <div className="flex items-center space-x-2">
                  <span className="text-xs text-purple-400">+{message.sources.length - 5} more sources</span>
                </div>
              )}
            </div>
          </div>
        )}

        {message.metadata && !message.isProgress && !message.isError && (
          <div className="mt-2 pt-2 border-t border-purple-500/10">
            <div className="flex items-center space-x-4 text-xs text-purple-300">
              {message.metadata.total_sources && (
                <span>📊 {message.metadata.total_sources} sources</span>
              )}
              {message.metadata.findings_count && (
                <span>🔍 {message.metadata.findings_count} findings</span>
              )}
              {message.metadata.recommendations_count && (
                <span>💡 {message.metadata.recommendations_count} recommendations</span>
              )}
            </div>
          </div>
        )}
        
        <div className="flex items-center justify-between mt-2">
          <p className={`text-xs ${
            message.role === 'user' ? 'text-green-100' : 
            message.isProgress ? 'text-amber-300' :
            message.isError ? 'text-red-300' :
            'text-purple-400'
          } font-medium`}>
            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        </div>
      </div>
    </div>
  </div>
);

// Function to get current research session status
const getCurrentResearchStatus = () => {
  if (!activeResearchSession) return null;
  
  const session = researchSessions.get(activeResearchSession.id);
  return session || null;
};

// Enhanced research panel with session management
const EnhancedResearchPanel = () => {
  const currentSession = getCurrentResearchStatus();
  
  return (
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
          
          {/* Session Status Indicator */}
          <div className="flex items-center space-x-3">
            {currentSession && (
              <div className="flex items-center space-x-2 px-3 py-1.5 bg-purple-800/50 rounded-lg border border-purple-500/30">
                <div className={`w-2 h-2 rounded-full ${
                  currentSession.status === 'running' ? 'bg-amber-400 animate-pulse' :
                  currentSession.status === 'completed' ? 'bg-green-400' :
                  currentSession.status === 'failed' ? 'bg-red-400' :
                  'bg-gray-400'
                }`}></div>
                <span className="text-xs text-purple-200 font-medium">
                  {currentSession.status === 'running' ? 'Researching...' :
                   currentSession.status === 'completed' ? 'Complete' :
                   currentSession.status === 'failed' ? 'Failed' :
                   'Ready'}
                </span>
                {currentSession.status === 'running' && currentSession.progress && (
                  <span className="text-xs text-purple-300">
                    {Math.round(currentSession.progress * 100)}%
                  </span>
                )}
              </div>
            )}
            
            <button
              onClick={() => setIsResearchMode(false)}
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-800/50 rounded-lg transition-all duration-200"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Research Messages */}
      <div className="flex-1 overflow-y-auto p-4 lg:p-6 space-y-6 bg-gradient-to-b from-purple-900/10 to-indigo-900/10 pb-24">
        {researchMessages.map((message, index) => (
          <ResearchMessageComponent key={message.id} message={message} index={index} />
        ))}
        
        {isResearchLoading && (
          <div className="flex justify-start animate-fadeIn">
            <ResearchThinkingAnimation 
              progress={currentSession?.progress || 0} 
              currentStep={currentSession?.current_step || "Initializing research..."}
            />
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
                placeholder={
                  isResearchLoading ? 
                    (currentSession?.current_step || "Research Agent is analyzing...") : 
                    "What would you like to research about cybersecurity?"
                }
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
            Press Enter to research • Powered by LangGraph + Tavily for comprehensive analysis
          </p>
        </div>
      </div>
    </div>
  );
};

// Add cleanup effect
useEffect(() => {
  return () => {
    cleanupResearchWebSocket();
  };
}, []);

// Update the main research panel render in your existing component
// Replace the existing research panel with:
{isResearchMode && <EnhancedResearchPanel />}