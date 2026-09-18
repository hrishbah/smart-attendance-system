import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, Plus, Edit, Trash2, Eye, Camera } from 'lucide-react';
import { api, Student } from '../api/client';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

export default function StudentsPage() {
  const { role } = useAuth();
  const [students, setStudents] = useState<Student[]>([]);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [showModal, setShowModal] = useState(false);
  const [editStudent, setEditStudent] = useState<Student | null>(null);
  const [form, setForm] = useState({ full_name: '', roll_number: '', branch: 'CSE AI', class_section: 'CSE AI', semester: '1st Semester', email: '', phone: '' });

  const load = () => {
    const params: Record<string, string> = { page: String(page) };
    if (search) params.search = search;
    api.getStudents(params).then(r => { setStudents(r.items); setTotalPages(r.pages); });
  };

  useEffect(() => { load(); }, [page, search]);

  const handleSave = async () => {
    try {
      if (editStudent) {
        await api.updateStudent(editStudent.id, form);
        toast.success('Student updated');
      } else {
        await api.createStudent(form);
        toast.success('Student created');
      }
      setShowModal(false);
      setEditStudent(null);
      load();
    } catch (e: unknown) {
      toast.error((e as Error).message);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this student?')) return;
    try {
      await api.deleteStudent(id);
      toast.success('Student deleted');
      load();
    } catch (e: unknown) {
      toast.error((e as Error).message);
    }
  };

  const openEdit = (s: Student) => {
    setEditStudent(s);
    setForm({ full_name: s.full_name, roll_number: s.roll_number, branch: s.branch, class_section: s.class_section, semester: s.semester, email: s.email, phone: s.phone || '' });
    setShowModal(true);
  };

  const openNew = () => {
    setEditStudent(null);
    setForm({ full_name: '', roll_number: '', branch: 'CSE AI', class_section: 'CSE AI', semester: '1st Semester', email: '', phone: '' });
    setShowModal(true);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row justify-between gap-4">
        <h2 className="text-2xl font-bold">Students</h2>
        {role === 'admin' && (
          <button onClick={openNew} className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">
            <Plus size={18} /> Add Student
          </button>
        )}
      </div>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
        <input placeholder="Search by name, roll number..." value={search} onChange={e => { setSearch(e.target.value); setPage(1); }}
          className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800" />
      </div>
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-700/50">
            <tr>
              <th className="px-4 py-3 text-left">Photo</th>
              <th className="px-4 py-3 text-left">Name</th>
              <th className="px-4 py-3 text-left">Roll Number</th>
              <th className="px-4 py-3 text-left">Branch</th>
              <th className="px-4 py-3 text-left">Class</th>
              <th className="px-4 py-3 text-left">Face Status</th>
              <th className="px-4 py-3 text-left">Attendance %</th>
              <th className="px-4 py-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {students.map(s => (
              <tr key={s.id} className="border-t border-gray-100 dark:border-gray-700">
                <td className="px-4 py-3">
                  {s.profile_photo ? (
                    <img src={`/uploads/${s.profile_photo}`} alt="" className="w-10 h-10 rounded-full object-cover" />
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-gray-200 dark:bg-gray-600 flex items-center justify-center text-xs font-bold">
                      {s.full_name.charAt(0)}
                    </div>
                  )}
                </td>
                <td className="px-4 py-3 font-medium">{s.full_name}</td>
                <td className="px-4 py-3">{s.roll_number}</td>
                <td className="px-4 py-3">{s.branch}</td>
                <td className="px-4 py-3">{s.class_section}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${s.face_status === 'registered' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                    {s.face_status === 'registered' ? 'Registered' : 'Not Registered'}
                  </span>
                </td>
                <td className="px-4 py-3">{s.attendance_percentage ?? 0}%</td>
                <td className="px-4 py-3">
                  <div className="flex gap-1">
                    <Link to={`/students/${s.id}`} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"><Eye size={16} /></Link>
                    {role === 'admin' && (
                      <>
                        <Link to={`/face-registration?student=${s.id}`} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-primary-600"><Camera size={16} /></Link>
                        <button onClick={() => openEdit(s)} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"><Edit size={16} /></button>
                        <button onClick={() => handleDelete(s.id)} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-red-500"><Trash2 size={16} /></button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          {Array.from({ length: totalPages }, (_, i) => i + 1).slice(0, 10).map(p => (
            <button key={p} onClick={() => setPage(p)} className={`px-3 py-1 rounded ${p === page ? 'bg-primary-600 text-white' : 'bg-gray-200 dark:bg-gray-700'}`}>{p}</button>
          ))}
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 w-full max-w-lg space-y-4">
            <h3 className="text-lg font-bold">{editStudent ? 'Edit Student' : 'Add Student'}</h3>
            {(['full_name', 'roll_number', 'branch', 'class_section', 'semester', 'email', 'phone'] as const).map(f => (
              <div key={f}>
                <label className="text-sm font-medium capitalize">{f.replace('_', ' ')}</label>
                <input value={form[f]} onChange={e => setForm({ ...form, [f]: e.target.value })}
                  className="w-full mt-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700" />
              </div>
            ))}
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowModal(false)} className="px-4 py-2 rounded-lg border">Cancel</button>
              <button onClick={handleSave} className="px-4 py-2 rounded-lg bg-primary-600 text-white">Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
