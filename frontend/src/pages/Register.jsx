import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Icon from '../components/common/Icons';
import api from '../services/api';

export const Register = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirm_password: '',
    full_name: '',
    institution_id: '',
  });
  const [institutions, setInstitutions] = useState([]);
  const [loadingInstitutions, setLoadingInstitutions] = useState(true);
  const [selectedInst, setSelectedInst] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchInstitutions = async () => {
      setLoadingInstitutions(true);
      try {
        const res = await api.getPublicInstitutions();
        const list = res?.data || [];
        setInstitutions(list);
        if (list.length > 0) {
          // Default to first available institution
          setFormData((prev) => ({ ...prev, institution_id: String(list[0].id) }));
          setSelectedInst(list[0]);
        }
      } catch (err) {
        console.error('Failed to load institutions list:', err);
        setError('Unable to load accredited institutions directory. Please try again or contact administrator.');
      } finally {
        setLoadingInstitutions(false);
      }
    };

    fetchInstitutions();
  }, []);

  const handleInstitutionChange = (e) => {
    const instId = e.target.value;
    setFormData({ ...formData, institution_id: instId });
    const found = institutions.find((i) => String(i.id) === String(instId));
    setSelectedInst(found || null);
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError(null);

    if (!formData.institution_id) {
      setError('Please select an accredited institution from the AICTE registry.');
      return;
    }

    if (formData.password !== formData.confirm_password) {
      setError('Passwords do not match.');
      return;
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters long with uppercase, lowercase, numbers, and special characters.');
      return;
    }

    setLoading(true);

    try {
      await register({
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name,
        institution_id: parseInt(formData.institution_id),
      });
      setSuccess(true);
    } catch (err) {
      setError(err.message || 'Registration failed. Please check your inputs.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-center py-12 sm:px-6 lg:px-8 bg-slate-100 font-sans gov-pattern">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center mb-6">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-white shadow-xl mb-3 border border-slate-200">
          <Icon name="shield" className="w-8 h-8 text-aicte-navy" />
        </div>
        <h2 className="text-xl font-extrabold text-white">AICTE Institution Registration</h2>
        <p className="text-xs text-slate-300 mt-1">Enroll as an Institution Finance Desk Officer</p>
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 shadow-2xl rounded-2xl sm:px-10 border border-slate-200">
          {success ? (
            <div className="text-center py-6 space-y-4">
              <div className="w-14 h-14 rounded-full bg-amber-100 text-amber-600 flex items-center justify-center mx-auto shadow-inner">
                <Icon name="checkCircle" className="w-8 h-8" />
              </div>
              <div>
                <h3 className="text-base font-extrabold text-slate-800">Registration Submitted for Verification</h3>
                <span className="inline-block mt-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
                  Status: PENDING APPROVAL
                </span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed px-2">
                Your institutional finance desk account for <strong className="text-slate-800">{selectedInst?.name || 'your institution'}</strong> has been submitted.
                An AICTE administrator will verify and activate your credentials before portal access is granted.
              </p>
              <div className="pt-2">
                <button
                  type="button"
                  onClick={() => navigate('/login')}
                  className="w-full py-2.5 px-4 rounded-xl bg-aicte-navy text-white text-xs font-bold hover:bg-aicte-dark shadow-md transition"
                >
                  Return to Regulatory Sign In
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleRegister} className="space-y-3.5 text-xs">
              {error && (
                <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 font-semibold flex items-center gap-2">
                  <Icon name="alertTriangle" className="w-4 h-4 text-rose-600 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <div>
                <label className="block font-bold text-slate-700 mb-1">Select Accredited Institution *</label>
                {loadingInstitutions ? (
                  <div className="p-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-400 text-xs">
                    Loading AICTE institution directory...
                  </div>
                ) : institutions.length === 0 ? (
                  <div className="p-3 rounded-xl border border-amber-200 bg-amber-50 text-amber-800 text-xs font-medium">
                    No accredited institutions found in database. Please contact an AICTE administrator to add institution records.
                  </div>
                ) : (
                  <>
                    <select
                      required
                      value={formData.institution_id}
                      onChange={handleInstitutionChange}
                      className="w-full px-3 py-2.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-aicte-navy text-xs font-medium bg-white"
                    >
                      <option value="">-- Select from AICTE Directory --</option>
                      {institutions.map((inst) => (
                        <option key={inst.id} value={inst.id}>
                          [{inst.institution_code}] {inst.name}
                        </option>
                      ))}
                    </select>

                    {selectedInst && (
                      <div className="mt-2 p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-[11px] text-slate-600">
                        <p className="font-semibold text-slate-800">{selectedInst.name}</p>
                        <p className="text-[10px] text-slate-500">
                          Code: <span className="font-mono font-bold text-aicte-navy">{selectedInst.institution_code}</span> &bull; Contact: {selectedInst.contact_email}
                        </p>
                      </div>
                    )}
                  </>
                )}
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Full Name / Desk Title *</label>
                <input
                  type="text"
                  required
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  placeholder="e.g. Dr. Rajesh Sharma (Finance Officer)"
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-aicte-navy"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Official Institutional Email *</label>
                <input
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="e.g. finance@dit-demo.edu.in"
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-aicte-navy"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Password *</label>
                  <input
                    type="password"
                    required
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    placeholder="••••••••••••"
                    className="w-full px-3 py-2 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-aicte-navy"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Confirm Password *</label>
                  <input
                    type="password"
                    required
                    value={formData.confirm_password}
                    onChange={(e) => setFormData({ ...formData, confirm_password: e.target.value })}
                    placeholder="••••••••••••"
                    className="w-full px-3 py-2 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-aicte-navy"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading || loadingInstitutions || institutions.length === 0}
                className="w-full py-2.5 px-4 rounded-xl bg-aicte-navy text-white text-xs font-bold hover:bg-aicte-dark shadow-md transition disabled:opacity-50 mt-2"
              >
                {loading ? 'Submitting Registration Request...' : 'Submit Institutional Registration'}
              </button>

              <div className="text-center text-xs text-slate-500 pt-2">
                Already registered?{' '}
                <Link to="/login" className="font-bold text-aicte-navy hover:underline">
                  Sign In Here
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default Register;
