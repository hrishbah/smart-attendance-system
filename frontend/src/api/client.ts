const API_BASE = `${import.meta.env.VITE_API_URL || ''}/api`;

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...options.headers,
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));

    const msg = Array.isArray(err.detail)
      ? err.detail.map((d: { msg: string }) => d.msg).join(', ')
      : (err.detail || `HTTP ${res.status}`);

    throw new Error(msg);
  }

  if (res.status === 204) return {} as T;

  return res.json();
}

export const UPLOAD_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/uploads` : '/uploads';

export const api = {
  login: (email: string, password: string) =>
    request<{ role: string; name: string; email: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  logout: () => request('/auth/logout', { method: 'POST' }),

  me: () =>
    request<{ role: string; name: string; email: string }>('/auth/me'),

  getStats: () =>
    request<{
      total_students: number;
      total_faculty: number;
      today_present: number;
      today_absent: number;
      attendance_percentage: number;
      registered_faces: number;
    }>('/dashboard/stats'),

  getDailyChart: () =>
    request<
      { label: string; present: number; absent: number; percentage: number }[]
    >('/dashboard/charts/daily'),

  getSubjectChart: () =>
    request<{ label: string; present: number }[]>(
      '/dashboard/charts/subject'
    ),

  getStudents: (params?: Record<string, string>) => {
    const q = new URLSearchParams(params).toString();

    return request<{
      items: Student[];
      total: number;
      page: number;
      pages: number;
    }>(`/students?${q}`);
  },

  getStudent: (id: number) =>
    request<Student>(`/students/${id}`),

  getStudentProfile: (id: number) =>
    request<StudentProfile>(`/students/${id}/profile`),

  createStudent: (data: Partial<Student>) =>
    request<Student>('/students', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateStudent: (id: number, data: Partial<Student>) =>
    request<Student>(`/students/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteStudent: (id: number) =>
    request(`/students/${id}`, {
      method: 'DELETE',
    }),

  getFaculty: (params?: Record<string, string>) => {
    const q = new URLSearchParams(params).toString();

    return request<{ items: Faculty[]; total: number }>(
      `/faculty?${q}`
    );
  },

  createFaculty: (data: {
    name: string;
    email: string;
    department: string;
    password: string;
  }) =>
    request<Faculty>('/faculty', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getSubjects: () =>
    request<Subject[]>('/subjects'),

  getClasses: () =>
    request<ClassItem[]>('/classes'),

  getDepartments: () =>
    request<{ id: number; name: string; code: string }[]>(
      '/departments'
    ),

  detectFace: (blob: Blob) => {
    const fd = new FormData();

    fd.append('image', blob, 'frame.jpg');

    return request<FaceDetectResult>('/face/detect', {
      method: 'POST',
      body: fd,
    });
  },

  registerFace: (studentId: number, blobs: Blob[]) => {
    const fd = new FormData();

    blobs.forEach((b, i) => {
      fd.append('images', b, `sample_${i}.jpg`);
    });

    return request<{
      success: boolean;
      message: string;
      samples_collected: number;
    }>(`/face/register/${studentId}`, {
      method: 'POST',
      body: fd,
    });
  },

  startSession: (subjectId: number) =>
    request<AttendanceSession>('/attendance/sessions', {
      method: 'POST',
      body: JSON.stringify({ subject_id: subjectId }),
    }),

  endSession: (sessionId: number) =>
    request<AttendanceSession>(
      `/attendance/sessions/${sessionId}/end`,
      {
        method: 'POST',
      }
    ),

  getSession: (sessionId: number) =>
    request<AttendanceSession>(
      `/attendance/sessions/${sessionId}`
    ),

  getSessionRecords: (sessionId: number) =>
    request<AttendanceRecord[]>(
      `/attendance/sessions/${sessionId}/records`
    ),

  recognize: (sessionId: number, blob: Blob) => {
    const fd = new FormData();

    fd.append('image', blob, 'frame.jpg');

    return request<RecognitionResult>(
      `/attendance/sessions/${sessionId}/recognize`,
      {
        method: 'POST',
        body: fd,
      }
    );
  },

  getReport: (type: string, subjectId?: number) => {
    const q = new URLSearchParams({
      report_type: type,
    });

    if (subjectId) {
      q.set('subject_id', String(subjectId));
    }

    return request<{ records: ReportRecord[] }>(
      `/reports/attendance?${q}`
    );
  },

  exportCsv: (type: string) =>
    `${API_BASE}/reports/export/csv?report_type=${type}`,

  exportExcel: (type: string) =>
    `${API_BASE}/reports/export/excel?report_type=${type}`,

  exportPdf: (type: string) =>
    `${API_BASE}/reports/export/pdf?report_type=${type}`,
};

export interface Student {
  id: number;
  full_name: string;
  roll_number: string;
  branch: string;
  class_section: string;
  semester: string;
  email: string;
  phone?: string;
  profile_photo?: string;
  face_status: string;
  status: string;
  class_id?: number;
  attendance_percentage?: number;
}

export interface Faculty {
  id: number;
  name: string;
  email: string;
  department: string;
  status: string;
}

export interface Subject {
  id: number;
  name: string;
  code: string;
  branch: string;
  class_id: number;
  class_name?: string;
  faculty_id?: number;
  faculty_name?: string;
}

export interface ClassItem {
  id: number;
  name: string;
  section?: string;
  semester: string;
  department_name?: string;
}

export interface StudentProfile {
  student: Student;
  subjects: string[];
  total_classes: number;
  present: number;
  absent: number;
  attendance_percentage: number;
  attendance_history: AttendanceRecord[];
}

export interface AttendanceSession {
  id: number;
  subject_id: number;
  subject_name: string;
  faculty_id: number;
  faculty_name: string;
  date: string;
  status: string;
  present_count: number;
  total_students: number;
}

export interface AttendanceRecord {
  id: number;
  student_id: number;
  student_name: string;
  roll_number: string;
  subject_id: number;
  subject_name: string;
  date: string;
  time: string;
  status: string;
  recognition_confidence?: number;
}

export interface FaceDetectResult {
  detected: boolean;
  face_count: number;
  message: string;
  bbox?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  quality_score?: number;
}

export interface RecognitionResult {
  recognized: boolean;
  student_id?: number;
  full_name?: string;
  roll_number?: string;
  branch?: string;
  confidence?: number;
  message: string;
  attendance_marked?: boolean;
  already_present?: boolean;
  attendance_time?: string;
  bbox?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

export interface ReportRecord {
  student_name: string;
  roll_number: string;
  subject: string;
  date: string;
  time: string;
  status: string;
  confidence?: number;
}
