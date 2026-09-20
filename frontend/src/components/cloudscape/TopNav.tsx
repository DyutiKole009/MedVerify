import React from 'react';
import TopNavigation from '@cloudscape-design/components/top-navigation';
import { getAnonymousId } from '../../services/session';
import { useAuth } from '../../context/AuthContext';

interface TopNavProps {
  onNavigate?: (href: string) => void;
  onSignOut?: () => void;
}

export const TopNav: React.FC<TopNavProps> = ({ onNavigate, onSignOut }) => {
  const { user, isAuthenticated, logout, openModal } = useAuth();
  const anonId = getAnonymousId().slice(0, 13) + '...';

  const utilities: any[] = [
    {
      type: 'button',
      text: 'CDSCO Gazette',
      href: 'https://cdsco.gov.in/opencms/opencms/en/Notifications/nsq-drugs/',
      external: true,
      externalIconAriaLabel: 'Opens in a new tab',
    },
  ];

  if (!isAuthenticated) {
    utilities.push(
      {
        type: 'button',
        text: 'Sign In',
        onClick: () => openModal('login'),
      },
      {
        type: 'button',
        text: 'Register',
        variant: 'primary-button',
        onClick: () => openModal('signup'),
      }
    );
  } else {
    utilities.push({
      type: 'menu-dropdown',
      text: user?.name || user?.email || 'Authenticated User',
      description: `Role: ${user?.role === 'pharmacist' ? 'Licensed Pharmacist' : user?.role === 'admin' ? 'Administrator' : 'Patient / Consumer'}`,
      iconName: 'user-profile',
      onItemClick: (e: any) => {
        if (e.detail.id === 'signout') {
          logout();
          onSignOut?.();
        }
      },
      items: [
        { id: 'role-info', text: `Role: ${user?.role?.toUpperCase()}` },
        { id: 'email-info', text: user?.email || 'Cognito User' },
        { id: 'divider', text: '-' },
        { id: 'signout', text: 'Sign Out' },
      ],
    });
  }

  // Anonymous Client Indicator
  utilities.push({
    type: 'button',
    text: `Client: ${anonId}`,
    disabled: true,
  });

  return (
    <TopNavigation
      identity={{
        href: '#dashboard',
        title: 'MedVerify',
        logo: {
          src: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%230284c7"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z"/></svg>',
          alt: 'MedVerify Logo',
        },
        onFollow: (e) => {
          e.preventDefault();
          onNavigate?.('#dashboard');
        },
      }}
      utilities={utilities}
      i18nStrings={{
        searchIconAriaLabel: 'Search',
        searchDismissIconAriaLabel: 'Close search',
        overflowMenuTriggerText: 'More',
      }}
    />
  );
};
