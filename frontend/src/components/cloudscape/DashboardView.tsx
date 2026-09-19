import React, { useState } from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  Input,
  Button,
  Table,
  Box,
  Badge,
  StatusIndicator,
  ColumnLayout,
  Link,
  FileUpload,
} from '@cloudscape-design/components';
import type { VerificationResponse } from '../../types/api';

export interface CaseRecord {
  id: string;
  query: string;
  batchNo: string;
  drugName: string;
  status: string;
  tier: 'SKILL' | 'REACTIVE' | 'DEEP';
  timestamp: string;
  result: VerificationResponse;
}

interface DashboardViewProps {
  onVerify: (queryText: string, file?: File) => void;
  onInspectCase: (caseItem: CaseRecord) => void;
  isLoading: boolean;
  recentCases: CaseRecord[];
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  onVerify,
  onInspectCase,
  isLoading,
  recentCases,
}) => {
  const [queryText, setQueryText] = useState('');
  const [files, setFiles] = useState<File[]>([]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!queryText.trim() && files.length === 0) return;
    onVerify(queryText.trim(), files[0]);
  };

  const handleSample = (sampleText: string, mockPhoto: boolean = false) => {
    setQueryText(sampleText);
    if (mockPhoto) {
      const blob = new Blob(['mock-packaging'], { type: 'image/jpeg' });
      const f = new File([blob], 'paracetamol_strip.jpg', { type: 'image/jpeg' });
      setFiles([f]);
    } else {
      setFiles([]);
    }
  };

  const getStatusIndicator = (status: string) => {
    switch (status) {
      case 'CLEAR':
        return <StatusIndicator type="success">No Regulatory Flags</StatusIndicator>;
      case 'NSQ':
        return <StatusIndicator type="warning">NSQ Quality Failure</StatusIndicator>;
      case 'SPURIOUS':
        return <StatusIndicator type="error">Spurious / Fake Alert</StatusIndicator>;
      case 'COMMUNITY_FLAGGED':
        return <StatusIndicator type="info">Community Flagged</StatusIndicator>;
      default:
        return <StatusIndicator type="stopped">No Match</StatusIndicator>;
    }
  };

  const getTierBadge = (tier: string) => {
    switch (tier) {
      case 'SKILL':
        return <Badge color="green">Tier 1: Skill</Badge>;
      case 'REACTIVE':
        return <Badge color="blue">Tier 2: Reactive</Badge>;
      case 'DEEP':
        return <Badge color="blue">Tier 3: Deep</Badge>;
      default:
        return <Badge color="grey">Orchestrator</Badge>;
    }
  };

  return (
    <SpaceBetween size="l">
      {/* Page Header */}
      <Header
        variant="h1"
        description="Verify medicine batches, packaging photos, or adverse reactions against official CDSCO regulatory records and real-world community signals."
      >
        Medicine Safety & Authenticity Intelligence
      </Header>

      {/* KPI Overview Cards */}
      <ColumnLayout columns={4} variant="text-grid">
        <Container>
          <Box variant="awsui-key-label">Active Verifications</Box>
          <Box variant="awsui-value-large">{recentCases.length + 14}</Box>
          <Box variant="small" color="text-status-success">
            All tiers operational
          </Box>
        </Container>

        <Container>
          <Box variant="awsui-key-label">CDSCO Flagged Batches</Box>
          <Box variant="awsui-value-large">1,284</Box>
          <Box variant="small" color="text-body-secondary">
            Sourced from CDSCO Gazettes
          </Box>
        </Container>

        <Container>
          <Box variant="awsui-key-label">Spurious / Counterfeit Alerts</Box>
          <Box variant="awsui-value-large">42</Box>
          <Box variant="small" color="text-status-error">
            Critical safety alerts
          </Box>
        </Container>

        <Container>
          <Box variant="awsui-key-label">Community Incident Reports</Box>
          <Box variant="awsui-value-large">18</Box>
          <Box variant="small" color="text-status-info">
            Verified patient signals
          </Box>
        </Container>
      </ColumnLayout>

      {/* Unified Interactive Verification Omnibox */}
      <Container
        header={
          <Header
            variant="h2"
            description="Enter a batch number, composition, or describe symptoms. The Orchestrator automatically selects the best AI agent."
          >
            Verify Medicine / Ask MedVerify
          </Header>
        }
      >
        <SpaceBetween size="m">
          <form onSubmit={handleSubmit}>
            <SpaceBetween size="s">
              <Input
                value={queryText}
                onChange={({ detail }) => setQueryText(detail.value)}
                placeholder="Enter batch number (e.g. B-9021), drug name, or describe an issue/symptom..."
                disabled={isLoading}
                type="search"
                autoFocus
              />

              <FileUpload
                onChange={({ detail }) => setFiles(detail.value)}
                value={files}
                i18nStrings={{
                  uploadButtonText: (e) => (e ? 'Choose files' : 'Attach Packaging Photo'),
                  dropzoneText: (e) => (e ? 'Drop files here' : 'Drop packaging image to verify'),
                  removeFileAriaLabel: (fileIndex) => `Remove file ${fileIndex + 1}`,
                  limitShowFewer: 'Show fewer files',
                  limitShowMore: 'Show more files',
                  errorIconAriaLabel: 'Error',
                }}
                showFileLastModified
                showFileSize
                accept="image/*"
              />

              <Box float="right">
                <Button
                  variant="primary"
                  loading={isLoading}
                  onClick={() => handleSubmit()}
                  disabled={!queryText.trim() && files.length === 0}
                >
                  Verify Medicine
                </Button>
              </Box>
            </SpaceBetween>
          </form>

          {/* Sample Query Chips */}
          <Box>
            <SpaceBetween direction="horizontal" size="xs">
              <Box variant="small" color="text-body-secondary" margin={{ top: 'xxs' }}>
                Quick Samples:
              </Box>
              <Button
                variant="inline-link"
                onClick={() => handleSample('B-9021')}
              >
                Batch B-9021 (NSQ Alert)
              </Button>
              <Button
                variant="inline-link"
                onClick={() => handleSample('SPUR-7788')}
              >
                Batch SPUR-7788 (Spurious Fake)
              </Button>
              <Button
                variant="inline-link"
                onClick={() => handleSample('CLEAN-BATCH-101')}
              >
                Clean Batch Sample
              </Button>
              <Button
                variant="inline-link"
                onClick={() => handleSample('Patient took batch NX102 and developed acute dizziness with blurred vision')}
              >
                Symptom Suspicion (Deep Agent)
              </Button>
              <Button
                variant="inline-link"
                onClick={() => handleSample('Paracetamol 500mg Batch B-9021', true)}
              >
                Packaging Photo Scan (Reactive Agent)
              </Button>
            </SpaceBetween>
          </Box>
        </SpaceBetween>
      </Container>

      {/* Recent Verification Cases Table */}
      <Table
        header={
          <Header
            variant="h2"
            counter={`(${recentCases.length})`}
            description="Historical medicine verification checks performed in this session."
          >
            Recent Verification Cases
          </Header>
        }
        columnDefinitions={[
          {
            id: 'id',
            header: 'Case ID',
            cell: (item) => <Link onFollow={() => onInspectCase(item)}>{item.id}</Link>,
            sortingField: 'id',
          },
          {
            id: 'batchNo',
            header: 'Batch No',
            cell: (item) => (
              <Box variant="code">{item.batchNo || 'N/A'}</Box>
            ),
          },
          {
            id: 'drugName',
            header: 'Drug / Query',
            cell: (item) => item.drugName || item.query,
          },
          {
            id: 'status',
            header: 'Regulatory Status',
            cell: (item) => getStatusIndicator(item.status),
          },
          {
            id: 'tier',
            header: 'Agent Tier',
            cell: (item) => getTierBadge(item.tier),
          },
          {
            id: 'timestamp',
            header: 'Time',
            cell: (item) => item.timestamp,
          },
          {
            id: 'action',
            header: 'Actions',
            cell: (item) => (
              <Button variant="inline-link" onClick={() => onInspectCase(item)}>
                Inspect Case
              </Button>
            ),
          },
        ]}
        items={recentCases}
        empty={
          <Box textAlign="center" color="inherit">
            <b>No verification cases yet</b>
            <Box variant="p" color="inherit">
              Enter a batch number above or attach a photo to run your first check.
            </Box>
          </Box>
        }
      />
    </SpaceBetween>
  );
};
