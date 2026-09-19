import React, { useState, useRef, useEffect } from 'react';

import {
  Bot,
  Send,
  Sparkles,
  User,
  Compass,
  DollarSign,
  AlertTriangle,
  Clock,
  ArrowRight,
  Lightbulb,
} from 'lucide-react';

import { useTrip } from '../hooks/useTrip';
import DisruptionAlertBanner from '../components/DisruptionAlertBanner';

export default function AIAssistantPage() {
  const {
    activeTrip,
    chatMessages,
    isAiTyping,
    sendMessage,
    activeDisruptions,
    setCurrentPage,
  } = useTrip();

  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef(null);

  const curr = activeTrip?.currency || 'INR';

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({
      behavior: 'smooth',
    });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages, isAiTyping]);

  const handleSend = (e) => {
    e.preventDefault();

    if (!inputText.trim()) return;

    sendMessage(inputText);
    setInputText('');
  };

  const handleSuggestionClick = (suggestion) => {
    sendMessage(suggestion);
  };

  const samplePromptCards = [
    {
      category: 'Itinerary Planning',
      icon: Clock,
      prompt: 'What should I do tomorrow morning?',
      desc: 'Retrieves tomorrow’s scheduled slots and transit buffers',
    },
    {
      category: 'Proximity & Logistics',
      icon: Compass,
      prompt: 'Which activities are close to my hotel?',
      desc: 'Uses spatial distance tool to find nearby venues',
    },
    {
      category: 'What-If Simulation',
      icon: AlertTriangle,
      prompt: 'What happens if my museum booking is cancelled?',
      desc: 'Evaluates fallback options and alternative activities',
    },
    {
      category: 'Budget Guardrails',
      icon: DollarSign,
      prompt: 'Can I reduce my budget to 70000 INR?',
      desc: 'Recalculates category allocations without dropping confirmed stops',
    },
  ];

  const quickPrompts = [
    'What should I do tomorrow morning?',
    'Which activities are close to my hotel?',
    'What happens if my museum booking is cancelled?',
    'How much have I spent?',
    'Can I reduce my budget to 70000 INR?',
    'What activities match my photography interest?',
    'Apply it.',
  ];

  return (
    <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5 flex flex-col min-h-[calc(100vh-5rem)]">

      {/* Disruption Banner */}
      <DisruptionAlertBanner />

      {/* Header */}
      <div className="pb-5 border-b border-slate-800 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-5">
        <div>
          <div className="flex items-center space-x-2 text-xs sm:text-sm font-semibold text-cyan-400 mb-1.5">
            <Sparkles className="w-4 h-4" />
            <span>Autonomous Tool-Equipped Agent</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Ask TravelPilot Co-Pilot
          </h1>

          <p className="text-sm text-slate-400 mt-1">
            Your intelligent assistant for itinerary, budget and travel disruptions.
          </p>
        </div>

        {/* Active Context */}
        <div className="flex items-center flex-wrap gap-2 text-xs">

          {activeDisruptions && activeDisruptions.length > 0 && (
            <button
              onClick={() => setCurrentPage('disruptions')}
              className="px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 hover:bg-amber-500/20 transition flex items-center space-x-1.5 cursor-pointer"
            >
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />

              <span>
                {activeDisruptions.length} Disruption
                {activeDisruptions.length > 1 ? 's' : ''} Active
              </span>
            </button>
          )}

          <div className="flex items-center space-x-2 text-xs bg-slate-900 border border-slate-800 px-3 py-2 rounded-full text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />

            <span className="text-slate-400">
              Context:
            </span>

            <span className="font-medium text-white">
              {activeTrip?.destination || 'No trip selected'}
            </span>

            <span className="text-slate-600">
              |
            </span>

            <span className="text-emerald-400 font-mono font-medium">
              {curr}{' '}
              {Math.max(
                0,
                (activeTrip?.budget || 0) -
                  (activeTrip?.spending || 0)
              ).toLocaleString()}{' '}
              Buffer
            </span>
          </div>
        </div>
      </div>

      {/* ========================= */}
      {/* LARGE AI CHAT AREA */}
      {/* ========================= */}

      <div
        className="
          flex-1
          min-h-[520px]
          lg:min-h-[600px]
          xl:min-h-[650px]
          overflow-y-auto
          pr-2
          sm:pr-3
          space-y-5
          mb-5
          rounded-2xl
          bg-slate-950/30
          border
          border-slate-800/60
          p-4
          sm:p-6
          lg:p-7
          shadow-inner
        "
      >

        {chatMessages.length === 0 ? (

          /* ========================= */
          /* EMPTY CHAT STATE */
          /* ========================= */

          <div className="min-h-full flex flex-col items-center justify-center text-center px-4 sm:px-8 py-8">

            <div className="w-20 h-20 rounded-3xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 mb-5 shadow-xl shadow-cyan-500/10">
              <Bot className="w-10 h-10" />
            </div>

            <h3 className="text-xl sm:text-2xl font-bold text-white mb-2">
              Grounded AI Travel Co-Pilot
            </h3>

            <p className="text-sm sm:text-base text-slate-300 max-w-2xl leading-relaxed mb-8">
              Unlike generic chatbots, TravelPilot retrieves your live
              itinerary, spatial information and budget state to help
              you plan, optimize and adapt your journey.
            </p>

            {/* Prompt Cards */}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-4xl text-left">

              {samplePromptCards.map((card, idx) => {
                const Icon = card.icon;

                return (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleSuggestionClick(card.prompt)}
                    className="
                      p-5
                      rounded-2xl
                      bg-slate-900/80
                      hover:bg-slate-800
                      border
                      border-slate-800
                      hover:border-cyan-500/40
                      text-left
                      transition
                      group
                      cursor-pointer
                      focus-visible:ring-2
                      focus-visible:ring-cyan-400
                      min-h-[130px]
                    "
                  >
                    <div className="flex items-center space-x-2 text-xs text-cyan-400 font-medium mb-2">
                      <Icon className="w-4 h-4" />
                      <span>{card.category}</span>
                    </div>

                    <div className="text-sm sm:text-base font-semibold text-white group-hover:text-cyan-200 transition">
                      "{card.prompt}"
                    </div>

                    <div className="text-xs sm:text-sm text-slate-400 mt-2 leading-relaxed">
                      {card.desc}
                    </div>
                  </button>
                );
              })}

            </div>
          </div>

        ) : (

          /* ========================= */
          /* CHAT MESSAGES */
          /* ========================= */

          chatMessages.map((msg) => {
            const isAi = msg.sender === 'ai';

            return (
              <div
                key={msg.id}
                className={`flex items-start gap-3 ${
                  isAi ? 'justify-start' : 'justify-end'
                }`}
              >

                {/* AI Avatar */}

                {isAi && (
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center text-slate-950 shrink-0 shadow-md ring-2 ring-cyan-500/20">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                )}

                {/* Message */}

                <div
                  className={`
                    max-w-[90%]
                    lg:max-w-[80%]
                    rounded-2xl
                    p-5
                    text-sm
                    sm:text-base
                    leading-relaxed
                    shadow-lg
                    ${
                      isAi
                        ? 'bg-slate-900/95 border border-slate-800/90 text-slate-200 backdrop-blur-sm'
                        : 'bg-gradient-to-r from-cyan-400 to-teal-400 text-slate-950 font-medium ml-auto shadow-cyan-500/10'
                    }
                  `}
                >

                  <p className="whitespace-pre-line leading-relaxed">
                    {msg.text}
                  </p>

                  <div
                    className={`
                      text-[10px]
                      mt-3
                      pt-2.5
                      border-t
                      flex
                      items-center
                      justify-between
                      ${
                        isAi
                          ? 'border-slate-800/80 text-slate-500'
                          : 'border-slate-900/10 text-slate-900/70'
                      }
                    `}
                  >

                    <span>
                      {msg.timestamp}
                    </span>

                    {isAi && (
                      <div className="flex items-center space-x-2">
                        <span className="text-[9px] font-mono text-cyan-400/90 uppercase tracking-wider bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-500/20">
                          {msg.intent
                            ? `Intent: ${msg.intent}`
                            : 'Tool Verified'}
                        </span>
                      </div>
                    )}

                  </div>

                  {/* Suggestions */}

                  {isAi &&
                    msg.suggestions &&
                    msg.suggestions.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-slate-800/80 space-y-2">

                        <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block">
                          Quick Actions & Follow-ups:
                        </span>

                        <div className="flex flex-wrap gap-2">

                          {msg.suggestions.map((sug, idx) => (
                            <button
                              key={idx}
                              type="button"
                              onClick={() =>
                                handleSuggestionClick(sug)
                              }
                              className="
                                text-xs
                                px-3
                                py-1.5
                                bg-slate-950
                                hover:bg-slate-800
                                text-cyan-300
                                hover:text-cyan-200
                                border
                                border-cyan-500/25
                                rounded-lg
                                transition
                                text-left
                                cursor-pointer
                                flex
                                items-center
                                space-x-1
                                focus-visible:ring-2
                                focus-visible:ring-cyan-400
                              "
                            >
                              <span>
                                {sug}
                              </span>

                              <ArrowRight className="w-3 h-3" />
                            </button>
                          ))}

                        </div>
                      </div>
                    )}

                </div>

                {/* User Avatar */}

                {!isAi && (
                  <div className="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0">
                    <User className="w-5 h-5" />
                  </div>
                )}

              </div>
            );
          })
        )}

        {/* Typing Indicator */}

        {isAiTyping && (
          <div className="flex items-center space-x-3">

            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center text-slate-950 shrink-0 animate-pulse">
              <Bot className="w-5 h-5 text-white" />
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-400 flex items-center space-x-3 shadow-md">
              <Sparkles className="w-4 h-4 text-cyan-400 animate-spin" />

              <span>
                Analyzing trip state & calling tools...
              </span>
            </div>

          </div>
        )}

        <div ref={messagesEndRef} />

      </div>

      {/* ========================= */}
      {/* QUICK PROMPTS */}
      {/* ========================= */}

      <div className="mb-4">

        <div className="flex items-center space-x-1.5 text-xs text-slate-400 mb-2">
          <Lightbulb className="w-3.5 h-3.5 text-amber-400" />
          <span>Quick Prompt Starters:</span>
        </div>

        <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">

          {quickPrompts.map((prompt, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSuggestionClick(prompt)}
              className="
                text-xs
                px-3.5
                py-2
                bg-slate-900/90
                hover:bg-slate-800
                border
                border-slate-800
                hover:border-cyan-500/40
                text-slate-300
                hover:text-white
                rounded-xl
                whitespace-nowrap
                transition
                cursor-pointer
                focus-visible:ring-2
                focus-visible:ring-cyan-400
              "
            >
              {prompt}
            </button>
          ))}

        </div>
      </div>

      {/* ========================= */}
      {/* LARGE MESSAGE INPUT */}
      {/* ========================= */}

      <form onSubmit={handleSend} className="relative">

        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder={`Ask about ${
            activeTrip?.destination || 'your trip'
          } (e.g. "What should I do tomorrow morning?")...`}
          className="
            w-full
            bg-slate-900
            border
            border-slate-800
            rounded-2xl
            pl-5
            pr-16
            py-4
            text-sm
            sm:text-base
            text-white
            focus:outline-none
            focus:border-cyan-400
            transition
            shadow-lg
            placeholder:text-slate-500
            focus-visible:ring-2
            focus-visible:ring-cyan-400
          "
          aria-label="Message TravelPilot Assistant"
        />

        <button
          type="submit"
          disabled={!inputText.trim() || isAiTyping}
          className="
            absolute
            right-2
            top-2
            p-3
            bg-cyan-400
            hover:bg-cyan-300
            disabled:opacity-40
            text-slate-950
            rounded-xl
            transition
            cursor-pointer
            shadow-md
          "
          aria-label="Send Message"
        >
          <Send className="w-5 h-5" />
        </button>

      </form>
    </div>
  );
}