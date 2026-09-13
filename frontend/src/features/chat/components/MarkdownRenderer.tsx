import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Check, Copy } from "lucide-react";

interface MarkdownRendererProps {
  content: string;
  onCitationClick?: (page: number) => void;
}

const CodeBlock = ({ language, value }: { language: string; value: string }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  return (
    <div className="relative group my-3 rounded-xl overflow-hidden border border-border bg-[#1E1E1E]">
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-[#252526] border-b border-border text-xs text-muted-foreground font-mono">
        <span>{language || "code"}</span>
        <button
          type="button"
          onClick={handleCopy}
          className="inline-flex items-center gap-1 text-[11px] hover:text-foreground transition-colors p-1 rounded hover:bg-white/5"
          title="Copy code"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <SyntaxHighlighter
        language={language || "text"}
        style={vscDarkPlus}
        customStyle={{
          margin: 0,
          padding: "1rem",
          fontSize: "0.825rem",
          backgroundColor: "transparent",
        }}
      >
        {value}
      </SyntaxHighlighter>
    </div>
  );
};

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  onCitationClick,
}) => {
  return (
    <div className="prose dark:prose-invert prose-sm max-w-none break-words leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          // Tables
          table: ({ children }) => (
            <div className="overflow-x-auto my-4 rounded-xl border border-border">
              <table className="min-w-full divide-y divide-border text-xs text-left">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-muted/60 text-muted-foreground uppercase font-semibold">
              {children}
            </thead>
          ),
          th: ({ children }) => (
            <th className="px-3.5 py-2.5 font-bold border-b border-border">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-3.5 py-2 border-b border-border/50">
              {children}
            </td>
          ),
          tr: ({ children }) => (
            <tr className="hover:bg-muted/30 transition-colors">{children}</tr>
          ),

          // Code blocks
          code({ node, inline, className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || "");
            const codeString = String(children).replace(/\n$/, "");

            if (!inline && match) {
              return (
                <CodeBlock
                  language={match[1]}
                  value={codeString}
                />
              );
            }

            if (!inline && codeString.includes("\n")) {
              return (
                <CodeBlock
                  language=""
                  value={codeString}
                />
              );
            }

            return (
              <code
                className="px-1.5 py-0.5 rounded-md font-mono text-xs bg-muted text-foreground border border-border/50"
                {...props}
              >
                {children}
              </code>
            );
          },

          // Blockquotes
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-primary/60 bg-primary/5 pl-4 py-1.5 my-3 rounded-r-lg italic text-muted-foreground">
              {children}
            </blockquote>
          ),

          // Links & potential page citations e.g. [Page 4](page:4)
          a: ({ href, children }) => {
            if (href?.startsWith("page:") && onCitationClick) {
              const pageNum = parseInt(href.replace("page:", ""), 10);
              return (
                <button
                  type="button"
                  onClick={() => onCitationClick(pageNum)}
                  className="inline-flex items-center px-1.5 py-0.2 mx-0.5 rounded bg-primary/10 text-primary hover:bg-primary/20 font-semibold text-xs transition-colors"
                >
                  {children}
                </button>
              );
            }
            return (
              <a
                href={href}
                target="_blank"
                rel="noreferrer"
                className="text-primary hover:underline font-medium"
              >
                {children}
              </a>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
