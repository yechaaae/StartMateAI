import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkBreaks from 'remark-breaks'

// 에이전트 답변/진행 메시지를 마크다운으로 렌더한다.
// - remark-gfm: 표(| |)/취소선/자동링크 등 GitHub 스타일 마크다운
// - remark-breaks: 단일 줄바꿈(\n)도 줄바꿈으로 유지
// - react-markdown 기본값이 raw HTML을 렌더하지 않으므로 XSS에 안전
// - 해시태그(#태그)는 '#' 뒤 공백이 없어 헤더로 변환되지 않고 그대로 표시됨
export const ChatMarkdown = ({ text }) => (
  <div className="chat-markdown">
    <Markdown remarkPlugins={[remarkGfm, remarkBreaks]}>{text || ''}</Markdown>
  </div>
)
