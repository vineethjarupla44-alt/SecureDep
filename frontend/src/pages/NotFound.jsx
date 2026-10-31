import React from 'react';
import { Link } from 'react-router-dom';
import Icon from '../components/common/Icons';

export const NotFound = () => {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center p-6">
      <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center text-slate-400 mb-4">
        <Icon name="alertTriangle" className="w-8 h-8 text-amber-500" />
      </div>
      <h2 className="text-2xl font-black text-slate-800">404 - Page Not Found</h2>
      <p className="text-xs text-slate-500 max-w-sm mt-1">
        The requested regulatory portal page does not exist or has been relocated under a different security scope.
      </p>
      <Link
        to="/"
        className="mt-5 inline-flex items-center gap-2 px-4 py-2 bg-aicte-navy text-white text-xs font-bold rounded-xl hover:bg-aicte-dark transition shadow-sm"
      >
        <Icon name="dashboard" className="w-4 h-4" />
        Return to Portal Home
      </Link>
    </div>
  );
};

export default NotFound;
