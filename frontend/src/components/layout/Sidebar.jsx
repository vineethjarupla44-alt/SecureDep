import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Icon from '../common/Icons';

export const Sidebar = ({ isOpen, onClose }) => {
  const { role, isInstitutionUser, isAdmin, isOfficial, logout } = useAuth();

  const getDashboardLink = () => {
    if (isAdmin) return '/admin';
    if (isOfficial) return '/official';
    return '/institution';
  };

  const navItems = [
    {
      section: 'Dashboards',
      items: [
        ...(isAdmin
          ? [{ label: 'Admin Executive', path: '/admin', icon: 'dashboard', roles: ['administrator'] }]
          : []),
        ...(isOfficial
          ? [{ label: 'Regulatory & Scrutiny', path: '/official', icon: 'shield', roles: ['aicte_official', 'administrator'] }]
          : []),
        ...(isInstitutionUser || isAdmin
          ? [{ label: 'Institution Desk', path: '/institution', icon: 'building', roles: ['institution_user', 'administrator', 'aicte_official'] }]
          : []),
      ],
    },
    {
      section: 'Core Operations',
      items: [
        { label: 'FDR Instruments', path: '/fdr', icon: 'fileText' },
        { label: 'Documents & OCR', path: '/documents', icon: 'upload' },
        { label: 'Maturity & Alerts', path: '/maturity', icon: 'calendar' },
        { label: 'Release & Refund', path: '/release-refund', icon: 'arrowRightCircle' },
      ],
    },
    {
      section: 'Intelligence & Audit',
      items: [
        { label: 'AI/ML Intelligence', path: '/ai-intelligence', icon: 'brain', badge: 'Phase 8' },
        { label: 'Audit Trail', path: '/audit-trail', icon: 'history' },
      ],
    },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-xs lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-40 w-64 bg-white border-r border-slate-200 flex flex-col transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Top Header Logo on Mobile */}
        <div className="p-4 border-b border-slate-200 flex items-center justify-between lg:hidden">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-aicte-navy flex items-center justify-center text-white font-bold">
              <Icon name="shield" className="w-5 h-5 text-aicte-teal" />
            </div>
            <span className="font-bold text-slate-800 text-sm">AICTE FDR Portal</span>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:bg-slate-100">
            <Icon name="x" className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Section */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
          {navItems.map((group, idx) => (
            <div key={idx}>
              <div className="px-3 mb-2 text-[11px] font-bold tracking-wider text-slate-400 uppercase">
                {group.section}
              </div>
              <div className="space-y-1">
                {group.items.map((item) => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    onClick={() => {
                      if (window.innerWidth < 1024) onClose();
                    }}
                    className={({ isActive }) =>
                      `flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                        isActive
                          ? 'bg-aicte-navy text-white shadow-xs font-bold'
                          : 'text-slate-600 hover:text-aicte-navy hover:bg-slate-100/80'
                      }`
                    }
                  >
                    <div className="flex items-center gap-3">
                      <Icon name={item.icon} className="w-4 h-4" />
                      <span>{item.label}</span>
                    </div>
                    {item.badge && (
                      <span className="px-1.5 py-0.5 text-[9px] font-extrabold rounded-md bg-teal-100 text-teal-800">
                        {item.badge}
                      </span>
                    )}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Bottom System Status Badge & Logout */}
        <div className="p-3 border-t border-slate-200 bg-slate-50/50">
          <div className="px-3 py-2 rounded-xl bg-slate-100 border border-slate-200/80 mb-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-500 uppercase">AICTE Node</span>
              <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-600">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping"></span>
                ONLINE
              </span>
            </div>
            <p className="text-[11px] font-semibold text-slate-700 mt-0.5">Flask API v1.8.0</p>
          </div>

          <button
            onClick={logout}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-rose-600 hover:bg-rose-50 transition border border-transparent hover:border-rose-200"
          >
            <Icon name="logOut" className="w-4 h-4" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
