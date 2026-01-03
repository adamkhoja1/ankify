import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom';
import './index.css';
import GeneratePage from './pages/GeneratePage';
import ReviewPage from './pages/ReviewPage';
import SessionsPage from './pages/SessionsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen flex flex-col">
          {/* Navigation */}
          <nav className="border-b bg-card">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between h-16">
                <div className="flex">
                  <Link to="/" className="flex items-center px-2 text-lg font-semibold text-primary">
                    🎴 Ankification
                  </Link>
                  <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                    <NavLink to="/">Review</NavLink>
                    <NavLink to="/generate">Generate</NavLink>
                    <NavLink to="/sessions">Sessions</NavLink>
                  </div>
                </div>
              </div>
            </div>
          </nav>

          {/* Main content */}
          <main className="flex-1">
            <Routes>
              <Route path="/" element={<ReviewPage />} />
              <Route path="/generate" element={<GeneratePage />} />
              <Route path="/sessions" element={<SessionsPage />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

function NavLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <Link
      to={to}
      className="inline-flex items-center px-1 pt-1 border-b-2 border-transparent text-sm font-medium text-muted-foreground hover:text-foreground hover:border-border transition-colors"
    >
      {children}
    </Link>
  );
}

export default App;
