import React, { useState, useEffect } from 'react';
import Card from '../components/common/Card';
import Badge from '../components/common/Badge';
import Icon from '../components/common/Icons';
import LoadingSpinner from '../components/common/LoadingSpinner';
import RiskRadarGauge from '../components/ai/RiskRadarGauge';
import DuplicateComparisonModal from '../components/ai/DuplicateComparisonModal';
import ComplianceGradeBadge from '../components/ai/ComplianceGradeBadge';
import Modal from '../components/common/Modal';
import { formatCurrency, formatDateTime } from '../utils/formatters';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

export const AIIntelligencePage = () => {
  const { isOfficial, isAdmin, user } = useAuth();

  const [loading, setLoading] = useState(true);
  const [candidates, setCandidates] = useState([]);
  const [complianceSummary, setComplianceSummary] = useState(null);
  const [modelHealth, setModelHealth] = useState(null);
  const [selectedCandidate, setSelectedCandidate] = useState(null);

  // Single FDR Risk Scorer Playground State
  const [sampleFdrId, setSampleFdrId] = useState('1');
  const [riskAssessment, setRiskAssessment] = useState(null);
  const [evaluatingRisk, setEvaluatingRisk] = useState(false);

  // 360 Dossier Modal State
  const [dossier, setDossier] = useState(null);
  const [dossierLoading, setDossierLoading] = useState(false);

  // Action Messages
  const [statusMsg, setStatusMsg] = useState(null);
  const [trainingModel, setTrainingModel] = useState(false);

  const fetchAIData = async () => {
    setLoading(true);
    try {
      const [dupRes, compRes, healthRes] = await Promise.allSettled([
        api.getDuplicateCandidates({ per_page: 20 }),
        isOfficial ? api.getGlobalComplianceSummary() : api.getInstitutionCompliance(user?.institution_id || 1),
        api.getModelsHealth(),
      ]);

      if (dupRes.status === 'fulfilled') setCandidates(dupRes.value?.data || []);
      if (compRes.status === 'fulfilled') setComplianceSummary(compRes.value);
      if (healthRes.status === 'fulfilled') setModelHealth(healthRes.value?.data);

      // Auto-evaluate first instrument for live demonstration
      evaluateSampleRisk('1');
    } catch (err) {
      console.error('Failed to load AI intelligence data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAIData();
  }, []);

  const evaluateSampleRisk = async (id) => {
    if (!id) return;
    setEvaluatingRisk(true);
    try {
      const res = await api.getFDRRiskScore(parseInt(id));
      if (res?.data) setRiskAssessment(res.data);
    } catch (e) {
      // Soft fallback
    } finally {
      setEvaluatingRisk(false);
    }
  };

  const handleTriggerDuplicateScan = async () => {
    setStatusMsg('Executing multi-pass intelligent duplicate scan...');
    try {
      const res = await api.triggerDuplicateScan();
      setStatusMsg(`Duplicate scan completed: ${res.data?.total_fdrs_scanned || 0} scanned, ${res.data?.new_candidates_created || 0} candidates created.`);
      const dupRes = await api.getDuplicateCandidates({ per_page: 20 });
      setCandidates(dupRes.data || []);
    } catch (err) {
      setStatusMsg(`Duplicate scan failed: ${err.message}`);
    }
  };

  const handleRetrainModel = async () => {
    setTrainingModel(true);
    setStatusMsg('Retraining baseline Isolation Forest on synthetic domain benchmark...');
    try {
      const res = await api.trainModel(500);
      setStatusMsg(`Retraining complete: ${res.data?.samples_trained || 500} benchmark samples trained and registered.`);
      const health = await api.getModelsHealth();
      setModelHealth(health.data);
    } catch (err) {
      setStatusMsg(`Retraining error: ${err.message}`);
    } finally {
      setTrainingModel(false);
    }
  };

  const handleOpen360Dossier = async (fdrId) => {
    setDossierLoading(true);
    try {
      const res = await api.get360Report(fdrId);
      setDossier(res.data);
    } catch (err) {
      alert(`Failed to load dossier: ${err.message}`);
    } finally {
      setDossierLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            <Icon name="brain" className="w-6 h-6 text-aicte-teal" />
            Advanced AI &amp; Machine Learning Intelligence Dashboard (Phase 8)
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Enterprise duplicate detection, explainable Isolation Forest anomaly scoring, and predictive compliance
          </p>
        </div>

        <div className="flex items-center gap-2">
          {isOfficial && (
            <button
              onClick={handleTriggerDuplicateScan}
              className="px-3.5 py-1.5 rounded-xl bg-aicte-teal text-white text-xs font-bold hover:bg-teal-700 transition shadow-xs flex items-center gap-1.5"
            >
              <Icon name="search" className="w-4 h-4" />
              Trigger Duplicate Scan
            </button>
          )}

          {isAdmin && (
            <button
              onClick={handleRetrainModel}
              disabled={trainingModel}
              className="px-3.5 py-1.5 rounded-xl bg-aicte-navy text-white text-xs font-bold hover:bg-aicte-dark transition shadow-xs flex items-center gap-1.5 disabled:opacity-50"
            >
              <Icon name="repeat" className={`w-4 h-4 ${trainingModel ? 'animate-spin' : ''}`} />
              {trainingModel ? 'Retraining...' : 'Retrain Baseline Model'}
            </button>
          )}
        </div>
      </div>

      {statusMsg && (
        <div className="p-3 rounded-xl bg-blue-50 border border-blue-200 text-blue-900 text-xs font-semibold flex items-center justify-between">
          <span>{statusMsg}</span>
          <button onClick={() => setStatusMsg(null)} className="text-blue-500 hover:text-blue-700 text-xs">
            Dismiss
          </button>
        </div>
      )}

      {/* Model Registry Telemetry Bar */}
      {modelHealth && (
        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-200 text-aicte-teal flex items-center justify-center font-bold">
              <Icon name="shield" className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-800 text-sm">Active AI Engine: {modelHealth.algorithm}</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-700">
                  {modelHealth.model_version}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Status: <strong className="text-emerald-600 uppercase font-semibold">{modelHealth.status}</strong> &bull; Feature Dimension: 8 Numerical Indicators
              </p>
            </div>
          </div>

          <div className="flex gap-4 text-slate-600 text-xs">
            <div>
              <span className="text-[10px] text-slate-400 font-bold uppercase block">Inference Engine</span>
              <span className="font-semibold text-slate-800">Scikit-learn IsolationForest</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 font-bold uppercase block">Attribution Mode</span>
              <span className="font-semibold text-slate-800">Dual Statistical Z-Score / IQR</span>
            </div>
          </div>
        </div>
      )}

      {/* 2-Column Section: Explainable Risk Scorer Radar & Compliance Grading */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risk Scorer Radar Box */}
        <Card title="Explainable Composite Risk Evaluation (0–100)" subtitle="Interactive multi-factor instrument scoring" icon="shield">
          <div className="space-y-4">
            {/* Input & Evaluation Form */}
            <div className="flex items-center gap-2">
              <div className="flex-1">
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Evaluate FDR Instrument ID</label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    min="1"
                    value={sampleFdrId}
                    onChange={(e) => setSampleFdrId(e.target.value)}
                    className="flex-1 px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-mono"
                    placeholder="Enter FDR ID (e.g. 1)"
                  />
                  <button
                    onClick={() => evaluateSampleRisk(sampleFdrId)}
                    disabled={evaluatingRisk}
                    className="px-4 py-1.5 rounded-lg bg-aicte-navy text-white text-xs font-semibold hover:bg-aicte-dark disabled:opacity-50"
                  >
                    {evaluatingRisk ? 'Analyzing...' : 'Evaluate'}
                  </button>
                  <button
                    onClick={() => handleOpen360Dossier(sampleFdrId)}
                    disabled={dossierLoading}
                    className="px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 text-xs font-semibold hover:bg-slate-50"
                  >
                    360° Dossier
                  </button>
                </div>
              </div>
            </div>

            {/* Radar Display */}
            {riskAssessment ? (
              <div className="space-y-4">
                <RiskRadarGauge
                  score={riskAssessment.risk_score}
                  category={riskAssessment.risk_category}
                  ruleScore={riskAssessment.rule_score}
                  mlScore={riskAssessment.ml_score}
                />

                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-2">
                  <div className="flex items-center justify-between border-b border-slate-200/80 pb-2">
                    <span className="font-bold text-slate-800">Recommended Supervisory Action:</span>
                    <Badge variant={`risk-${riskAssessment.risk_category?.toLowerCase()}`}>
                      {riskAssessment.risk_category}
                    </Badge>
                  </div>
                  <p className="text-slate-600 text-[11px] leading-relaxed">{riskAssessment.recommended_action}</p>
                </div>

                {/* Factors Attribution Accordion */}
                {riskAssessment.contributing_factors?.length > 0 && (
                  <div>
                    <h5 className="text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-2">
                      Factor Attribution Explanations
                    </h5>
                    <div className="space-y-1.5 text-xs">
                      {riskAssessment.contributing_factors.map((f, i) => (
                        <div key={i} className="p-2.5 rounded-lg bg-white border border-slate-200 flex items-start gap-2">
                          <Icon name="alertTriangle" className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                          <div>
                            <span className="font-bold text-slate-800 block">{f.factor || f.feature}</span>
                            <span className="text-[11px] text-slate-500 leading-normal">{f.explanation}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-slate-400 py-8 text-center">Enter an instrument ID above to evaluate composite risk.</p>
            )}
          </div>
        </Card>

        {/* Institutional Compliance Distribution & Profile */}
        <Card title="Council Predictive Compliance Intelligence" subtitle="Institutional grading scale & warning indicators" icon="brain">
          <div className="space-y-4">
            {/* Grade Scale Legend */}
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Regulatory Letter Grading Scale
              </span>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded font-black text-white bg-emerald-500 flex items-center justify-center text-[10px]">A</span>
                  <span className="text-slate-700">90–100: Exemplary</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded font-black text-white bg-teal-500 flex items-center justify-center text-[10px]">B</span>
                  <span className="text-slate-700">75–89: Good Standing</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded font-black text-white bg-amber-500 flex items-center justify-center text-[10px]">C</span>
                  <span className="text-slate-700">60–74: Attention Required</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded font-black text-white bg-rose-500 flex items-center justify-center text-[10px]">D</span>
                  <span className="text-slate-700">&lt;60: Intervention</span>
                </div>
              </div>
            </div>

            {/* Institution Profile Summary (if single) or Council Grid */}
            {complianceSummary?.institutions ? (
              <div>
                <h5 className="text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Affiliated Institutions Regulatory Roster
                </h5>
                <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                  {complianceSummary.institutions.map((inst) => (
                    <div
                      key={inst.institution_id}
                      className="p-3 rounded-xl border border-slate-200 bg-white flex items-center justify-between text-xs hover:border-aicte-navy transition"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-800">{inst.name}</span>
                          <span className="text-[10px] text-slate-400 font-mono font-bold">{inst.code}</span>
                        </div>
                        <p className="text-[10px] text-slate-500 mt-0.5">
                          Unresolved Matured FDRs: <strong className="text-rose-600">{inst.matured_unresolved_count || 0}</strong>
                        </p>
                      </div>

                      <ComplianceGradeBadge
                        grade={inst.compliance_grade}
                        score={inst.compliance_score}
                      />
                    </div>
                  ))}
                </div>
              </div>
            ) : complianceSummary?.compliance_grade ? (
              <div className="p-4 rounded-xl border border-slate-200 bg-white">
                <ComplianceGradeBadge
                  grade={complianceSummary.compliance_grade}
                  score={complianceSummary.compliance_score}
                />
              </div>
            ) : null}

            {/* Safety Disclaimer */}
            <div className="p-3 rounded-lg bg-blue-50/70 border border-blue-200 text-blue-900 text-[11px] leading-relaxed">
              <p className="font-bold flex items-center gap-1.5">
                <Icon name="info" className="w-3.5 h-3.5 text-blue-700" />
                Statutory Regulatory Guardrail:
              </p>
              <p className="text-blue-800 mt-0.5">
                AI and machine learning indicators are advisory analytical signals. They do not automatically approve, reject, release, or refund any security deposit.
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Intelligent Duplicate Candidates Table */}
      <Card
        title="Intelligent Duplicate FDR Candidates (Phase 8)"
        subtitle="Cross-institution identical certificates, SHA-256 hash collisions, and fuzzy Levenshtein matches"
        icon="brain"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-4">Flag ID</th>
                <th className="py-2.5 px-4">Primary FDR</th>
                <th className="py-2.5 px-4">Duplicate Candidate</th>
                <th className="py-2.5 px-4">Detection Algorithm</th>
                <th className="py-2.5 px-4">Similarity Score</th>
                <th className="py-2.5 px-4 text-center">Status</th>
                <th className="py-2.5 px-4 text-right">Review Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {candidates.length > 0 ? (
                candidates.map((cand) => (
                  <tr key={cand.id} className="hover:bg-slate-50 transition">
                    <td className="py-3 px-4 font-mono font-bold text-slate-800">#{cand.id}</td>
                    <td className="py-3 px-4 font-mono font-semibold text-slate-800">
                      {cand.primary_fdr?.fdr_number || `#${cand.primary_fdr_id}`}
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-rose-700">
                      {cand.duplicate_fdr?.fdr_number || `#${cand.duplicate_fdr_id}`}
                    </td>
                    <td className="py-3 px-4">
                      <Badge variant="teal">{cand.match_type}</Badge>
                    </td>
                    <td className="py-3 px-4 font-bold text-slate-900">
                      {(cand.similarity_score * 100).toFixed(1)}%
                    </td>
                    <td className="py-3 px-4 text-center">
                      <Badge status={cand.status} />
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => setSelectedCandidate(cand)}
                        className="px-3 py-1 rounded-lg bg-aicte-navy text-white text-[11px] font-semibold hover:bg-aicte-dark transition shadow-xs"
                      >
                        Inspect Diff
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    No suspect duplicate candidates detected in the current scope.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Duplicate Modal */}
      {selectedCandidate && (
        <DuplicateComparisonModal
          isOpen={!!selectedCandidate}
          onClose={() => setSelectedCandidate(null)}
          candidate={selectedCandidate}
          onReviewSuccess={() => fetchAIData()}
        />
      )}

      {/* 360-Degree AI Dossier Modal */}
      {dossier && (
        <Modal
          isOpen={!!dossier}
          onClose={() => setDossier(null)}
          title={`360-Degree AI Dossier: FDR #${dossier.fdr_details?.id}`}
          subtitle={`Certificate Number: ${dossier.fdr_details?.fdr_number} &bull; ${dossier.institution?.name}`}
          maxWidth="max-w-4xl"
        >
          <div className="space-y-5 text-xs max-h-[70vh] overflow-y-auto">
            {/* Top Stat */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div>
                <span className="text-[10px] text-slate-400 font-bold uppercase">Principal</span>
                <p className="text-base font-bold text-slate-900">{formatCurrency(dossier.fdr_details?.deposit_amount)}</p>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 font-bold uppercase">Bank</span>
                <p className="font-semibold text-slate-800">{dossier.fdr_details?.issuing_bank}</p>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 font-bold uppercase">Risk Category</span>
                <div className="mt-0.5"><Badge variant={`risk-${dossier.risk_assessment?.risk_category?.toLowerCase()}`}>{dossier.risk_assessment?.risk_category}</Badge></div>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 font-bold uppercase">Anomaly Detected?</span>
                <p className="font-bold text-slate-800 mt-0.5">{dossier.anomaly_analysis?.is_anomaly ? 'YES (Outlier)' : 'NO (Normal)'}</p>
              </div>
            </div>

            {/* Document Coverage */}
            <div className="p-4 rounded-xl border border-slate-200 bg-white">
              <h5 className="font-bold text-slate-800 mb-2">Attached Documents Verification Coverage</h5>
              <div className="text-slate-600">
                Total Documents Uploaded: <strong>{dossier.documents_verification?.total_documents || 0}</strong>
              </div>
            </div>

            {/* Statutory Disclaimer */}
            <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 leading-normal">
              <p className="font-bold">Official AICTE Regulatory Notice:</p>
              <p className="text-[11px] mt-0.5">{dossier.regulatory_disclaimer}</p>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default AIIntelligencePage;
