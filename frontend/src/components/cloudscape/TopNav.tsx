import React from 'react';
import TopNavigation from '@cloudscape-design/components/top-navigation';
import { getAnonymousId } from '../../services/session';

interface TopNavProps {
  onNavigate?: (href: string) => void;
}

export const TopNav: React.FC<TopNavProps> = ({ onNavigate }) => {
  const anonId = getAnonymousId().slice(0, 13) + '...';

  return (
    <TopNavigation
      identity={{
        href: '#dashboard',
        title: 'MedVerify',
        logo: {
          src: 'https://img.icons8.com/color/96/shield-check.png',
          alt: 'MedVerify Logo',
        },
        onFollow: (e) => {
          e.preventDefault();
          onNavigate?.('#dashboard');
        },
      }}
      utilities={[
        {
          type: 'button',
          text: 'CDSCO Gazette',
          href: 'https://cdsco.gov.in/opencms/opencms/en/Notifications/nsq-drugs/',
          external: true,
          externalIconAriaLabel: 'Opens in a new tab',
        },
        {
          type: 'menu-dropdown',
          text: anonId,
          description: 'Anonymous Client Session',
          iconName: 'user-profile',
          items: [
            { id: 'role', text: 'Role: Consumer / Anonymous' },
            { id: 'session', text: `Client: ${getAnonymousId()}` },
          ],
        },
      ]}
      i18nStrings={{
        searchIconAriaLabel: 'Search',
        searchDismissIconAriaLabel: 'Close search',
        overflowMenuTriggerText: 'More',
      }}
    />
  );
};
