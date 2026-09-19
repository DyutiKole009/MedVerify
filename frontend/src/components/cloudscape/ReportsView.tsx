import React, { useState } from 'react';
import {
  Table,
  Header,
  SpaceBetween,
  Button,
  Badge,
  Box,
  Modal,
  FormField,
  Input,
  Select,
  Textarea,
  StatusIndicator,
} from '@cloudscape-design/components';
import { submitCommunityReport } from '../../services/api';

interface ReportsViewProps {
  isModalOpen?: boolean;
  onCloseModal?: () => void;
  defaultBatchNo?: string;
}

export const ReportsView: React.FC<ReportsViewProps> = ({
  isModalOpen = false,
  onCloseModal,
  defaultBatchNo = '',
}) => {
  const [modalVisible, setModalVisible] = useState(isModalOpen);
  const [batchNo, setBatchNo] = useState(defaultBatchNo);
  const [drugName, setDrugName] = useState('');
  const [issueType, setIssueType] = useState<{ label: string; value: string }>({
    label: 'Suspected Counterfeit / Fake',
    value: 'SUSPECTED_COUNTERFEIT',
  });
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);

  // Sync external modal trigger
  React.useEffect(() => {
    setModalVisible(isModalOpen);
  }, [isModalOpen]);

  const reports = [
    {
      id: 'REP-901',
      batchNo: 'B-9021',
      drugName: 'Paracetamol 500mg',
      issueType: 'PACKAGING_DEFECT',
      description: 'The blister strip foil is loose and text on the back is misaligned.',
      date: '2024-05-18',
      status: 'VERIFIED',
    },
    {
      id: 'REP-902',
      batchNo: 'SPUR-7788',
      drugName: 'Amoxicillin 250mg',
      issueType: 'SUSPECTED_COUNTERFEIT',
      description: 'Tablets crumbled into white powder with abnormal acidic smell upon opening.',
      date: '2024-05-15',
      status: 'FLAGGED',
    },
    {
      id: 'REP-903',
      batchNo: 'NX102',
      drugName: 'Cough Syrup 100ml',
      issueType: 'ADVERSE_REACTION',
      description: 'Severe throat irritation and rash reported within 30 minutes of dosage.',
      date: '2024-05-11',
      status: 'INVESTIGATING',
    },
  ];

  const handleClose = () => {
    setModalVisible(false);
    onCloseModal?.();
  };

  const handleSubmit = async () => {
    if (!description.trim()) return;
    setIsSubmitting(true);
    await submitCommunityReport({
      batch_no: batchNo.trim() || undefined,
      drug_name: drugName.trim() || undefined,
      issue_type: issueType.value,
      description: description.trim(),
    });
    setIsSubmitting(false);
    setSubmitSuccess(true);
    setTimeout(() => {
      setSubmitSuccess(false);
      handleClose();
    }, 1500);
  };

  return (
    <SpaceBetween size="l">
      <Header
        variant="h1"
        description="Crowd-sourced real-world issues, adverse reactions, and packaging defect signals submitted by consumers and registered pharmacists."
        actions={
          <Button variant="primary" onClick={() => setModalVisible(true)}>
            File Incident Report
          </Button>
        }
      >
        Community Safety Intelligence & Incident Reports
      </Header>

      <Table
        columnDefinitions={[
          {
            id: 'id',
            header: 'Report ID',
            cell: (item) => <Box variant="code">{item.id}</Box>,
          },
          {
            id: 'batchNo',
            header: 'Batch ID',
            cell: (item) => <Box variant="strong">{item.batchNo}</Box>,
          },
          {
            id: 'drugName',
            header: 'Drug Name',
            cell: (item) => item.drugName,
          },
          {
            id: 'issueType',
            header: 'Report Category',
            cell: (item) => (
              <Badge color={item.issueType === 'SUSPECTED_COUNTERFEIT' ? 'red' : 'blue'}>
                {item.issueType.replace('_', ' ')}
              </Badge>
            ),
          },
          {
            id: 'description',
            header: 'Description & Symptoms',
            cell: (item) => item.description,
          },
          {
            id: 'status',
            header: 'Status',
            cell: (item) => (
              <StatusIndicator type={item.status === 'VERIFIED' ? 'success' : 'warning'}>
                {item.status}
              </StatusIndicator>
            ),
          },
          {
            id: 'date',
            header: 'Date Logged',
            cell: (item) => item.date,
          },
        ]}
        items={reports}
      />

      {/* Cloudscape Report Submission Modal */}
      <Modal
        visible={modalVisible}
        onDismiss={handleClose}
        header="Submit Medicine Incident Report"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button variant="link" onClick={handleClose}>
                Cancel
              </Button>
              <Button
                variant="primary"
                loading={isSubmitting}
                onClick={handleSubmit}
                disabled={!description.trim()}
              >
                Submit Report
              </Button>
            </SpaceBetween>
          </Box>
        }
      >
        {submitSuccess ? (
          <Box textAlign="center" padding={{ vertical: 'l' }}>
            <StatusIndicator type="success">
              Report successfully recorded in community safety registry.
            </StatusIndicator>
          </Box>
        ) : (
          <SpaceBetween size="m">
            <FormField label="Batch Number" description="Batch printed on strip or outer carton">
              <Input
                value={batchNo}
                onChange={({ detail }) => setBatchNo(detail.value)}
                placeholder="e.g. B-9021"
              />
            </FormField>

            <FormField label="Medicine Name" description="Brand or generic composition">
              <Input
                value={drugName}
                onChange={({ detail }) => setDrugName(detail.value)}
                placeholder="e.g. Paracetamol 500mg"
              />
            </FormField>

            <FormField label="Issue Category">
              <Select
                selectedOption={issueType}
                onChange={({ detail }) =>
                  setIssueType(detail.selectedOption as { label: string; value: string })
                }
                options={[
                  { label: 'Suspected Counterfeit / Fake', value: 'SUSPECTED_COUNTERFEIT' },
                  { label: 'Packaging / Label Print Flaw', value: 'PACKAGING_DEFECT' },
                  { label: 'Unexpected Adverse Reaction', value: 'ADVERSE_REACTION' },
                  { label: 'Lack of Therapeutic Effect', value: 'INEFFECTIVE' },
                ]}
              />
            </FormField>

            <FormField
              label="Description & Clinical Observations"
              description="Describe physical anomalies, symptoms experienced, or packaging defects"
            >
              <Textarea
                value={description}
                onChange={({ detail }) => setDescription(detail.value)}
                placeholder="Provide details on tablets, smell, packaging defects, or symptoms..."
                rows={3}
              />
            </FormField>
          </SpaceBetween>
        )}
      </Modal>
    </SpaceBetween>
  );
};
