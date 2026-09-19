import { useState } from 'react';
import AppLayout from '@cloudscape-design/components/app-layout';
import { TopNav } from './components/cloudscape/TopNav';
import { Navigation } from './components/cloudscape/Navigation';
import { DashboardView } from './components/cloudscape/DashboardView';
import type { CaseRecord } from './components/cloudscape/DashboardView';
import { CaseDetailView } from './components/cloudscape/CaseDetailView';
import { DocumentsView } from './components/cloudscape/DocumentsView';
import { ReportsView } from './components/cloudscape/ReportsView';
import { AnalyticsView } from './components/cloudscape/AnalyticsView';
import { ToolsDrawer } from './components/cloudscape/ToolsDrawer';
import { submitVerification } from './services/api';
import type { VerificationResponse } from './types/api';

const DEFAULT_CASES: CaseRecord[] = [
  {
    id: 'MV-1024',
    query: 'B-9021',
    batchNo: 'B-9021',
    drugName: 'Paracetamol 500mg',
    status: 'NSQ',
    tier: 'SKILL',
    timestamp: 'Just now',
    result: {
      session_id: '8f03c0b2-4d29-4d6b-9c7a-9a9446f25dc1',
      status_category: 'NSQ',
      summary: 'Fails dissolution and assay standards according to CDSCO May 2024 Gazette.',
      disclaimer: 'Absence of a flag is not proof of safety.',
      orchestrator_tier: 'SKILL',
      orchestrator_reasoning: 'Direct batch check without image upload.',
      community_flag: false,
      community_report_count: 0,
      official_record: {
        batch_no: 'B-9021',
        drug_name: 'Paracetamol 500mg',
        manufacturer_name: 'Acme Pharmaceuticals Ltd, Plot 14, Solan (HP)',
        alert_status: 'NSQ',
        nsq_reason: 'Fails dissolution test (active ingredient release below standard limits)',
        source_month: '2024-05',
        source_document_s3_key: 'notices/2024-05-central.pdf',
      },
    },
  },
  {
    id: 'MV-1023',
    query: 'SPUR-7788',
    batchNo: 'SPUR-7788',
    drugName: 'Amoxicillin 250mg Capsules',
    status: 'SPURIOUS',
    tier: 'REACTIVE',
    timestamp: '15 min ago',
    result: {
      session_id: '3c19b882-9912-4aa1-8012-781912882319',
      status_category: 'SPURIOUS',
      summary: 'Manufactured by fictitious entity; declared spurious counterfeit medicine by regulatory authorities.',
      disclaimer: 'Absence of a flag is not proof of safety.',
      orchestrator_tier: 'REACTIVE',
      orchestrator_reasoning: 'Packaging photo analysis detected invalid licensing number.',
      community_flag: true,
      community_report_count: 3,
      official_record: {
        batch_no: 'SPUR-7788',
        drug_name: 'Amoxicillin 250mg Capsules',
        manufacturer_name: 'Non-Existent Fictitious Laboratories, Roorkee',
        alert_status: 'SPURIOUS',
        nsq_reason: 'Product does not contain stated active pharmaceutical ingredient (spurious)',
        source_month: '2024-04',
      },
    },
  },
  {
    id: 'MV-1022',
    query: 'CLEAN-101',
    batchNo: 'CLEAN-101',
    drugName: 'Pantoprazole Gastro-Resistant Tablets',
    status: 'CLEAR',
    tier: 'SKILL',
    timestamp: '1 hr ago',
    result: {
      session_id: '1a902188-7712-4e99-b102-441092817291',
      status_category: 'CLEAR',
      summary: 'No regulatory quality alert or spurious flag recorded in CDSCO repository.',
      disclaimer: 'Absence of a flag is not proof of safety.',
      orchestrator_tier: 'SKILL',
      orchestrator_reasoning: 'Single deterministic lookup completed.',
      community_flag: false,
      community_report_count: 0,
      official_record: null,
    },
  },
];

export function App() {
  const [activeNav, setActiveNav] = useState('#dashboard');
  const [selectedCase, setSelectedCase] = useState<CaseRecord | null>(null);
  const [cases, setCases] = useState<CaseRecord[]>(DEFAULT_CASES);
  const [isLoading, setIsLoading] = useState(false);
  const [isToolsOpen, setIsToolsOpen] = useState(false);

  const handleVerify = async (queryText: string, file?: File) => {
    setIsLoading(true);
    try {
      const result: VerificationResponse = await submitVerification({
        text: queryText,
        imageFile: file,
        batchNo: queryText && queryText.length <= 15 ? queryText : undefined,
      });

      const newCase: CaseRecord = {
        id: `MV-${1025 + cases.length}`,
        query: queryText || file?.name || 'Inspection',
        batchNo: result.official_record?.batch_no || (queryText.length <= 15 ? queryText : 'Extracted'),
        drugName: result.official_record?.drug_name || queryText || 'Packaging Scan',
        status: result.status_category,
        tier: result.orchestrator_tier,
        timestamp: 'Just now',
        result,
      };

      setCases([newCase, ...cases]);
      setSelectedCase(newCase);
    } catch (err) {
      console.error('Verification error:', err);
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
      <TopNav onNavigate={(href) => setActiveNav(href)} />

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

export default App;
