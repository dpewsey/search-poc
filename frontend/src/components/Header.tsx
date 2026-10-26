import { useNavigate } from 'react-router-dom';
import { Logo } from './Logo';
import { SearchBar } from './SearchBar';

interface HeaderProps {
  query?: string;
  showSearch?: boolean;
}

export function Header({ query, showSearch = true }: HeaderProps) {
  const navigate = useNavigate();

  function handleSearch(q: string) {
    navigate(`/search?q=${encodeURIComponent(q)}`);
  }

  return (
    <header className="border-b border-gray-100 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
      <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-6">
        <Logo />
        {showSearch && (
          <div className="flex-1 max-w-xl">
            <SearchBar initialQuery={query} onSearch={handleSearch} />
          </div>
        )}
      </div>
    </header>
  );
}
