import { useEffect, useState, useRef, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Camera, Square, CheckCircle, AlertCircle } from 'lucide-react';
import { api, Student } from '../api/client';
import { useWebcam } from '../hooks/useWebcam';
import toast from 'react-hot-toast';

const TARGET_SAMPLES = 15;

export default function FaceRegistrationPage() {
  const [searchParams] = useSearchParams();
  const [students, setStudents] = useState<Student[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [samples, setSamples] = useState<Blob[]>([]);
  const [status, setStatus] = useState('');
  const [capturing, setCapturing] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [bbox, setBbox] = useState<{ x: number; y: number; width: number; height: number } | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { videoRef, isActive, error, start, stop, captureFrame } = useWebcam();

  useEffect(() => {
    api.getStudents({ per_page: '100' }).then(r => {
      const unregistered = r.items.filter(s => s.face_status !== 'registered');
      setStudents([...r.items.filter(s => s.face_status === 'registered'), ...unregistered]);
    });
    const sid = searchParams.get('student');
    if (sid) setSelectedId(Number(sid));
  }, [searchParams]);

  const stopCapture = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = null;
    setCapturing(false);
  }, []);

  const startCapture = async () => {
    if (!selectedId) { toast.error('Select a student first'); return; }
    if (!isActive) await start();
    setSamples([]);
    setCapturing(true);
    setStatus('Position your face in the frame...');

    intervalRef.current = setInterval(async () => {
      const frame = await captureFrame();
      if (!frame) return;
      try {
        const result = await api.detectFace(frame);
        setBbox(result.bbox || null);
        if (result.detected && (result.quality_score ?? 0) >= 0.4) {
          setSamples(prev => {
            if (prev.length >= TARGET_SAMPLES) return prev;
            const newSamples = [...prev, frame];
            setStatus(`Captured ${newSamples.length}/${TARGET_SAMPLES} samples`);
            if (newSamples.length >= TARGET_SAMPLES) {
              stopCapture();
              setStatus('All samples captured! Click Register Face.');
            }
            return newSamples;
          });
        } else {
          setStatus(result.message);
        }
      } catch {
        setStatus('Detection error - retrying...');
      }
    }, 800);
  };

  const handleRegister = async () => {
    if (!selectedId || samples.length < 10) {
      toast.error('Need at least 10 quality samples');
      return;
    }
    setRegistering(true);
    try {
      const result = await api.registerFace(selectedId, samples);
      toast.success(result.message);
      setStatus('Face successfully registered.');
      setSamples([]);
      api.getStudents({ per_page: '100' }).then(r => setStudents(r.items));
    } catch (e: unknown) {
      toast.error((e as Error).message);
    } finally {
      setRegistering(false);
    }
  };

  useEffect(() => () => { stopCapture(); stop(); }, [stopCapture, stop]);

  const selected = students.find(s => s.id === selectedId);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Register Student Face</h2>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium">Select Student</label>
            <select value={selectedId || ''} onChange={e => setSelectedId(Number(e.target.value))}
              className="w-full mt-1 px-3 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800">
              <option value="">-- Select Student --</option>
              {students.map(s => (
                <option key={s.id} value={s.id}>{s.full_name} ({s.roll_number}) - {s.face_status === 'registered' ? 'Registered' : 'Not Registered'}</option>
              ))}
            </select>
          </div>
          {selected && (
            <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg text-sm">
              <p><strong>{selected.full_name}</strong></p>
              <p>Roll: {selected.roll_number} | {selected.branch}</p>
            </div>
          )}
          <div className="relative bg-black rounded-xl overflow-hidden aspect-video">
            <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
            {bbox && isActive && (
              <div className="absolute border-2 border-green-400 rounded"
                style={{ left: `${(bbox.x / (videoRef.current?.videoWidth || 1)) * 100}%`, top: `${(bbox.y / (videoRef.current?.videoHeight || 1)) * 100}%`, width: `${(bbox.width / (videoRef.current?.videoWidth || 1)) * 100}%`, height: `${(bbox.height / (videoRef.current?.videoHeight || 1)) * 100}%` }} />
            )}
            {!isActive && !error && (
              <div className="absolute inset-0 flex items-center justify-center text-white/70">Camera off</div>
            )}
          </div>
          {error && (
            <div className="flex items-start gap-2 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg text-sm">
              <AlertCircle size={18} className="mt-0.5 shrink-0" />
              <div>
                <p>{error}</p>
                <p className="mt-1 text-xs opacity-80">Go to browser settings → Site permissions → Camera → Allow</p>
              </div>
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            {!isActive ? (
              <button onClick={start} className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg"><Camera size={18} /> Start Camera</button>
            ) : (
              <button onClick={() => { stopCapture(); stop(); }} className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg"><Square size={18} /> Stop Camera</button>
            )}
            {!capturing ? (
              <button onClick={startCapture} disabled={!selectedId || !isActive} className="px-4 py-2 bg-green-600 text-white rounded-lg disabled:opacity-50">Start Capture</button>
            ) : (
              <button onClick={stopCapture} className="px-4 py-2 bg-yellow-600 text-white rounded-lg">Stop Capture</button>
            )}
            <button onClick={handleRegister} disabled={samples.length < 10 || registering}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg disabled:opacity-50">
              {registering ? 'Registering...' : `Register Face (${samples.length} samples)`}
            </button>
          </div>
        </div>
        <div className="space-y-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl border p-5">
            <h3 className="font-semibold mb-3">Registration Guide</h3>
            <ol className="text-sm space-y-2 text-gray-600 dark:text-gray-400 list-decimal list-inside">
              <li>Select the student from the dropdown</li>
              <li>Click "Start Camera" and allow permissions</li>
              <li>Position face in center of frame</li>
              <li>Click "Start Capture" - system captures ~15 samples</li>
              <li>Slightly move head left/right during capture</li>
              <li>Click "Register Face" when done</li>
            </ol>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl border p-5">
            <h3 className="font-semibold mb-2">Status</h3>
            <p className="text-sm">{status || 'Ready'}</p>
            <div className="mt-3 flex items-center gap-2">
              <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div className="bg-primary-600 h-2 rounded-full transition-all" style={{ width: `${(samples.length / TARGET_SAMPLES) * 100}%` }} />
              </div>
              <span className="text-sm font-medium">{samples.length}/{TARGET_SAMPLES}</span>
            </div>
            {samples.length >= 10 && (
              <p className="mt-2 flex items-center gap-1 text-green-600 text-sm"><CheckCircle size={16} /> Enough samples to register</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
