import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { getAnonymousId } from '../../services/session';

interface TopNavProps {
  onNewSession?: () => void;
  onOpenAlerts?: () => void;
  unreadNoticesCount?: number;
  spuriousCount?: number;
  onNavigate?: (href: string) => void;
  onSignOut?: () => void;
}

export const TopNav: React.FC<TopNavProps> = ({
  onNewSession,
  onOpenAlerts,
  unreadNoticesCount = 0,
  spuriousCount = 0,
  onNavigate,
  onSignOut,
}) => {
  const { user, isAuthenticated, logout, openModal } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  const anonId = getAnonymousId().slice(0, 8);

  // Derive actual person name from profile or email
  const rawEmail = user?.email || (user?.user_id && user.user_id.includes('@') ? user.user_id : '');
  const derivedFromEmail = rawEmail
    ? rawEmail
        .split('@')[0]
        .split(/[._-]/)
        .filter(Boolean)
        .map((s) => s.charAt(0).toUpperCase() + s.slice(1))
        .join(' ')
    : '';

  const displayName =
    user?.name && user.name.trim() && user.name.toLowerCase() !== 'customer'
      ? user.name
      : derivedFromEmail
      ? derivedFromEmail
      : isAuthenticated
      ? 'Jyotirmoy'
      : 'Guest User';

  const displayRole = !isAuthenticated
    ? 'Guest Access'
    : user?.role === 'pharmacist'
    ? 'Licensed Pharmacist'
    : user?.role === 'admin'
    ? 'Administrator'
    : 'Consumer Account';

  const initials = displayName
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((n) => n[0].toUpperCase())
    .join('') || (isAuthenticated ? 'J' : 'G');

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="h-13 py-2.5 px-6 bg-white border-b border-slate-200 z-30 flex items-center justify-between shrink-0 shadow-xs select-none">
      <div className="flex items-center gap-4">
        {/* Brand Logo & Name */}
        <div
          className="flex items-center gap-2.5 cursor-pointer"
          onClick={() => {
            onNewSession?.();
            onNavigate?.('#dashboard');
          }}
        >
          <div className="w-7 h-7 rounded-md bg-sky-600 flex items-center justify-center text-white font-bold shadow-xs">
            <span className="material-symbols-outlined text-[17px] text-white font-semibold">verified_user</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-semibold text-[15px] tracking-tight text-slate-900">MedVerify</span>
            <span className="font-mono text-[10px] text-slate-600 font-medium px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200">
              CDSCO AI
            </span>
          </div>
        </div>

        <div className="h-4 w-px bg-slate-200" />

        {/* Live CDSCO Status */}
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-600" />
          </span>
          <span className="text-[12px] text-slate-600 font-medium">CDSCO Gateway Online</span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Alerts & Recalls Trigger */}
        <button
          type="button"
          className="flex items-center gap-1.5 text-xs text-slate-600 hover:text-slate-900 px-2.5 py-1.5 rounded-md hover:bg-slate-100 transition-colors border border-slate-200 cursor-pointer shadow-2xs"
          onClick={() => onOpenAlerts?.()}
          title="Open CDSCO Recall Notices Drawer"
        >
          <span className="material-symbols-outlined text-[16px] text-rose-600">crisis_alert</span>
          <span className="hidden sm:inline font-medium">
            {unreadNoticesCount > 0 ? `${unreadNoticesCount} Notices` : 'Recalls'}
          </span>
          {spuriousCount > 0 && (
            <span className="px-1.5 py-0.5 rounded bg-rose-50 text-rose-700 font-mono text-[10px] font-semibold border border-rose-200">
              {spuriousCount} Spurious
            </span>
          )}
        </button>

        <div className="h-4 w-px bg-slate-200" />

        {/* User Profile Pill */}
        <div className="relative" ref={dropdownRef}>
          <button
            type="button"
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2 pl-1.5 pr-2.5 py-1 hover:bg-slate-100 rounded-lg border border-slate-200 transition cursor-pointer shadow-2xs"
            title={`Logged in as ${displayName}`}
          >
            <div className="w-7 h-7 rounded-full bg-sky-600 border border-sky-700 flex items-center justify-center text-xs font-bold text-white shadow-2xs">
              {initials}
            </div>
            <div className="flex flex-col text-left">
              <span className="text-[13px] font-semibold leading-tight text-slate-900 truncate max-w-[180px]">
                {displayName}
              </span>
              <span className="font-mono text-[10px] text-slate-500 leading-tight">
                {displayRole}
              </span>
            </div>
            <span className="material-symbols-outlined text-[16px] text-slate-400">expand_more</span>
          </button>

          {/* Profile Dropdown Menu */}
          {dropdownOpen && (
            <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-xl border border-slate-200 py-1 z-50 text-xs text-slate-700 font-sans">
              <div className="px-3 py-2 border-b border-slate-100">
                <div className="font-semibold text-slate-900 truncate">{displayName}</div>
                {user?.email && <div className="text-[11px] text-slate-500 truncate">{user.email}</div>}
                <div className="text-[11px] text-slate-500 font-mono mt-0.5">{displayRole}</div>
                <div className="text-[10px] text-slate-400 font-mono mt-0.5">Session: {anonId}</div>
              </div>

              {isAuthenticated ? (
                <>
                  <a
                    href="https://cdsco.gov.in/opencms/opencms/en/Notifications/nsq-drugs/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 px-3 py-2 hover:bg-slate-50 text-slate-700 transition"
                  >
                    <span className="material-symbols-outlined text-[15px] text-slate-400">gavel</span>
                    <span>CDSCO Gazette Portal</span>
                  </a>
                  <button
                    type="button"
                    onClick={() => {
                      setDropdownOpen(false);
                      logout();
                      onSignOut?.();
                    }}
                    className="w-full text-left flex items-center gap-2 px-3 py-2 hover:bg-rose-50 text-rose-600 transition cursor-pointer"
                  >
                    <span className="material-symbols-outlined text-[15px]">logout</span>
                    <span>Sign Out</span>
                  </button>
                </>
              ) : (
                <div className="p-2 space-y-1">
                  <button
                    type="button"
                    onClick={() => {
                      setDropdownOpen(false);
                      openModal('login');
                    }}
                    className="w-full text-center py-1.5 bg-sky-600 hover:bg-sky-700 text-white font-medium rounded-lg transition cursor-pointer"
                  >
                    Sign In
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setDropdownOpen(false);
                      openModal('signup');
                    }}
                    className="w-full text-center py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-lg transition cursor-pointer"
                  >
                    Create Account
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
