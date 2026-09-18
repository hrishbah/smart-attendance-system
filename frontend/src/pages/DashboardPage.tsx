import { useEffect, useState } from 'react';
import { Users, GraduationCap, UserCheck, UserX, Percent, ScanFace } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import { api } from '../api/client';

function StatCard({ icon: Icon, label, value, color }: { icon: typeof Users; label: string; value: string | number; color: string }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
        </div>
        <div className={`p-3 rounded-xl ${color}`}><Icon size={22} /></div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState({ total_students: 0, total_faculty: 0, today_present: 0, today_absent: 0, attendance_percentage: 0, registered_faces: 0 });
  const [daily, setDaily] = useState<{ label: string; present: number; percentage: number }[]>([]);
  const [subject, setSubject] = useState<{ label: string; present: number }[]>([]);

  useEffect(() => {
    api.getStats().then(setStats);
    api.getDailyChart().then(setDaily);
    api.getSubjectChart().then(setSubject);
  }, []);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Dashboard</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <StatCard icon={Users} label="Total Students" value={stats.total_students} color="bg-blue-100 text-blue-600" />
        <StatCard icon={GraduationCap} label="Total Faculty" value={stats.total_faculty} color="bg-purple-100 text-purple-600" />
        <StatCard icon={UserCheck} label="Today's Present" value={stats.today_present} color="bg-green-100 text-green-600" />
        <StatCard icon={UserX} label="Today's Absent" value={stats.today_absent} color="bg-red-100 text-red-600" />
        <StatCard icon={Percent} label="Attendance %" value={`${stats.attendance_percentage}%`} color="bg-yellow-100 text-yellow-600" />
        <StatCard icon={ScanFace} label="Registered Faces" value={stats.registered_faces} color="bg-indigo-100 text-indigo-600" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold mb-4">Daily Attendance (7 days)</h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={daily}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="label" fontSize={12} />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="present" stroke="#3b82f6" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold mb-4">Subject-wise Attendance</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={subject}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="label" fontSize={10} angle={-20} textAnchor="end" height={60} />
              <YAxis />
              <Tooltip />
              <Bar dataKey="present" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
