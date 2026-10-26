interface HighlightedTextProps {
  text: string;
  query: string;
}

export function HighlightedText({ text, query }: HighlightedTextProps) {
  if (!query.trim()) {
    return <span>{text}</span>;
  }

  const terms = query
    .trim()
    .split(/\s+/)
    .filter((t) => t.length > 0);
  const pattern = terms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
  const regex = new RegExp(`(${pattern})`, 'gi');
  const parts = text.split(regex);

  return (
    <span>
      {parts.map((part, i) => {
        const isMatch = terms.some(
          (term) => part.toLowerCase() === term.toLowerCase(),
        );
        return isMatch ? (
          <mark key={i} className="bg-amber-100 text-gray-900 rounded-sm px-0.5">
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        );
      })}
    </span>
  );
}
