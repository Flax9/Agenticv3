import RichText from '../Common/RichText'
import ArtifactCard from './ArtifactCard'
import ExtractionCard from './ExtractionCard'
import { ReasoningBox, ToolCallCard } from './ToolCallCard'

export default function ChatBubble({ message, children }) {
  const isUser = message.sender === 'user'
  const author = message.author ?? (isUser ? 'FPP (User)' : 'Pertamina AI Copilot')

  return (
    <div className={`flex max-w-[94%] gap-3 ${isUser ? 'flex-row-reverse self-end' : ''}`}>
      <div
        aria-hidden="true"
        className={`flex h-[34px] w-[34px] shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-white shadow-sm ${
          isUser ? 'bg-sky-600' : 'border border-white/20 bg-gradient-to-br from-pertamina-navy to-pertamina-navy-light'
        }`}
      >
        {isUser ? 'Anda' : 'AI'}
      </div>

      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <span className={`text-[11px] font-semibold text-pertamina-gray-500 ${isUser ? 'text-right' : ''}`}>
          {author}
          {message.simulated && (
            <span className="ml-1.5 rounded bg-amber-50 px-1 text-[9.5px] font-bold text-amber-700">SIMULASI</span>
          )}
        </span>

        <div
          className={`rounded-2xl px-4 py-3 text-[13.5px] leading-relaxed shadow-sm ${
            isUser
              ? 'rounded-tr border border-sky-200 bg-pertamina-blue-light text-sky-900'
              : message.error
                ? 'rounded-tl border border-red-200 bg-pertamina-red-light text-red-900'
                : 'rounded-tl border border-pertamina-gray-200 bg-white text-pertamina-gray-900'
          }`}
        >
          {message.tool && <ToolCallCard title={message.tool.title} lines={message.tool.lines} />}

          {message.text && (
            <p className="whitespace-pre-wrap break-words">
              {message.pending && <span className="mr-1.5 inline-block animate-pulse">⏳</span>}
              <RichText text={message.text} />
            </p>
          )}

          {message.reasoning && <ReasoningBox lines={message.reasoning} />}
          {message.extractionCard && <ExtractionCard />}
          {message.artifact && <ArtifactCard {...message.artifact} />}
          {message.tail && (
            <p className="mt-2.5">
              <RichText text={message.tail} />
            </p>
          )}

          {message.attachment && (
            <div className="mt-1.5 inline-flex max-w-full items-center gap-2 rounded-lg border border-sky-300 bg-sky-600/10 px-3 py-1.5 text-xs font-medium text-sky-700">
              📎 <strong className="truncate">{message.attachment.name}</strong>
              <span className="shrink-0">({message.attachment.size})</span>
            </div>
          )}

          {children}
        </div>
      </div>
    </div>
  )
}
