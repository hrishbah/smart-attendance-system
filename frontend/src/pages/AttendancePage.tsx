import { useEffect, useState, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Camera,
  Square,
  Play,
  StopCircle,
  UserX,
  CheckCircle,
  AlertTriangle,
} from 'lucide-react';
import {
  api,
  Subject,
  AttendanceSession,
  RecognitionResult,
  AttendanceRecord,
} from '../api/client';
import { useWebcam } from '../hooks/useWebcam';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

interface RecognizedEntry {
  id: string;
  type: 'present' | 'duplicate' | 'unknown';
  name: string;
  roll_number?: string;
  branch?: string;
  confidence?: number;
  time?: string;
  message: string;
}

export default function AttendancePage() {
  const { name } = useAuth();

  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [subjectId, setSubjectId] = useState<number | null>(null);
  const [session, setSession] = useState<AttendanceSession | null>(null);
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [recognized, setRecognized] = useState<RecognizedEntry[]>([]);
  const [scanning, setScanning] = useState(false);

  const [bbox, setBbox] = useState<{
    x: number;
    y: number;
    width: number;
    height: number;
  } | null>(null);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Prevent multiple recognition requests from running at the same time.
  const processingRef = useRef(false);

  // Keeps track of students that have already appeared in this UI.
  const seenStudentsRef = useRef<Set<string>>(new Set());

  const { videoRef, isActive, error, start, stop, captureFrame } = useWebcam();

  // ------------------------------------------------------------
  // LOAD SUBJECTS
  // ------------------------------------------------------------

  useEffect(() => {
    api.getSubjects().then(setSubjects);
  }, []);

  // ------------------------------------------------------------
  // LOAD ATTENDANCE RECORDS
  // ------------------------------------------------------------

  const loadRecords = useCallback(() => {
    if (!session) return;

    api
      .getSessionRecords(session.id)
      .then(setRecords)
      .catch(() => {
        // Ignore temporary record loading errors.
      });
  }, [session]);

  useEffect(() => {
    loadRecords();
  }, [loadRecords]);

  // ------------------------------------------------------------
  // START ATTENDANCE SESSION
  // ------------------------------------------------------------

  const handleStartSession = async () => {
    if (!subjectId) {
      toast.error('Select a subject');
      return;
    }

    try {
      const s = await api.startSession(subjectId);

      setSession(s);
      setRecognized([]);
      setRecords([]);

      seenStudentsRef.current.clear();

      toast.success('Attendance session started');
    } catch (e: unknown) {
      toast.error((e as Error).message);
    }
  };

  // ------------------------------------------------------------
  // END ATTENDANCE SESSION
  // ------------------------------------------------------------

  const handleEndSession = async () => {
    if (!session) return;

    stopScanning();

    try {
      await api.endSession(session.id);

      setSession({
        ...session,
        status: 'ended',
      });

      toast.success('Session ended');
    } catch (e: unknown) {
      toast.error((e as Error).message);
    }
  };

  // ------------------------------------------------------------
  // ADD / UPDATE RECOGNITION ENTRY
  // ------------------------------------------------------------

  const addEntry = useCallback(
    (result: RecognitionResult) => {
      const studentKey =
        result.student_id != null
          ? `student-${result.student_id}`
          : result.roll_number
            ? `roll-${result.roll_number}`
            : 'unknown';

      const entryType: RecognizedEntry['type'] = result.recognized
        ? result.already_present
          ? 'duplicate'
          : 'present'
        : 'unknown';

      const entry: RecognizedEntry = {
        id: studentKey,
        type: entryType,
        name: result.recognized
          ? result.full_name || 'Unknown'
          : 'UNKNOWN FACE',
        roll_number: result.roll_number,
        branch: result.branch,
        confidence: result.confidence,
        time: result.attendance_time,
        message: result.already_present
          ? 'Already Present'
          : result.recognized
            ? 'Attendance Marked'
            : 'Attendance Not Marked',
      };

      setRecognized(prev => {
        // --------------------------------------------------------
        // UNKNOWN FACE
        // --------------------------------------------------------
        // Keep only ONE unknown-face card.
        if (!result.recognized) {
          const alreadyUnknown = prev.some(item => item.id === 'unknown');

          if (alreadyUnknown) {
            return prev;
          }

          return [entry, ...prev].slice(0, 20);
        }

        // --------------------------------------------------------
        // KNOWN STUDENT
        // --------------------------------------------------------
        const existingIndex = prev.findIndex(
          item => item.id === studentKey
        );

        // Student has never appeared in the list.
        if (existingIndex === -1) {
          seenStudentsRef.current.add(studentKey);

          return [entry, ...prev].slice(0, 20);
        }

        // Student already exists.
        // UPDATE the existing card instead of creating another card.
        const updated = [...prev];
        updated[existingIndex] = {
          ...updated[existingIndex],
          ...entry,
          id: studentKey,
        };

        return updated;
      });

      // Refresh today's attendance only when attendance was actually marked.
      if (result.attendance_marked) {
        loadRecords();
      }
    },
    [loadRecords]
  );

  // ------------------------------------------------------------
  // STOP SCANNING
  // ------------------------------------------------------------

  const stopScanning = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    processingRef.current = false;
    setScanning(false);
  }, []);

  // ------------------------------------------------------------
  // START SCANNING
  // ------------------------------------------------------------

  const startScanning = async () => {
    if (!session || session.status === 'ended') {
      toast.error('Start an attendance session first');
      return;
    }

    if (!isActive) {
      await start();
    }

    setScanning(true);

    intervalRef.current = setInterval(async () => {
      // Don't send another request while the previous one is running.
      if (processingRef.current) {
        return;
      }

      processingRef.current = true;

      try {
        const frame = await captureFrame();

        if (!frame || !session) {
          return;
        }

        const result = await api.recognize(session.id, frame);

        setBbox(result.bbox || null);

        // Only display recognized faces and unknown faces.
        if (
          result.recognized ||
          result.message?.toLowerCase().includes('unknown face')
        ) {
          addEntry(result);
        }
      } catch (error) {
        // Ignore individual frame/network errors.
        console.error('Recognition error:', error);
      } finally {
        processingRef.current = false;
      }
    }, 2000);
  };

  // ------------------------------------------------------------
  // CLEANUP
  // ------------------------------------------------------------

  useEffect(() => {
    return () => {
      stopScanning();
      stop();
    };
  }, [stopScanning, stop]);

  // ------------------------------------------------------------
  // CURRENT SUBJECT
  // ------------------------------------------------------------

  const subject = subjects.find(s => s.id === subjectId);

  // ------------------------------------------------------------
  // UI
  // ------------------------------------------------------------

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Live Attendance</h2>

      {/* ------------------------------------------------------ */}
      {/* SUBJECT + SESSION CONTROLS */}
      {/* ------------------------------------------------------ */}

      <div className="flex flex-wrap gap-3 items-end">
        <div>
          <label className="text-sm font-medium">Subject</label>

          <select
            value={subjectId || ''}
            onChange={e => {
              const value = Number(e.target.value);
              setSubjectId(value || null);
            }}
            disabled={!!session && session.status === 'active'}
            className="block mt-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
          >
            <option value="">Select Subject</option>

            {subjects.map(s => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        {!session ? (
          <button
            onClick={handleStartSession}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg"
          >
            <Play size={18} />
            Start Attendance
          </button>
        ) : (
          <button
            onClick={handleEndSession}
            disabled={session.status === 'ended'}
            className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg disabled:opacity-50"
          >
            <StopCircle size={18} />
            End Attendance
          </button>
        )}
      </div>

      {/* ------------------------------------------------------ */}
      {/* SESSION INFORMATION */}
      {/* ------------------------------------------------------ */}

      {session && (
        <div className="flex flex-wrap gap-4 text-sm bg-white dark:bg-gray-800 rounded-lg border p-3">
          <span>
            <strong>Subject:</strong> {session.subject_name}
          </span>

          <span>
            <strong>Faculty:</strong> {name}
          </span>

          <span>
            <strong>Session:</strong>{' '}
            <span
              className={
                session.status === 'active'
                  ? 'text-green-600'
                  : 'text-gray-500'
              }
            >
              {session.status === 'active' ? 'Active' : 'Ended'}
            </span>
          </span>

          <span>
            <strong>Present:</strong> {records.length} /{' '}
            {session.total_students}
          </span>
        </div>
      )}

      {/* ------------------------------------------------------ */}
      {/* MAIN GRID */}
      {/* ------------------------------------------------------ */}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ---------------------------------------------------- */}
        {/* CAMERA */}
        {/* ---------------------------------------------------- */}

        <div className="lg:col-span-2 space-y-3">
          <div className="relative bg-black rounded-xl overflow-hidden aspect-video">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-cover"
            />

            {bbox && isActive && (
              <div
                className="absolute border-2 border-blue-400 rounded"
                style={{
                  left: `${
                    (bbox.x / (videoRef.current?.videoWidth || 1)) * 100
                  }%`,
                  top: `${
                    (bbox.y / (videoRef.current?.videoHeight || 1)) * 100
                  }%`,
                  width: `${
                    (bbox.width / (videoRef.current?.videoWidth || 1)) * 100
                  }%`,
                  height: `${
                    (bbox.height / (videoRef.current?.videoHeight || 1)) * 100
                  }%`,
                }}
              />
            )}

            {!isActive && (
              <div className="absolute inset-0 flex items-center justify-center text-white/60">
                Camera off
              </div>
            )}
          </div>

          {error && (
            <div className="text-red-500 text-sm">
              {error}
            </div>
          )}

          {/* CAMERA BUTTONS */}

          <div className="flex flex-wrap gap-2">
            {!isActive ? (
              <button
                onClick={start}
                className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg"
              >
                <Camera size={18} />
                Start Camera
              </button>
            ) : (
              <button
                onClick={() => {
                  stopScanning();
                  stop();
                  setBbox(null);
                }}
                className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg"
              >
                <Square size={18} />
                Stop Camera
              </button>
            )}

            {!scanning ? (
              <button
                onClick={startScanning}
                disabled={!session || session.status === 'ended' || !isActive}
                className="px-4 py-2 bg-green-600 text-white rounded-lg disabled:opacity-50"
              >
                Start Scanning
              </button>
            ) : (
              <button
                onClick={stopScanning}
                className="px-4 py-2 bg-yellow-600 text-white rounded-lg"
              >
                Stop Scanning
              </button>
            )}
          </div>
        </div>

        {/* ---------------------------------------------------- */}
        {/* RIGHT SIDE */}
        {/* ---------------------------------------------------- */}

        <div className="space-y-4">
          {/* RECOGNIZED STUDENTS */}

          <div className="bg-white dark:bg-gray-800 rounded-xl border p-4 max-h-96 overflow-y-auto">
            <h3 className="font-semibold mb-3">
              Recognized Students
            </h3>

            {recognized.length === 0 && (
              <p className="text-sm text-gray-500">
                Waiting for faces...
              </p>
            )}

            {recognized.map(r => (
              <div
                key={r.id}
                className={`p-3 mb-2 rounded-lg text-sm ${
                  r.type === 'present'
                    ? 'bg-green-50 dark:bg-green-900/20 border border-green-200'
                    : r.type === 'duplicate'
                      ? 'bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200'
                      : 'bg-red-50 dark:bg-red-900/20 border border-red-200'
                }`}
              >
                {/* NAME + ICON */}

                <div className="flex items-center gap-2">
                  {r.type === 'present' ? (
                    <CheckCircle
                      size={16}
                      className="text-green-600"
                    />
                  ) : r.type === 'duplicate' ? (
                    <AlertTriangle
                      size={16}
                      className="text-yellow-600"
                    />
                  ) : (
                    <UserX
                      size={16}
                      className="text-red-600"
                    />
                  )}

                  <span className="font-medium">
                    {r.name}
                  </span>
                </div>

                {/* ROLL + BRANCH */}

                {r.roll_number && (
                  <p className="text-xs mt-1">
                    {r.roll_number}
                    {r.branch ? ` | ${r.branch}` : ''}
                  </p>
                )}

                {/* CONFIDENCE */}

                {r.confidence != null && (
                  <p className="text-xs">
                    Confidence: {Number(r.confidence).toFixed(1)}%
                  </p>
                )}

                {/* STATUS */}

                <p className="text-xs mt-1">
                  {r.type === 'present' && (
                    <span className="text-green-700">
                      ✓ Attendance Marked
                      {r.time ? ` - ${r.time}` : ''}
                    </span>
                  )}

                  {r.type === 'duplicate' && (
                    <span className="text-yellow-700">
                      ⚠ Already Present
                      {r.time ? ` - ${r.time}` : ''}
                    </span>
                  )}

                  {r.type === 'unknown' && (
                    <span className="text-red-700">
                      Not registered
                    </span>
                  )}
                </p>

                {/* REGISTER LINK */}

                {r.type === 'unknown' && (
                  <Link
                    to="/face-registration"
                    className="text-xs text-primary-600 hover:underline mt-1 inline-block"
                  >
                    Register Student →
                  </Link>
                )}
              </div>
            ))}
          </div>

          {/* TODAY'S ATTENDANCE */}

          <div className="bg-white dark:bg-gray-800 rounded-xl border p-4 max-h-64 overflow-y-auto">
            <h3 className="font-semibold mb-3">
              Today's Attendance ({records.length})
            </h3>

            {records.length === 0 && (
              <p className="text-sm text-gray-500">
                No attendance marked yet.
              </p>
            )}

            {records.map(r => (
              <div
                key={r.id}
                className="flex justify-between py-2 border-b border-gray-100 dark:border-gray-700 text-sm"
              >
                <div>
                  <p className="font-medium">
                    {r.student_name}
                  </p>

                  <p className="text-xs text-gray-500">
                    {r.roll_number}
                  </p>
                </div>

                <span className="text-green-600 text-xs">
                  {r.time}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}