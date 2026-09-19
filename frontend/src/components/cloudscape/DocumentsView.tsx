import React from 'react';
import {
  Table,
  Header,
  SpaceBetween,
  Button,
  Badge,
  Box,
  Link,
} from '@cloudscape-design/components';

export const DocumentsView: React.FC = () => {
  const documents = [
    {
      id: 'DOC-2024-05-CENTRAL',
      month: '2024-05',
      name: 'CDSCO Central Drugs Laboratory Monthly NSQ Gazette',
      type: 'CENTRAL',
      batchesFlagged: 48,
      spuriousCount: 3,
      url: 'https://cdsco.gov.in/opencms/opencms/en/Notifications/nsq-drugs/',
    },
    {
      id: 'DOC-2024-04-STATE',
      month: '2024-04',
      name: 'State Drugs Testing Laboratory Alerts (Maharashtra & Gujarat)',
      type: 'STATE',
      batchesFlagged: 31,
      spuriousCount: 1,
      url: 'https://cdsco.gov.in/opencms/opencms/en/Notifications/nsq-drugs/',
    },
    {
      id: 'DOC-2024-03-CENTRAL',
      month: '2024-03',
      name: 'Central Drugs Laboratory Quality Evaluation Summary',
      type: 'CENTRAL',
      batchesFlagged: 54,
      spuriousCount: 4,
      url: 'https://cdsco.gov.in/opencms/opencms/en/Notifications/nsq-drugs/',
    },
    {
      id: 'DOC-2024-02-CENTRAL',
      month: '2024-02',
      name: 'CDSCO National Spurious Medicine Alert Notice',
      type: 'CENTRAL',
      batchesFlagged: 27,
      spuriousCount: 7,
      url: 'https://cdsco.gov.in/opencms/opencms/en/Notifications/nsq-drugs/',
    },
  ];

  return (
    <SpaceBetween size="l">
      <Header
        variant="h1"
        description="Ingested Central Drugs Standard Control Organisation (CDSCO) gazette publications and quality failure documents stored in S3."
        actions={
          <Button
            href="https://cdsco.gov.in/opencms/opencms/en/Notifications/nsq-drugs/"
            external
          >
            Visit Official CDSCO Portal
          </Button>
        }
      >
        Regulatory Quality Notices & Gazette Archives
      </Header>

      <Table
        columnDefinitions={[
          {
            id: 'month',
            header: 'Gazette Month',
            cell: (item) => <Box variant="strong">{item.month}</Box>,
            sortingField: 'month',
          },
          {
            id: 'name',
            header: 'Document Description',
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
            id: 'batchesFlagged',
            header: 'Flagged Batches',
            cell: (item) => `${item.batchesFlagged} Batches`,
          },
          {
            id: 'spuriousCount',
            header: 'Spurious Alerts',
            cell: (item) => (
              <Badge color={item.spuriousCount > 0 ? 'red' : 'grey'}>
                {item.spuriousCount} Spurious
              </Badge>
            ),
          },
          {
            id: 'action',
            header: 'Action',
            cell: (item) => (
              <Link href={item.url} external>
                View Source
              </Link>
            ),
          },
        ]}
        items={documents}
      />
    </SpaceBetween>
  );
};
