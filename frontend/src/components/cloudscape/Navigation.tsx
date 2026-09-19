import SideNavigation from '@cloudscape-design/components/side-navigation';
import type { SideNavigationProps } from '@cloudscape-design/components/side-navigation';

interface NavigationProps {
  activeHref: string;
  onFollow: (href: string) => void;
}

export const Navigation: React.FC<NavigationProps> = ({ activeHref, onFollow }) => {
  const items: SideNavigationProps.Item[] = [
    { type: 'link', text: 'Dashboard', href: '#dashboard' },
    {
      type: 'section',
      text: 'Case Management',
      items: [
        { type: 'link', text: 'Recent Verifications', href: '#cases' },
        { type: 'link', text: 'New Verification', href: '#verify' },
      ],
    },
    {
      type: 'section',
      text: 'Knowledge Base',
      items: [
        { type: 'link', text: 'CDSCO Regulatory Notices', href: '#notices' },
        { type: 'link', text: 'Flagged Manufacturers', href: '#manufacturers' },
      ],
    },
    {
      type: 'section',
      text: 'Community Safety',
      items: [
        { type: 'link', text: 'Community Signals', href: '#reports' },
        { type: 'link', text: 'File a Report', href: '#new-report' },
      ],
    },
    {
      type: 'section',
      text: 'System Intelligence',
      items: [
        { type: 'link', text: 'Multi-Agent Analytics', href: '#analytics' },
      ],
    },
  ];

  return (
    <SideNavigation
      activeHref={activeHref}
      header={{ href: '#dashboard', text: 'MedVerify Workspace' }}
      items={items}
      onFollow={(event) => {
        if (!event.detail.external) {
          event.preventDefault();
          onFollow(event.detail.href);
        }
      }}
    />
  );
};
