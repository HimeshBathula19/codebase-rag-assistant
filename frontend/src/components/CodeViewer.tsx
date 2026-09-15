import type { ReactNode } from "react";

const KEYWORDS = new Set([
  "import",
  "from",
  "as",
  "def",
  "class",
  "return",
  "if",
  "else",
  "elif",
  "for",
  "while",
  "try",
  "except",
  "finally",
  "with",
  "async",
  "await",
  "yield",
  "const",
  "let",
  "var",
  "function",
  "export",
  "default",
  "new",
  "this",
  "true",
  "false",
  "null",
  "None",
  "True",
  "False",
  "public",
  "private",
  "protected",
  "static",
  "void",
  "int",
  "string",
  "package",
  "func",
  "type",
  "struct",
  "impl",
  "fn",
  "mod",
  "use",
  "match",
]);

function highlightLine(line: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const regex = /("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\/\/.*|#.*|\b\d+\b|\b[A-Za-z_][\w]*\b|[^\w\s]+|\s+)/g;
  const tokens = line.match(regex) || [line];
  tokens.forEach((token, index) => {
    let className = "text-slate-800";
    if (/^['"]/.test(token)) className = "text-emerald-700";
    else if (/^(\/\/|#)/.test(token)) className = "text-slate-400";
    else if (/^\d+$/.test(token)) className = "text-amber-700";
    else if (KEYWORDS.has(token)) className = "text-accent-700";
    parts.push(
      <span key={index} className={className}>
        {token}
      </span>,
    );
  });
  return parts;
}

export function CodeViewer({
  path,
  content,
  highlightStart,
  highlightEnd,
}: {
  path: string;
  content: string;
  highlightStart?: number;
  highlightEnd?: number;
}) {
  const lines = content.length ? content.split("\n") : [""];
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <div className="border-b border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-500">{path}</div>
      <div className="max-h-[70vh] overflow-auto scrollbar-thin">
        <table className="w-full border-collapse font-mono text-[13px] leading-6">
          <tbody>
            {lines.map((line, idx) => {
              const lineNo = idx + 1;
              const active =
                highlightStart && highlightEnd ? lineNo >= highlightStart && lineNo <= highlightEnd : false;
              return (
                <tr key={lineNo} className={active ? "bg-accent-50" : undefined} id={`line-${lineNo}`}>
                  <td className="w-12 select-none border-r border-slate-100 px-2 text-right text-slate-400">{lineNo}</td>
                  <td className="whitespace-pre px-3">{highlightLine(line)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
