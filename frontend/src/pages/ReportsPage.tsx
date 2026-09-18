import { useEffect, useState } from 'react';
import { Download } from 'lucide-react';
import { api, Subject } from '../api/client';

export default function ReportsPage() {
  const [type, setType] = useState('daily');
  const [subjectId, setSubjectId] = useState<number | ''>('');
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [records, setRecords] = useState<{ student_name: string; roll_number: string; subject: string; date: string; time: string; status: string; confidence?: number }[]>([]);

  useEffect(() => { api.getSubjects().then(setSubjects); }, []);

  useEffect(() => {
    api.getReport(type, subjectId || undefined).then(r => setRecords(r.records));
  }, [type, subjectId]);

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
        <a href={api.exportCsv(type)} className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg"><Download size={16} /> CSV</a>
        <a href={api.exportExcel(type)} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg"><Download size={16} /> Excel</a>
        <a href={api.exportPdf(type)} className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg"><Download size={16} /> PDF</a>
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
