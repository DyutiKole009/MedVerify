import React, { useState, useEffect } from 'react';
import {
  Table,
  Header,
  SpaceBetween,
  Button,
  Badge,
  Box,
  Link,
  Alert,
} from '@cloudscape-design/components';
import { getRegulatoryNotices, triggerWebScraper } from '../../services/api';

interface NoticeItem {
  id: string;
  month: string;
  name: string;
  type: string;
  batchesFlagged: number;
  spuriousCount: number;
  url: string;
  status: 'INGESTED' | 'DISCOVERED_CANDIDATE';
  docHash: string;
}

export const DocumentsView: React.FC = () => {
  const [documents, setDocuments] = useState<NoticeItem[]>([]);
  const [isScraping, setIsScraping] = useState(false);
  const [scrapeSuccess, setScrapeSuccess] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    loadNotices();
  }, []);

  const loadNotices = async () => {
    try {
      const docs = await getRegulatoryNotices();
      setDocuments(docs);
    } catch {
      // Keep empty if failed
    }
  };

  const handleRunScraper = async () => {
    setIsScraping(true);
    setScrapeSuccess(null);
    setErrorMsg(null);
    try {
      const res = await triggerWebScraper();
      const newCandidates: NoticeItem[] = res.candidates || [];

      setDocuments((prev) => {
        // Merge without duplicating docHash
        const existingHashes = new Set(prev.map((d) => d.docHash));
        const added = newCandidates.filter((c) => !existingHashes.has(c.docHash));
        return [...added, ...prev];
      });

      setScrapeSuccess(
        `Web Scraper successfully queried cdsco.gov.in: ${res.count} alert document(s) discovered, cataloged with SHA-256 hash, and classified.`
      );
    } catch (err: any) {
      setErrorMsg(err.message || 'Scraper encountered an error reaching CDSCO portal.');
    } finally {
      setIsScraping(false);
    }
  };

  return (
    <SpaceBetween size="l">
      <Header
        variant="h1"
        description="Central Drugs Standard Control Organisation (CDSCO) gazette publications, monthly quality alerts, and live web scraper pipeline."
        actions={
          <SpaceBetween direction="horizontal" size="xs">
            <Button
              variant="primary"
              iconName="search"
              loading={isScraping}
              onClick={handleRunScraper}
            >
              Run CDSCO Live Scraper
            </Button>
            <Button
              href="https://cdsco.gov.in/opencms/opencms/en/Notifications/nsq-drugs/"
              external
            >
              Visit Official CDSCO Portal
            </Button>
          </SpaceBetween>
        }
      >
        Regulatory Quality Notices & Gazette Archives
      </Header>

      {scrapeSuccess && (
        <Alert
          type="success"
          dismissible
          onDismiss={() => setScrapeSuccess(null)}
          header="Web Scraper Run Completed"
        >
          {scrapeSuccess}
        </Alert>
      )}

      {errorMsg && (
        <Alert
          type="error"
          dismissible
          onDismiss={() => setErrorMsg(null)}
          header="Scraper Error"
        >
          {errorMsg}
        </Alert>
      )}

      <Table
        header={
          <Header
            variant="h2"
            counter={`(${documents.length})`}
            description="Official gazettes scraped and cataloged in the MedVerify pipeline."
          >
            Cataloged Alert Documents
          </Header>
        }
        columnDefinitions={[
          {
            id: 'month',
            header: 'Gazette Month',
            cell: (item) => <Box variant="strong">{item.month}</Box>,
            sortingField: 'month',
          },
          {
            id: 'name',
            header: 'Document Description / Title',
            cell: (item) => item.name,
          },
          {
            id: 'type',
            header: 'Jurisdiction',
            cell: (item) => (
              <Badge color={item.type === 'CENTRAL' ? 'blue' : 'green'}>
                {item.type}
              </Badge>
            ),
          },
          {
            id: 'status',
            header: 'Pipeline Status',
            cell: (item) => (
              <Badge color={item.status === 'INGESTED' ? 'green' : 'severity-medium'}>
                {item.status === 'INGESTED' ? 'INGESTED IN DB' : 'CANDIDATE DISCOVERED'}
              </Badge>
            ),
          },
          {
            id: 'docHash',
            header: 'Deduplication Hash (SHA-256)',
            cell: (item) => (
              <Box variant="code">
                {item.docHash ? `${item.docHash.substring(0, 14)}...` : 'N/A'}
              </Box>
            ),
          },
          {
            id: 'action',
            header: 'Action',
            cell: (item) => (
              <Link href={item.url} external>
                View Source Link
              </Link>
            ),
          },
        ]}
        items={documents}
        empty={
          <Box textAlign="center" color="inherit">
            <b>No documents found</b>
            <Box variant="p" color="inherit">
              Click &quot;Run CDSCO Live Scraper&quot; above to query the CDSCO portal.
            </Box>
          </Box>
        }
      />
    </SpaceBetween>
  );
};
