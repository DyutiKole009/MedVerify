import React from 'react';
import { HelpPanel, Box, SpaceBetween, Alert, Link } from '@cloudscape-design/components';

export const ToolsDrawer: React.FC = () => {
  return (
    <HelpPanel
      header={<h2>About MedVerify Intelligence</h2>}
      footer={
        <Box color="text-body-secondary">
          <Link external href="https://cdsco.gov.in">
            CDSCO Official Portal
          </Link>
        </Box>
      }
    >
      <SpaceBetween size="m">
        <Box variant="p">
          MedVerify lets consumers, pharmacists, and regulatory inspectors verify whether a medicine batch has publicly recorded quality concerns or real-world incident flags.
        </Box>

        <Alert type="warning" header="Core Safety Principle">
          <strong>"Absence of a flag is not proof of safety."</strong>
          <Box variant="p">
            A clean check indicates that no government laboratory has published an alert for this batch. It is not an absolute certificate of authenticity.
          </Box>
        </Alert>

        <Box variant="h4">3-Tier Multi-Agent System</Box>
        <Box variant="p">
          • <strong>Skill Agent (Tier 1):</strong> Deterministic point lookup in DynamoDB for batch numbers in under 500ms.<br />
          • <strong>Reactive Agent (Tier 2):</strong> Multi-modal OCR pipeline extracting batch numbers and expiry from packaging photos.<br />
          • <strong>Deep Agent (Tier 3):</strong> Bounded LangGraph agent searching Bedrock Knowledge Base for precedents and symptoms.
        </Box>
      </SpaceBetween>
    </HelpPanel>
  );
};
