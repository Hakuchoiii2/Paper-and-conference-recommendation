import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { SystemProvider } from './context/SystemContext';
import { AnalysisResultPage } from './pages/AnalysisResultPage';
import { ComparePage } from './pages/ComparePage';
import { ConferenceDetailPage } from './pages/ConferenceDetailPage';
import { ExplorePage } from './pages/ExplorePage';
import { ExplorePaperDetailPage } from './pages/ExplorePaperDetailPage';
import { InputPage } from './pages/InputPage';
import { PaperDetailPage } from './pages/PaperDetailPage';

export function App() {
  return (
    <SystemProvider>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<ExplorePage />} />
            <Route path="/explore/papers/:paperId" element={<ExplorePaperDetailPage />} />
            <Route path="/analyze" element={<InputPage />} />
            <Route path="/analyses/:analysisId" element={<AnalysisResultPage />} />
            <Route
              path="/analyses/:analysisId/papers/:paperId"
              element={<PaperDetailPage />}
            />
            <Route
              path="/analyses/:analysisId/conferences/:conferenceId"
              element={<ConferenceDetailPage />}
            />
            <Route path="/compare" element={<ComparePage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </SystemProvider>
  );
}

export default App;
