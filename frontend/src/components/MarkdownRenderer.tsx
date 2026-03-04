import { memo } from "react"
import Markdown from "react-markdown"
import remarkGfm from "remark-gfm"

interface MarkdownRendererProps {
  content: string
  className?: string
}

const H1 = memo(({ children, ...props }: React.ComponentPropsWithoutRef<"h1">) => (
  <h1 className="mb-4 mt-6 text-3xl font-bold text-foreground" {...props}>{children}</h1>
))
H1.displayName = "H1"

const H2 = memo(({ children, ...props }: React.ComponentPropsWithoutRef<"h2">) => (
  <h2 className="mb-3 mt-5 text-2xl font-semibold text-foreground" {...props}>{children}</h2>
))
H2.displayName = "H2"

const H3 = memo(({ children, ...props }: React.ComponentPropsWithoutRef<"h3">) => (
  <h3 className="mb-2 mt-4 text-xl font-medium text-foreground" {...props}>{children}</h3>
))
H3.displayName = "H3"

const H4 = memo(({ children, ...props }: React.ComponentPropsWithoutRef<"h4">) => (
  <h4 className="mb-2 mt-3 text-lg font-medium text-foreground" {...props}>{children}</h4>
))
H4.displayName = "H4"

const P = memo(({ children, ...props }: React.ComponentPropsWithoutRef<"p">) => (
  <p className="mb-4 text-foreground" {...props}>{children}</p>
))
P.displayName = "P"

const Ul = memo(({ children, ...props }: React.ComponentPropsWithoutRef<"ul">) => (
  <ul className="mb-4 list-disc pl-6 text-foreground" {...props}>{children}</ul>
))
Ul.displayName = "Ul"

const Ol = memo(({ children, ...props }: React.ComponentPropsWithoutRef<"ol">) => (
  <ol className="mb-4 list-decimal pl-6 text-foreground" {...props}>{children}</ol>
))
Ol.displayName = "Ol"

const Li = memo(({ children, ...props }: React.ComponentPropsWithoutRef<"li">) => (
  <li className="mb-1 text-foreground" {...props}>{children}</li>
))
Li.displayName = "Li"

const Blockquote = memo(({ children, ...props }: React.ComponentPropsWithoutRef<"blockquote">) => (
  <blockquote className="border-l-4 border-border pl-4 italic text-muted-foreground" {...props}>{children}</blockquote>
))
Blockquote.displayName = "Blockquote"

const InlineCode = memo(({ children, className, ...props }: React.ComponentPropsWithoutRef<"code">) => {
  // If inside a <pre>, render as block code
  if (className) {
    return <code className="font-mono text-sm text-foreground" {...props}>{children}</code>
  }
  return <code className="rounded bg-muted px-1 py-0.5 font-mono text-sm text-foreground" {...props}>{children}</code>
})
InlineCode.displayName = "InlineCode"

const Pre = memo(({ children, ...props }: React.ComponentPropsWithoutRef<"pre">) => (
  <pre className="mb-4 overflow-x-auto rounded-lg bg-muted p-4" {...props}>{children}</pre>
))
Pre.displayName = "Pre"

const A = memo(({ children, ...props }: React.ComponentPropsWithoutRef<"a">) => (
  <a className="text-blue-500 hover:underline" {...props}>{children}</a>
))
A.displayName = "A"

const TableWrapper = memo(({ children, ...props }: React.ComponentPropsWithoutRef<"table">) => (
  <div className="mb-4 overflow-x-auto">
    <table className="min-w-full border-collapse border border-border" {...props}>{children}</table>
  </div>
))
TableWrapper.displayName = "TableWrapper"

const Thead = memo(({ children, ...props }: React.ComponentPropsWithoutRef<"thead">) => (
  <thead className="bg-muted/50" {...props}>{children}</thead>
))
Thead.displayName = "Thead"

const Tbody = memo(({ children, ...props }: React.ComponentPropsWithoutRef<"tbody">) => (
  <tbody className="[&>tr:nth-child(even)]:bg-muted/20" {...props}>{children}</tbody>
))
Tbody.displayName = "Tbody"

const Tr = memo(({ children, ...props }: React.ComponentPropsWithoutRef<"tr">) => (
  <tr className="border-b border-border transition-colors hover:bg-muted/40" {...props}>{children}</tr>
))
Tr.displayName = "Tr"

const Th = memo(({ children, ...props }: React.ComponentPropsWithoutRef<"th">) => (
  <th className="border-r border-border bg-muted/50 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground last:border-r-0" {...props}>{children}</th>
))
Th.displayName = "Th"

const Td = memo(({ children, ...props }: React.ComponentPropsWithoutRef<"td">) => (
  <td className="border-r border-border px-4 py-3 align-top text-sm text-foreground last:border-r-0" {...props}>{children}</td>
))
Td.displayName = "Td"

const Hr = memo((props: React.ComponentPropsWithoutRef<"hr">) => (
  <hr className="my-6 border-border" {...props} />
))
Hr.displayName = "Hr"

const COMPONENTS = {
  h1: H1,
  h2: H2,
  h3: H3,
  h4: H4,
  p: P,
  ul: Ul,
  ol: Ol,
  li: Li,
  blockquote: Blockquote,
  code: InlineCode,
  pre: Pre,
  a: A,
  table: TableWrapper,
  thead: Thead,
  tbody: Tbody,
  tr: Tr,
  th: Th,
  td: Td,
  hr: Hr,
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div className={className}>
      <Markdown remarkPlugins={[remarkGfm]} components={COMPONENTS}>
        {content}
      </Markdown>
    </div>
  )
}
