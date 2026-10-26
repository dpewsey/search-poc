import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { EpisodePage } from './pages/EpisodePage';
import { EpisodesPage } from './pages/EpisodesPage';
import { HomePage } from './pages/HomePage';
import { SearchResultsPage } from './pages/SearchResultsPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/search" element={<SearchResultsPage />} />
        <Route path="/episodes" element={<EpisodesPage />} />
        <Route path="/episode/:id" element={<EpisodePage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
