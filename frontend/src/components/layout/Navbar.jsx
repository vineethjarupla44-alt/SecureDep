import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { formatRoleName } from '../../utils/formatters';
import Icon from '../common/Icons';
import api from '../../services/api';

export const Navbar = ({ onToggleSidebar }) => {
  const { user, logout, switchDemoPersona, role } = useAuth();
  const [unreadAlerts, setUnreadAlerts] = useState(0);
  const [showPersonaMenu, setShowPersonaMenu] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  useEffect(() => {
    const fetchAlertCount = async () => {
      try {
        const res = await api.getAlerts({ is_acknowledged: 'false', per_page: 1 });
        if (res?.total !== undefined) {
          setUnreadAlerts(res.total);
        }
      } catch (e) {
        // Soft fallback
      }
    };
    if (user) fetchAlertCount();
  }, [user]);

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
      {/* Top Government Strip */}
      <div className="bg-aicte-dark text-white px-4 py-1 text-[11px] font-medium flex items-center justify-between border-b border-aicte-navy">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            GOVERNMENT OF INDIA &bull; MINISTRY OF EDUCATION &bull; AICTE
          </span>
          <span className="text-slate-400">|</span>
          <span className="text-slate-300 hidden md:inline">SIH 26265 FDR &amp; Security Deposit Portal</span>
        </div>
        <div className="flex items-center gap-4 text-slate-300">
          <span className="text-emerald-400 font-semibold hidden sm:inline">Phase 8/9 Engine Active</span>
          <span>Helpdesk: 1800-AICTE-FDR</span>
        </div>
      </div>

      {/* Main App Bar */}
      <div className="px-4 lg:px-6 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={onToggleSidebar}
            className="p-2 rounded-lg text-slate-600 hover:bg-slate-100 lg:hidden"
            title="Toggle Menu"
          >
            <Icon name="menu" className="w-5 h-5" />
          </button>

          {/* AICTE Logo Emblem */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-aicte-dark to-aicte-navy flex items-center justify-center text-white font-bold shadow-md shadow-aicte-navy/20 border border-aicte-blue">
              <Icon name="shield" className="w-6 h-6 text-aicte-teal" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold text-slate-900 tracking-tight leading-none">
                  AICTE <span className="text-aicte-navy font-extrabold">FDR PORTAL</span>
                </h1>
                <span className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-teal-50 text-aicte-teal border border-teal-200 uppercase">
                  Gov Portal
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium mt-0.5">
                AI-Powered Security Deposit &amp; Compliance Management
              </p>
            </div>
          </div>
        </div>

        {/* Right Action Icons & Persona Menu */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Quick Persona Switcher for Evaluation */}
          <div className="relative">
            <button
              onClick={() => setShowPersonaMenu(!showPersonaMenu)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-xs font-semibold text-slate-700 transition"
              title="Switch demo persona for testing"
            >
              <span className="w-2 h-2 rounded-full bg-aicte-teal"></span>
              <span className="hidden md:inline">Role Switcher:</span>
              <span className="text-aicte-navy font-bold">{formatRoleName(role)}</span>
              <Icon name="chevronDown" className="w-3.5 h-3.5 text-slate-400" />
            </button>

            {showPersonaMenu && (
              <div className="absolute right-0 mt-2 w-64 rounded-xl bg-white shadow-xl border border-slate-200 p-2 z-50 animate-in fade-in slide-in-from-top-2">
                <div className="px-3 py-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                  Test User Personas
                </div>
                <button
                  onClick={() => {
                    switchDemoPersona('administrator');
                    setShowPersonaMenu(false);
                  }}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs font-semibold flex items-center justify-between ${
                    role === 'administrator' ? 'bg-aicte-light text-aicte-navy' : 'text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <div>
                    <p className="font-bold">System Administrator</p>
                    <p className="text-[10px] text-slate-500 font-normal">Full Council-wide Access</p>
                  </div>
                  {role === 'administrator' && <Icon name="checkCircle" className="w-4 h-4 text-aicte-navy" />}
                </button>

                <button
                  onClick={() => {
                    switchDemoPersona('aicte_official');
                    setShowPersonaMenu(false);
                  }}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs font-semibold flex items-center justify-between ${
                    role === 'aicte_official' ? 'bg-aicte-light text-aicte-navy' : 'text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <div>
                    <p className="font-bold">AICTE Official / Finance Desk</p>
                    <p className="text-[10px] text-slate-500 font-normal">Scrutiny &amp; Verification</p>
                  </div>
                  {role === 'aicte_official' && <Icon name="checkCircle" className="w-4 h-4 text-aicte-navy" />}
                </button>

                <button
                  onClick={() => {
                    switchDemoPersona('institution_user', 1);
                    setShowPersonaMenu(false);
                  }}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs font-semibold flex items-center justify-between ${
                    role === 'institution_user' ? 'bg-aicte-light text-aicte-navy' : 'text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <div>
                    <p className="font-bold">Delhi Institute of Tech (Inst 1)</p>
                    <p className="text-[10px] text-slate-500 font-normal">Isolated College Desk</p>
                  </div>
                  {role === 'institution_user' && <Icon name="checkCircle" className="w-4 h-4 text-aicte-navy" />}
                </button>
              </div>
            )}
          </div>

          {/* User Profile Chip */}
          <div className="relative">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center gap-2 p-1.5 rounded-xl hover:bg-slate-100 transition"
            >
              <div className="w-8 h-8 rounded-full bg-aicte-navy text-white flex items-center justify-center font-bold text-xs shadow-xs">
                {user?.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
              </div>
              <div className="hidden lg:block text-left">
                <p className="text-xs font-bold text-slate-800 leading-none">{user?.full_name || 'Officer'}</p>
                <p className="text-[10px] text-slate-500 mt-0.5">{user?.email || 'officer@aicte.gov.in'}</p>
              </div>
            </button>

            {showUserMenu && (
              <div className="absolute right-0 mt-2 w-56 rounded-xl bg-white shadow-xl border border-slate-200 p-2 z-50">
                <div className="px-3 py-2 border-b border-slate-100">
                  <p className="text-xs font-bold text-slate-800">{user?.full_name}</p>
                  <p className="text-[10px] text-slate-500 truncate">{user?.email}</p>
                  <span className="inline-block mt-1 px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700">
                    {formatRoleName(role)}
                  </span>
                </div>
                <button
                  onClick={() => {
                    setShowUserMenu(false);
                    logout();
                  }}
                  className="w-full text-left px-3 py-2 rounded-lg text-xs font-semibold text-rose-600 hover:bg-rose-50 flex items-center gap-2 mt-1"
                >
                  <Icon name="logOut" className="w-4 h-4" />
                  Sign Out
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Navbar;
