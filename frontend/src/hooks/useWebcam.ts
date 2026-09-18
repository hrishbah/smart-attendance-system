import { useRef, useState, useCallback, useEffect } from 'react';

export interface WebcamState {
  stream: MediaStream | null;
  error: string | null;
  isActive: boolean;
  videoRef: React.RefObject<HTMLVideoElement>;
  start: () => Promise<void>;
  stop: () => void;
  captureFrame: () => Promise<Blob | null>;
}

export function useWebcam(): WebcamState {
  const videoRef = useRef<HTMLVideoElement>(null!);
  const streamRef = useRef<MediaStream | null>(null);

  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isActive, setIsActive] = useState(false);

  const stop = useCallback(() => {
    const currentStream = streamRef.current;

    if (currentStream) {
      currentStream.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.srcObject = null;
    }

    setStream(null);
    setIsActive(false);
  }, []);

  const start = useCallback(async () => {
    setError(null);

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('Camera not supported in this browser');
      }

      // Stop any existing camera first
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }

      const media = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'user',
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });

      streamRef.current = media;
      setStream(media);

      setIsActive(true);
    } catch (e: unknown) {
      const err = e as Error;

      if (err.name === 'NotAllowedError') {
        setError(
          'Camera permission denied. Please allow camera access in your browser settings and reload.'
        );
      } else if (err.name === 'NotFoundError') {
        setError('No camera detected.');
      } else if (err.name === 'NotReadableError') {
        setError('Camera is already being used by another application.');
      } else {
        setError(err.message || 'Failed to access camera');
      }

      setIsActive(false);
    }
  }, []);

  // Attach the stream to the video element after React has rendered it.
  useEffect(() => {
    const video = videoRef.current;
    const currentStream = streamRef.current;

    if (!video || !currentStream) return;

    video.srcObject = currentStream;
    video.muted = true;
    video.playsInline = true;

    const playVideo = async () => {
      try {
        await video.play();
      } catch (err) {
        console.error('Video playback error:', err);
      }
    };

    playVideo();

    return () => {
      if (video.srcObject === currentStream) {
        video.pause();
        video.srcObject = null;
      }
    };
  }, [stream]);

  const captureFrame = useCallback(async (): Promise<Blob | null> => {
    const video = videoRef.current;

    if (!video || !isActive) {
      return null;
    }

    if (video.readyState < 2 || video.videoWidth === 0) {
      return null;
    }

    const canvas = document.createElement('canvas');

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext('2d');

    if (!ctx) {
      return null;
    }

    ctx.drawImage(video, 0, 0);

    return new Promise(resolve => {
      canvas.toBlob(
        blob => resolve(blob),
        'image/jpeg',
        0.92
      );
    });
  }, [isActive]);

  // Cleanup only when the hook/component is actually unmounted.
  useEffect(() => {
    return () => {
      const currentStream = streamRef.current;

      if (currentStream) {
        currentStream.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
    };
  }, []);

  return {
    stream,
    error,
    isActive,
    videoRef,
    start,
    stop,
    captureFrame,
  };
}