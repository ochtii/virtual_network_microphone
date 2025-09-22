package com.sadistic.audiostreamer;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.MediaRecorder;
import android.os.Binder;
import android.os.Build;
import android.os.IBinder;
import android.util.Log;

import androidx.core.app.NotificationCompat;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;

import fi.iki.elonen.NanoHTTPD;

public class AudioStreamingService extends Service {
    private static final String TAG = "AudioStreamingService";
    private static final String CHANNEL_ID = "EvilAudioStreamChannel";
    private static final int NOTIFICATION_ID = 42069;

    // Audio configuration
    private static final int SAMPLE_RATE = 44100;
    private static final int CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO;
    private static final int AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT;
    private static final int BUFFER_SIZE = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT);

    private AudioRecord audioRecord;
    private StreamingServer httpServer;
    private Thread recordingThread;
    private volatile boolean isRecording = false;

    // Voice activation settings
    private volatile boolean voiceActivationEnabled = false;
    private volatile float voiceThreshold = -30.0f; // dB
    private volatile boolean isAboveThreshold = false;

    // Audio level callback
    private AudioLevelCallback audioLevelCallback;

    // Binder for local service binding
    private final IBinder binder = new LocalBinder();

    public interface AudioLevelCallback {
        void onAudioLevel(float dbLevel);
    }

    public class LocalBinder extends Binder {
        AudioStreamingService getService() {
            return AudioStreamingService.this;
        }
    }

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        int port = intent.getIntExtra("port", 42069);
        boolean voiceActivation = intent.getBooleanExtra("voiceActivation", false);
        float threshold = intent.getFloatExtra("threshold", -30.0f);

        this.voiceActivationEnabled = voiceActivation;
        this.voiceThreshold = threshold;

        startForeground(NOTIFICATION_ID, createNotification(port));
        startAudioStreaming(port);

        return START_STICKY; // Keep running even if app is killed
    }

    @Override
    public IBinder onBind(Intent intent) {
        return binder;
    }

    private void startAudioStreaming(int port) {
        try {
            // Initialize audio recording
            audioRecord = new AudioRecord(
                MediaRecorder.AudioSource.MIC,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                BUFFER_SIZE * 2
            );

            // Start HTTP server
            httpServer = new StreamingServer(port);
            httpServer.start();

            // Start recording thread
            isRecording = true;
            recordingThread = new Thread(this::recordAudio);
            recordingThread.start();

            Log.d(TAG, "Audio streaming started on port " + port);

        } catch (Exception e) {
            Log.e(TAG, "Failed to start audio streaming", e);
        }
    }

    private void recordAudio() {
        if (audioRecord == null) return;

        try {
            audioRecord.startRecording();
        } catch (IllegalStateException e) {
            Log.e(TAG, "Failed to start recording", e);
            return;
        }
        
        byte[] audioBuffer = new byte[BUFFER_SIZE];

        while (isRecording && audioRecord != null) {
            try {
                int bytesRead = audioRecord.read(audioBuffer, 0, audioBuffer.length);
                
                if (bytesRead > 0) {
                    // Calculate audio level for voice activation
                    float dbLevel = calculateDbLevel(audioBuffer, bytesRead);
                    
                    // Notify callback of audio level
                    if (audioLevelCallback != null) {
                        audioLevelCallback.onAudioLevel(dbLevel);
                    }

                    // Voice activation logic
                    boolean shouldStream = true;
                    if (voiceActivationEnabled) {
                        isAboveThreshold = dbLevel > voiceThreshold;
                        shouldStream = isAboveThreshold;
                    }

                    // Send audio data to connected clients
                    if (shouldStream && httpServer != null) {
                        httpServer.broadcastAudioData(audioBuffer, bytesRead);
                    }
                }
            } catch (IllegalStateException e) {
                Log.e(TAG, "Error reading audio data", e);
                break;
            }
        }

        // Safe cleanup
        try {
            if (audioRecord != null && audioRecord.getState() == AudioRecord.STATE_INITIALIZED) {
                if (audioRecord.getRecordingState() == AudioRecord.RECORDSTATE_RECORDING) {
                    audioRecord.stop();
                }
                audioRecord.release();
                audioRecord = null;
            }
        } catch (IllegalStateException e) {
            Log.e(TAG, "Error stopping audio record", e);
        }
    }

    private float calculateDbLevel(byte[] audioData, int length) {
        // Convert byte array to short array for processing
        double sum = 0;
        for (int i = 0; i < length - 1; i += 2) {
            short sample = (short) ((audioData[i + 1] << 8) | (audioData[i] & 0xFF));
            sum += sample * sample;
        }

        double rms = Math.sqrt(sum / (length / 2));
        
        if (rms == 0) {
            return -96.0f; // Minimum dB level
        }
        
        // Convert to dB (reference: 32767 for 16-bit audio)
        double db = 20 * Math.log10(rms / 32767.0);
        return (float) Math.max(db, -96.0); // Clamp to minimum
    }

    public void setVoiceActivationEnabled(boolean enabled) {
        this.voiceActivationEnabled = enabled;
    }

    public void setVoiceThreshold(float threshold) {
        this.voiceThreshold = threshold;
    }

    public void setAudioLevelCallback(AudioLevelCallback callback) {
        this.audioLevelCallback = callback;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        stopAudioStreaming();
    }

    private void stopAudioStreaming() {
        isRecording = false;

        if (recordingThread != null) {
            try {
                recordingThread.join(1000);
            } catch (InterruptedException e) {
                Log.e(TAG, "Failed to stop recording thread", e);
            }
        }

        if (httpServer != null) {
            httpServer.stop();
        }

        if (audioRecord != null) {
            audioRecord.release();
            audioRecord = null;
        }

        Log.d(TAG, "Audio streaming stopped");
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "Evil Audio Stream",
                NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Background audio streaming service");
            
            NotificationManager manager = getSystemService(NotificationManager.class);
            manager.createNotificationChannel(channel);
        }
    }

    private Notification createNotification(int port) {
        return new NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle("😈 Audio Stream Active")
                .setContentText("Broadcasting evil at port " + port)
                .setSmallIcon(android.R.drawable.ic_media_play)
                .setOngoing(true)
                .build();
    }

    // Inner class for HTTP streaming server
    private class StreamingServer extends NanoHTTPD {
        public StreamingServer(int port) {
            super(port);
        }

        @Override
        public Response serve(IHTTPSession session) {
            String uri = session.getUri();
            
            if ("/audio".equals(uri)) {
                return serveAudioStream();
            } else {
                return newFixedLengthResponse(Response.Status.OK, "text/html",
                    "<html><body><h1>😈 Sadistic Audio Streamer</h1>" +
                    "<p>Access audio stream at: <a href='/audio'>/audio</a></p>" +
                    "<p>Currently " + (isRecording ? "broadcasting evil" : "dormant") + "</p>" +
                    "</body></html>");
            }
        }

        private Response serveAudioStream() {
            return newChunkedResponse(Response.Status.OK, "audio/wav", new AudioStreamInputStream());
        }

        public void broadcastAudioData(byte[] data, int length) {
            // In a real implementation, this would send data to all connected audio stream clients
            // For simplicity, we'll just log that data is being processed
            // Log.d(TAG, "Broadcasting " + length + " bytes of audio data");
        }
    }

    // Custom InputStream for streaming audio
    private class AudioStreamInputStream extends java.io.InputStream {
        private final byte[] buffer = new byte[BUFFER_SIZE];
        private int bufferPos = 0;
        private int bufferSize = 0;
        
        @Override
        public int read() throws IOException {
            if (bufferPos >= bufferSize) {
                fillBuffer();
                if (bufferSize == 0) {
                    return -1; // EOF
                }
            }
            return buffer[bufferPos++] & 0xFF;
        }

        @Override
        public int read(byte[] b, int off, int len) throws IOException {
            if (bufferPos >= bufferSize) {
                fillBuffer();
                if (bufferSize == 0) {
                    return -1; // EOF
                }
            }

            int available = bufferSize - bufferPos;
            int toRead = Math.min(len, available);
            System.arraycopy(buffer, bufferPos, b, off, toRead);
            bufferPos += toRead;
            return toRead;
        }

        private void fillBuffer() throws IOException {
            if (audioRecord != null && isRecording) {
                bufferSize = audioRecord.read(buffer, 0, buffer.length);
                bufferPos = 0;
                
                // Apply voice activation filter
                if (voiceActivationEnabled && !isAboveThreshold) {
                    // Send silence if below threshold
                    java.util.Arrays.fill(buffer, 0, bufferSize, (byte) 0);
                }
            } else {
                bufferSize = 0;
            }
        }
    }
}