import { useState } from 'react';
import AppLayout from '@cloudscape-design/components/app-layout';
import Alert from '@cloudscape-design/components/alert';
import { TopNav } from './components/cloudscape/TopNav';
import { Navigation } from './components/cloudscape/Navigation';
import { DashboardView } from './components/cloudscape/DashboardView';
import type { CaseRecord } from './components/cloudscape/DashboardView';
import { CaseDetailView } from './components/cloudscape/CaseDetailView';
import { DocumentsView } from './components/cloudscape/DocumentsView';
import { ReportsView } from './components/cloudscape/ReportsView';
import { AnalyticsView } from './components/cloudscape/AnalyticsView';
import { ToolsDrawer } from './components/cloudscape/ToolsDrawer';
import { AuthModal } from './components/AuthModal';
import { AuthPage } from './components/AuthPage';
import { AuthProvider, useAuth } from './context/AuthContext';
import { submitVerification } from './services/api';
import type { VerificationResponse } from './types/api';

function AppContent() {
  const { isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const [guestAccess, setGuestAccess] = useState(false);

  const [activeNav, setActiveNav] = useState('#dashboard');
  const [selectedCase, setSelectedCase] = useState<CaseRecord | null>(null);
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isToolsOpen, setIsToolsOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // If user is not logged in and hasn't opted for guest access, show AuthPage first
  if (isAuthLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center text-white">
        <div className="flex flex-col items-center space-y-3">
          <div className="w-10 h-10 border-4 border-sky-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm font-medium text-slate-300">Loading MedVerify Workspace...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated && !guestAccess) {
    return <AuthPage onContinueAsGuest={() => setGuestAccess(true)} />;
  }

  const handleVerify = async (queryText: string, file?: File) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const result: VerificationResponse = await submitVerification({
        text: queryText,
        imageFile: file,
        batchNo: queryText && queryText.length <= 15 ? queryText : undefined,
      });

      const localImageUrl = file ? URL.createObjectURL(file) : undefined;
      const enrichedResult: VerificationResponse = {
        ...result,
        image_url: result.image_url || localImageUrl,
        input_type: file ? 'IMAGE' : 'TEXT',
      };

      const newCase: CaseRecord = {
        id: result.session_id,
        query: queryText || file?.name || 'Inspection',
        batchNo: result.official_record?.batch_no || (queryText.length <= 15 ? queryText : 'N/A'),
        drugName: result.official_record?.drug_name || queryText || 'Packaging Scan',
        status: result.status_category,
        tier: result.orchestrator_tier,
        timestamp: new Date().toISOString(),
        imageUrl: localImageUrl,
        result: enrichedResult,
      };

      setCases((prev) => [newCase, ...prev]);
      setSelectedCase(newCase);
    } catch (err: any) {
      console.error('Verification error:', err);
      setErrorMessage(err?.message || 'Verification request failed. Please check network connection.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleInspectCase = (c: CaseRecord) => {
    setSelectedCase(c);
  };

  const handleBackToDashboard = () => {
    setSelectedCase(null);
    setActiveNav('#dashboard');
  };

  const renderContent = () => {
    if (selectedCase) {
      return (
        <CaseDetailView
          caseId={selectedCase.id}
          result={selectedCase.result}
          onBack={handleBackToDashboard}
          onOpenReportModal={() => setActiveNav('#new-report')}
        />
      );
    }

    switch (activeNav) {
      case '#notices':
        return <DocumentsView />;
      case '#reports':
        return <ReportsView isModalOpen={false} />;
      case '#new-report':
        return <ReportsView isModalOpen={true} onCloseModal={() => setActiveNav('#reports')} />;
      case '#analytics':
        return <AnalyticsView />;
      case '#verify':
      case '#cases':
      case '#dashboard':
      default:
        return (
          <DashboardView
            onVerify={handleVerify}
            onInspectCase={handleInspectCase}
            isLoading={isLoading}
            recentCases={cases}
          />
        );
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <TopNav
        onNavigate={(href) => setActiveNav(href)}
        onSignOut={() => setGuestAccess(false)}
      />
      <AuthModal />

      <AppLayout
        navigation={
          <Navigation
            activeHref={activeNav}
            onFollow={(href) => {
              setSelectedCase(null);
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
