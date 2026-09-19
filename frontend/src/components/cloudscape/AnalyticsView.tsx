import React from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  ColumnLayout,
  Box,
  ProgressBar,
  KeyValuePairs,
} from '@cloudscape-design/components';

export const AnalyticsView: React.FC = () => {
  return (
    <SpaceBetween size="l">
      <Header
        variant="h1"
        description="Operational metrics, agent tier dispatch distribution, and latency indicators across MedVerify multi-tier architecture."
      >
        Multi-Agent System Intelligence & Performance
      </Header>

      <ColumnLayout columns={3}>
        <Container header={<Header variant="h3">Tier 1: Skill Agent</Header>}>
          <SpaceBetween size="s">
            <Box variant="awsui-value-large">74%</Box>
            <Box variant="small" color="text-body-secondary">
              Of all incoming queries routed to deterministic DynamoDB lookup
            </Box>
            <ProgressBar value={74} />
            <KeyValuePairs
              columns={2}
              items={[
                { label: 'Avg Latency', value: '18 ms' },
                { label: 'Compute Cost', value: '$0.00001' },
              ]}
            />
          </SpaceBetween>
        </Container>

        <Container header={<Header variant="h3">Tier 2: Reactive Agent</Header>}>
          <SpaceBetween size="s">
            <Box variant="awsui-value-large">18%</Box>
            <Box variant="small" color="text-body-secondary">
              Packaging photos routed through 5-step Step Functions pipeline
            </Box>
            <ProgressBar value={18} status="in-progress" />
            <KeyValuePairs
              columns={2}
              items={[
                { label: 'Avg Latency', value: '1.4 s' },
                { label: 'OCR Accuracy', value: '96.2%' },
              ]}
            />
          </SpaceBetween>
        </Container>

        <Container header={<Header variant="h3">Tier 3: Deep Agent</Header>}>
          <SpaceBetween size="s">
            <Box variant="awsui-value-large">8%</Box>
            <Box variant="small" color="text-body-secondary">
              Ambiguous / adverse symptom queries routed to Bedrock Knowledge Base
            </Box>
            <ProgressBar value={8} />
            <KeyValuePairs
              columns={2}
              items={[
                { label: 'Avg Latency', value: '3.8 s' },
                { label: 'Max Iterations', value: '5 (Bounded)' },
              ]}
            />
          </SpaceBetween>
        </Container>
      </ColumnLayout>

      <Container
        header={
          <Header
            variant="h2"
            description="Knowledge Base growth through feedback-gated reinforcement."
          >
            RAG Knowledge Base Promotion Metrics
          </Header>
        }
      >
        <KeyValuePairs
          columns={4}
          items={[
            { label: 'Total Verified Sessions', value: '342' },
            { label: 'Positive Feedback Rate', value: '94.6%' },
            { label: 'Promoted to Bedrock KB', value: '118 Sessions' },
            { label: 'Hallucination Rate', value: '0.0% (Gated)' },
          ]}
        />
      </Container>
    </SpaceBetween>
  );
};
