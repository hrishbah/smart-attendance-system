import { useEffect, useState } from 'react';
import { Download } from 'lucide-react';
import { api, Subject } from '../api/client';

export default function ReportsPage() {
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [type, setType] = useState('daily');
  const [subjectId, setSubjectId] = useState<number | ''>('');
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [records, setRecords] = useState<{ student_name: string; roll_number: string; subject: string; date: string; time: string; status: string; confidence?: number }[]>([]);

  useEffect(() => { api.getSubjects().then(setSubjects); }, []);

  useEffect(() => {
    api.getReport(type, subjectId || undefined).then(r => setRecords(r.records));
  }, [type, subjectId]);

  const handleDownload = async (format: 'csv' | 'excel' | 'pdf') => {
    if (downloading) return;
    setDownloading(true);
    setError(null);
    try {
      const apiBase = import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL : '';
      const url = (apiBase ? apiBase + '/api' : '/api') + `/reports/export/${format}?report_type=${encodeURIComponent(type)}${subjectId ? '&subject_id=' + encodeURIComponent(String(subjectId)) : ''}`;
      const res = await fetch(url, { credentials: 'include' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        const msg = Array.isArray(err.detail) ? err.detail.map((d: { msg: string }) => d.msg).join(', ') : (err.detail || `Download failed (${res.status})`);
        throw new Error(msg);
      }
      const blob = await res.blob();
      const ext = format === 'excel' ? 'xlsx' : format;
      const a = document.createElement('a');
      const urlObj = URL.createObjectURL(blob);
      a.href = urlObj;
      a.download = `attendance-report-${type}-${subjectId || 'all'}.${ext}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(urlObj), 100);
    } catch (e: any) {
      setError(e?.message || 'Download failed');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Reports</h2>
      <div className="flex flex-wrap gap-3">
        {['daily', 'weekly', 'monthly'].map(t => (
          <button key={t} onClick={() => setType(t)} className={`px-4 py-2 rounded-lg capitalize ${type === t ? 'bg-primary-600 text-white' : 'bg-gray-200 dark:bg-gray-700'}`}>{t}</button>
        ))}
        <select value={subjectId} onChange={e => setSubjectId(e.target.value ? Number(e.target.value) : '')}
          className="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800">
          <option value="">All Subjects</option>
          {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        {error && <div className="w-full text-red-600 text-sm font-medium">{error}</div>}
        <button onClick={() => handleDownload('csv')} disabled={downloading} className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg disabled:opacity-50">{downloading ? 'Downloading…' : <><Download size={16} /> CSV</>}</button>
        <button onClick={() => handleDownload('excel')} disabled={downloading} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg disabled:opacity-50">{downloading ? 'Downloading…' : <><Download size={16} /> Excel</>}</button>
        <button onClick={() => handleDownload('pdf')} disabled={downloading} className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg disabled:opacity-50">{downloading ? 'Downloading…' : <><Download size={16} /> PDF</>}</button>
      </div>
      <div className="bg-white dark:bg-gray-800 rounded-xl border overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-700/50">
            <tr>
              <th className="px-4 py-3 text-left">Student</th>
              <th className="px-4 py-3 text-left">Roll No</th>
              <th className="px-4 py-3 text-left">Subject</th>
              <th className="px-4 py-3 text-left">Date</th>
              <th className="px-4 py-3 text-left">Time</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {records.map((r, i) => (
              <tr key={i} className="border-t">
                <td className="px-4 py-2">{r.student_name}</td>
                <td className="px-4 py-2">{r.roll_number}</td>
                <td className="px-4 py-2">{r.subject}</td>
                <td className="px-4 py-2">{r.date}</td>
                <td className="px-4 py-2">{r.time}</td>
                <td className="px-4 py-2">{r.status}</td>
                <td className="px-4 py-2">{r.confidence ? `${r.confidence}%` : '-'}</td>
              </tr>
            ))}
            {records.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-500">No records found</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
