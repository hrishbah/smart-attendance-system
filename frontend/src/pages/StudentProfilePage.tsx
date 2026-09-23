import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api, StudentProfile, UPLOAD_URL } from '../api/client';

export default function StudentProfilePage() {
  const { id } = useParams();
  const [profile, setProfile] = useState<StudentProfile | null>(null);

  useEffect(() => {
    if (id) api.getStudentProfile(Number(id)).then(setProfile);
  }, [id]);

  if (!profile) return <div className="animate-pulse">Loading...</div>;
  const s = profile.student;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-xl border p-6 flex flex-col sm:flex-row gap-6">
        {s.profile_photo ? (
          <img src={`${UPLOAD_URL}/${s.profile_photo}`} alt="" className="w-32 h-32 rounded-xl object-cover" />
        ) : (
          <div className="w-32 h-32 rounded-xl bg-gray-200 dark:bg-gray-600 flex items-center justify-center text-4xl font-bold">{s.full_name.charAt(0)}</div>
        )}
        <div className="flex-1 grid grid-cols-2 gap-3 text-sm">
          <div><span className="text-gray-500">Name</span><p className="font-semibold text-lg">{s.full_name}</p></div>
          <div><span className="text-gray-500">Roll Number</span><p className="font-medium">{s.roll_number}</p></div>
          <div><span className="text-gray-500">Branch</span><p>{s.branch}</p></div>
          <div><span className="text-gray-500">Class</span><p>{s.class_section}</p></div>
          <div><span className="text-gray-500">Face Status</span>
            <p className={s.face_status === 'registered' ? 'text-green-600 font-medium' : 'text-gray-500'}>
              {s.face_status === 'registered' ? '✓ Registered' : 'Not Registered'}
            </p>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Total Classes', value: profile.total_classes },
          { label: 'Present', value: profile.present },
          { label: 'Absent', value: profile.absent },
          { label: 'Attendance %', value: `${profile.attendance_percentage}%` },
        ].map(c => (
          <div key={c.label} className="bg-white dark:bg-gray-800 rounded-xl border p-4 text-center">
            <p className="text-2xl font-bold">{c.value}</p>
            <p className="text-sm text-gray-500">{c.label}</p>
          </div>
        ))}
      </div>
      <div className="bg-white dark:bg-gray-800 rounded-xl border overflow-hidden">
        <h3 className="p-4 font-semibold border-b">Attendance History</h3>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-700/50">
            <tr><th className="px-4 py-2 text-left">Subject</th><th className="px-4 py-2 text-left">Date</th><th className="px-4 py-2 text-left">Time</th><th className="px-4 py-2 text-left">Status</th></tr>
          </thead>
          <tbody>
            {profile.attendance_history.map(a => (
              <tr key={a.id} className="border-t">
                <td className="px-4 py-2">{a.subject_name}</td>
                <td className="px-4 py-2">{a.date}</td>
                <td className="px-4 py-2">{a.time}</td>
                <td className="px-4 py-2"><span className="text-green-600">{a.status}</span></td>
              </tr>
            ))}
            {profile.attendance_history.length === 0 && (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-500">No attendance records yet</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
