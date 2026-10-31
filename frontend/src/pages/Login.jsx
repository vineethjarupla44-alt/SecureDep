import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Icon from '../components/common/Icons';

export const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [accountStatus, setAccountStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const { login, switchDemoPersona } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setAccountStatus(null);

    try {
      const res = await login(email, password);
      // Route based on role
      const userRole = res?.user?.role;
      if (userRole === 'administrator') navigate('/admin');
      else if (userRole === 'aicte_official') navigate('/official');
      else navigate('/institution');
    } catch (err) {
      if (err.data?.account_status) {
        setAccountStatus(err.data.account_status);
      }
      setError(err.message || 'Invalid email or password. Please verify your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickPersona = async (roleName, demoEmail, demoPass) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setLoading(true);
    setError(null);
    try {
      await login(demoEmail, demoPass);
      if (roleName === 'administrator') navigate('/admin');
      else if (roleName === 'aicte_official') navigate('/official');
      else navigate('/institution');
    } catch (err) {
      // If backend user not seeded yet in live DB, switch to demo persona locally
      await switchDemoPersona(roleName);
      if (roleName === 'administrator') navigate('/admin');
      else if (roleName === 'aicte_official') navigate('/official');
      else navigate('/institution');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-center py-12 sm:px-6 lg:px-8 bg-slate-100 font-sans gov-pattern">
      {/* Top Banner */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center mb-6">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-white shadow-xl border border-slate-200 mb-3">
          <Icon name="shield" className="w-10 h-10 text-aicte-navy" />
        </div>
        <h2 className="text-2xl font-extrabold text-white tracking-tight">
          AICTE SECURITY DEPOSIT PORTAL
        </h2>
        <p className="text-xs font-medium text-slate-300 mt-1">
          Government of India &bull; All India Council for Technical Education
        </p>
      </div>

      {/* Login Card */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 shadow-2xl rounded-2xl sm:px-10 border border-slate-200/80">
          <div className="mb-6 pb-4 border-b border-slate-100">
            <h3 className="text-base font-bold text-slate-800">Regulatory Portal Authentication</h3>
            <p className="text-xs text-slate-500 mt-0.5">Enter your institutional or official credentials</p>
          </div>

          {accountStatus === 'PENDING' ? (
            <div className="mb-4 p-3.5 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 text-xs">
              <div className="flex items-center gap-2 font-bold mb-1">
                <Icon name="clock" className="w-4 h-4 text-amber-700 shrink-0" />
                <span>Account Pending Administrative Verification</span>
              </div>
              <p className="text-[11px] text-amber-800 leading-relaxed">
                Your registration was received and is currently in <strong className="font-semibold">PENDING</strong> review. An AICTE administrator must verify your institutional credentials before access is granted.
              </p>
            </div>
          ) : accountStatus === 'REJECTED' ? (
            <div className="mb-4 p-3.5 rounded-xl bg-rose-50 border border-rose-300 text-rose-900 text-xs">
              <div className="flex items-center gap-2 font-bold mb-1">
                <Icon name="xCircle" className="w-4 h-4 text-rose-700 shrink-0" />
                <span>Registration Request Rejected</span>
              </div>
              <p className="text-[11px] text-rose-800 leading-relaxed">
                Your institutional registration has been rejected by the administrator. Please contact AICTE support or submit a new request.
              </p>
            </div>
          ) : error && (
            <div className="mb-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-semibold flex items-center gap-2">
              <Icon name="alertTriangle" className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4 text-xs">
            <div>
              <label className="block font-bold text-slate-700 mb-1">Official Email Address</label>
              <div className="relative">
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="e.g. officer@aicte-india.org"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-aicte-navy text-xs font-medium"
                />
              </div>
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-aicte-navy text-xs font-medium"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 rounded-xl bg-aicte-navy text-white text-xs font-bold hover:bg-aicte-dark shadow-md transition disabled:opacity-50 mt-2"
            >
              {loading ? 'Authenticating with Central Registry...' : 'Sign In to Portal'}
            </button>
          </form>

          {/* Quick Demo Personas (Evaluation Tool) */}
          <div className="mt-6 pt-6 border-t border-slate-200">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider text-center mb-3">
              One-Click Role Switcher (Evaluation Testing)
            </p>
            <div className="grid grid-cols-3 gap-2 text-[11px]">
              <button
                type="button"
                onClick={() => handleQuickPersona('administrator', 'admin@aicte-india.org', 'AdminSecure2026!')}
                className="p-2 rounded-lg border border-slate-200 bg-slate-50 hover:bg-aicte-light hover:border-aicte-navy text-slate-700 font-semibold text-center transition"
              >
                <span className="block font-bold text-aicte-navy text-[10px]">Admin</span>
                Executive
              </button>

              <button
                type="button"
                onClick={() => handleQuickPersona('aicte_official', 'regulator@aicte-india.org', 'OfficialSecure2026!')}
                className="p-2 rounded-lg border border-slate-200 bg-slate-50 hover:bg-aicte-light hover:border-aicte-navy text-slate-700 font-semibold text-center transition"
              >
                <span className="block font-bold text-aicte-navy text-[10px]">Official</span>
                Scrutiny
              </button>

              <button
                type="button"
                onClick={() => handleQuickPersona('institution_user', 'officer@dit.edu.in', 'DITSecret2026!')}
                className="p-2 rounded-lg border border-slate-200 bg-slate-50 hover:bg-aicte-light hover:border-aicte-navy text-slate-700 font-semibold text-center transition"
              >
                <span className="block font-bold text-aicte-navy text-[10px]">Institution</span>
                Finance
              </button>
            </div>
          </div>

          <div className="mt-6 text-center text-xs text-slate-500">
            New educational institution?{' '}
            <Link to="/register" className="font-bold text-aicte-navy hover:underline">
              Register Institution User
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
