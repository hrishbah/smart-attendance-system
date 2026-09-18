import { useEffect, useState } from 'react';
import { Plus } from 'lucide-react';
import { api, Faculty } from '../api/client';
import toast from 'react-hot-toast';

export default function FacultyPage() {
  const [faculty, setFaculty] = useState<Faculty[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ name: '', email: '', department: 'CSE AI', password: 'faculty123' });

  const load = () => api.getFaculty({ per_page: '50' }).then(r => setFaculty(r.items));

  useEffect(() => { load(); }, []);

  const handleSave = async () => {
    try {
      await api.createFaculty(form);
      toast.success('Faculty created');
      setShowModal(false);
      load();
    } catch (e: unknown) {
      toast.error((e as Error).message);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between">
        <h2 className="text-2xl font-bold">Faculty</h2>
        <button onClick={() => setShowModal(true)} className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg"><Plus size={18} /> Add Faculty</button>
      </div>
      <div className="bg-white dark:bg-gray-800 rounded-xl border overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-700/50">
            <tr><th className="px-4 py-3 text-left">Name</th><th className="px-4 py-3 text-left">Email</th><th className="px-4 py-3 text-left">Department</th><th className="px-4 py-3 text-left">Status</th></tr>
          </thead>
          <tbody>
            {faculty.map(f => (
              <tr key={f.id} className="border-t">
                <td className="px-4 py-3 font-medium">{f.name}</td>
                <td className="px-4 py-3">{f.email}</td>
                <td className="px-4 py-3">{f.department}</td>
                <td className="px-4 py-3"><span className="text-green-600 capitalize">{f.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 w-full max-w-md space-y-3">
            <h3 className="font-bold">Add Faculty</h3>
            {(['name', 'email', 'department', 'password'] as const).map(f => (
              <input key={f} placeholder={f} value={form[f]} onChange={e => setForm({ ...form, [f]: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700" />
            ))}
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowModal(false)} className="px-4 py-2 border rounded-lg">Cancel</button>
              <button onClick={handleSave} className="px-4 py-2 bg-primary-600 text-white rounded-lg">Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
