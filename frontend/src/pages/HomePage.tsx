import { Mic } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Logo } from '../components/Logo';
import { SearchBar } from '../components/SearchBar';

export function HomePage() {
  const navigate = useNavigate();

  function handleSearch(query: string) {
    navigate(`/search?q=${encodeURIComponent(query)}`);
  }

  return (
    <div className="min-h-screen bg-stone-50 flex flex-col">
      <header className="px-4 py-4">
        <div className="max-w-4xl mx-auto">
          <Logo />
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center px-4 -mt-20">
        <div className="w-full max-w-xl text-center">
          <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 tracking-tight">
            Find that moment.
          </h1>
          <p className="mt-4 text-gray-500 text-lg">
            Search conversations, quotes and memorable moments from The Yard.
          </p>

          <div className="mt-8">
            <SearchBar onSearch={handleSearch} size="large" autoFocus />
          </div>

          <div className="mt-8 flex items-center justify-center gap-2 text-gray-400 text-sm">
            <Mic className="w-3.5 h-3.5" />
            <span>A searchable archive of The Yard podcast</span>
          </div>
        </div>
      </main>
    </div>
  );
}
