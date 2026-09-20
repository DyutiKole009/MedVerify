import { useState } from 'react';
import AppLayout from '@cloudscape-design/components/app-layout';
import Alert from '@cloudscape-design/components/alert';
import { TopNav } from './components/cloudscape/TopNav';
import { Navigation } from './components/cloudscape/Navigation';
import type { CaseRecord } from './components/cloudscape/DashboardView';
import { DocumentsView } from './components/cloudscape/DocumentsView';
import { ReportsView } from './components/cloudscape/ReportsView';
import { AnalyticsView } from './components/cloudscape/AnalyticsView';
import { ToolsDrawer } from './components/cloudscape/ToolsDrawer';
import { AuthModal } from './components/AuthModal';
import { AuthPage } from './components/AuthPage';
import { ChatInterface } from './components/cloudscape/ChatInterface';
import { AuthProvider, useAuth } from './context/AuthContext';

function AppContent() {
  const { isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const [guestAccess, setGuestAccess] = useState(false);

  const [activeNav, setActiveNav] = useState('#dashboard');
  const [cases] = useState<CaseRecord[]>([]);
  const [isToolsOpen, setIsToolsOpen] = useState(false);
  const [isRecallsOpen, setIsRecallsOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // If user is not logged in and hasn't opted for guest access, show AuthPage first
  if (isAuthLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center text-white font-sans">
        <div className="flex flex-col items-center space-y-3">
          <div className="w-10 h-10 border-4 border-sky-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm font-medium text-slate-300 font-mono">Loading MedVerify CDSCO Workspace...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated && !guestAccess) {
    return <AuthPage onContinueAsGuest={() => setGuestAccess(true)} />;
  }

  const renderContent = () => {
    switch (activeNav) {
      case '#notices':
        return <DocumentsView />;
      case '#reports':
        return <ReportsView isModalOpen={false} />;
      case '#new-report':
        return <ReportsView isModalOpen={true} onCloseModal={() => setActiveNav('#reports')} />;
      case '#analytics':
        return <AnalyticsView />;
      case '#cases':
      case '#verify':
      case '#dashboard':
      default:
        return (
          <ChatInterface
            initialCases={cases}
            isRecallsDrawerOpen={isRecallsOpen}
            onCloseRecallsDrawer={() => setIsRecallsOpen(false)}
          />
        );
    }
  };

  const isChatView = ['#dashboard', '#verify', '#cases'].includes(activeNav);

  if (isChatView) {
    return (
      <div className="h-screen flex flex-col bg-[#f8fafc] overflow-hidden">
        <TopNav
          onNavigate={(href) => setActiveNav(href)}
          onOpenAlerts={() => setIsRecallsOpen(true)}
          onNewSession={() => setActiveNav('#dashboard')}
          onSignOut={() => setGuestAccess(false)}
        />
        <AuthModal />
        <div className="flex-1 overflow-hidden">
          <ChatInterface
            initialCases={cases}
            isRecallsDrawerOpen={isRecallsOpen}
            onCloseRecallsDrawer={() => setIsRecallsOpen(false)}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f8fafc]">
      <TopNav
        onNavigate={(href) => setActiveNav(href)}
        onOpenAlerts={() => setIsRecallsOpen(true)}
        onSignOut={() => setGuestAccess(false)}
      />
      <AuthModal />

      <AppLayout
        navigation={
          <Navigation
            activeHref={activeNav}
            onFollow={(href) => {
              setActiveNav(href);
            }}
          />
        }
        notifications={
          errorMessage ? (
            <Alert
              type="error"
              dismissible
              onDismiss={() => setErrorMessage(null)}
              header="Verification Error"
            >
              {errorMessage}
            </Alert>
          ) : null
        }
        content={renderContent()}
        tools={<ToolsDrawer />}
        toolsOpen={isToolsOpen}
        onToolsChange={({ detail }) => setIsToolsOpen(detail.open)}
        headerSelector="#top-nav"
        contentType="default"
      />
    </div>
  );
}

export function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
