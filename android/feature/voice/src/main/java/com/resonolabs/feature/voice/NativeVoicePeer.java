package com.resonolabs.feature.voice;

import android.content.Context;
import android.media.AudioAttributes;
import android.media.AudioFocusRequest;
import android.media.AudioFormat;
import android.media.AudioManager;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import org.json.JSONObject;

import org.webrtc.AudioTrack;
import org.webrtc.DataChannel;
import org.webrtc.IceCandidate;
import org.webrtc.audio.JavaAudioDeviceModule;
import org.webrtc.MediaConstraints;
import org.webrtc.MediaStream;
import org.webrtc.MediaStreamTrack;
import org.webrtc.PeerConnection;
import org.webrtc.PeerConnectionFactory;
import org.webrtc.RtpReceiver;
import org.webrtc.RtpTransceiver;
import org.webrtc.SdpObserver;
import org.webrtc.SessionDescription;

import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.concurrent.atomic.AtomicBoolean;

public final class NativeVoicePeer {
    private static final String LOG_TAG = "ReSonoVoice";
    public interface Listener {
        void onOffer(String sdp);
        void onLive();
        void onRealtimeEvent(String json);
        void onFailure(String reason);
        /** Runs on the capture thread: only copy/enqueue into a bounded audio queue here. */
        default void onAudioFrame(byte[] pcm, long captureTimeNanos) { }
        /** Runs on the main thread after the native recorder reports its actual state. */
        default void onCaptureChanged(boolean capturing) { }
    }

    private static final Object FACTORY_LOCK = new Object();
    private static boolean initialized;

    private final Context context;
    private final Listener listener;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final AtomicBoolean offerDelivered = new AtomicBoolean();
    private final AtomicBoolean failurePosted = new AtomicBoolean();
    private final AtomicBoolean bufferedUpdatePosted = new AtomicBoolean();
    private final Object captureLock = new Object();
    // Native handles belong to the main thread. The audio callback never touches them.
    private JavaAudioDeviceModule audioDevice;
    private PeerConnectionFactory factory;
    private PeerConnection peer;
    private DataChannel dataChannel;
    private AudioManager audioManager;
    private AudioFocusRequest audioFocusRequest;
    private int previousAudioMode = AudioManager.MODE_NORMAL;
    private boolean previousSpeakerphoneOn;
    private volatile boolean closed;
    private volatile boolean captureEnabled;
    private volatile boolean playbackEnabled = true;
    private volatile long dataChannelBufferedBytes;
    private long captureOpenedAtNanos;
    // Per-press aggregate diagnostics only: never retain audio or transcript content.
    private long captureFrameCount;
    private long captureByteCount;
    private long staleCaptureFrameCount;
    private int capturePeak;
    private boolean recordingRequested;
    private volatile long recordingGeneration;
    private boolean capturing;

    public NativeVoicePeer(Context context, Listener listener) {
        this.context = context.getApplicationContext();
        this.listener = listener;
    }

    public void createOffer() {
        onMain(this::createOfferOnMain);
    }

    private void createOfferOnMain() {
        if (closed || factory != null) return;
        try {
            ensureInitialized();
            audioManager = (AudioManager) context.getSystemService(Context.AUDIO_SERVICE);
            if (audioManager == null) throw new IllegalStateException("audio manager unavailable");
            previousAudioMode = audioManager.getMode();
            previousSpeakerphoneOn = audioManager.isSpeakerphoneOn();
            AudioAttributes playbackAttributes = new AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build();
            audioFocusRequest = new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT)
                    .setAudioAttributes(playbackAttributes)
                    .setWillPauseWhenDucked(true)
                    .setOnAudioFocusChangeListener(change -> {
                        if (change == AudioManager.AUDIOFOCUS_LOSS
                                || change == AudioManager.AUDIOFOCUS_LOSS_TRANSIENT
                                || change == AudioManager.AUDIOFOCUS_LOSS_TRANSIENT_CAN_DUCK) {
                            fail("audio-focus-lost");
                        }
                    })
                    .build();
            if (audioManager.requestAudioFocus(audioFocusRequest) != AudioManager.AUDIOFOCUS_REQUEST_GRANTED) {
                throw new IllegalStateException("audio focus unavailable");
            }
            // Match the R1's full-range media/notification speaker path. MODE_IN_COMMUNICATION
            // selects the quieter voice-call curve, while Settings controls STREAM_MUSIC.
            audioManager.setMode(AudioManager.MODE_NORMAL);
            audioManager.setSpeakerphoneOn(true);
            JavaAudioDeviceModule.Builder audioBuilder = JavaAudioDeviceModule.builder(context);
            audioBuilder.setAudioAttributes(playbackAttributes);
            audioBuilder.setUseLowLatency(true);
            audioBuilder.setEnableVolumeLogger(true);
            audioBuilder.setInputSampleRate(24_000);
            audioBuilder.setUseStereoInput(false);
            audioBuilder.setAudioFormat(AudioFormat.ENCODING_PCM_16BIT);
            audioBuilder.setUseHardwareAcousticEchoCanceler(
                    JavaAudioDeviceModule.isBuiltInAcousticEchoCancelerSupported());
            audioBuilder.setUseHardwareNoiseSuppressor(
                    JavaAudioDeviceModule.isBuiltInNoiseSuppressorSupported());
            audioBuilder.setAudioBufferCallback(this::captureAudio);
            audioBuilder.setAudioRecordStateCallback(new JavaAudioDeviceModule.AudioRecordStateCallback() {
                @Override public void onWebRtcAudioRecordStart() { recordingChanged(true); }
                @Override public void onWebRtcAudioRecordStop() { recordingChanged(false); }
            });
            audioBuilder.setAudioRecordErrorCallback(new JavaAudioDeviceModule.AudioRecordErrorCallback() {
                @Override public void onWebRtcAudioRecordInitError(String error) { fail("audio-record-init-failed"); }
                @Override public void onWebRtcAudioRecordStartError(
                        JavaAudioDeviceModule.AudioRecordStartErrorCode code, String error) {
                    fail("audio-record-start-failed");
                }
                @Override public void onWebRtcAudioRecordError(String error) { fail("audio-record-failed"); }
            });
            audioBuilder.setAudioTrackErrorCallback(new JavaAudioDeviceModule.AudioTrackErrorCallback() {
                @Override public void onWebRtcAudioTrackInitError(String error) { fail("audio-playback-init-failed"); }
                @Override public void onWebRtcAudioTrackStartError(
                        JavaAudioDeviceModule.AudioTrackStartErrorCode code, String error) {
                    fail("audio-playback-start-failed");
                }
                @Override public void onWebRtcAudioTrackError(String error) { fail("audio-playback-failed"); }
            });
            audioDevice = audioBuilder.createAudioDeviceModule();
            audioDevice.setSpeakerMute(!playbackEnabled);
            // This pinned ADM can start AudioRecord before SDP negotiation completes.
            updateCapture();
            if (failurePosted.get()) return;
            factory = PeerConnectionFactory.builder()
                    .setAudioDeviceModule(audioDevice)
                    .createPeerConnectionFactory();
            PeerConnection.RTCConfiguration config = new PeerConnection.RTCConfiguration(
                    Collections.emptyList());
            config.sdpSemantics = PeerConnection.SdpSemantics.UNIFIED_PLAN;
            peer = factory.createPeerConnection(config, new PeerObserver());
            if (peer == null) throw new IllegalStateException("peer creation failed");

            // PCM appends and commit share the ordered channel; never duplicate input via RTP.
            peer.addTransceiver(MediaStreamTrack.MediaType.MEDIA_TYPE_AUDIO,
                    new RtpTransceiver.RtpTransceiverInit(
                            RtpTransceiver.RtpTransceiverDirection.RECV_ONLY));

            DataChannel.Init init = new DataChannel.Init();
            init.ordered = true;
            dataChannel = peer.createDataChannel("oai-events", init);
            if (dataChannel == null) throw new IllegalStateException("data channel creation failed");
            dataChannel.registerObserver(new DataObserver());
            peer.createOffer(new OfferObserver(), new MediaConstraints());
        } catch (Exception exception) {
            fail("peer-start-failed");
        }
    }

    public void applyAnswer(String sdp) {
        onMain(() -> applyAnswerOnMain(sdp));
    }

    private void applyAnswerOnMain(String sdp) {
        if (closed) return;
        if (peer == null || sdp == null || sdp.isBlank()) {
            fail("answer-invalid");
            return;
        }
        peer.setRemoteDescription(new SimpleSdpObserver() {
            @Override
            public void onSetSuccess() {
                Log.i(LOG_TAG, "remote WebRTC answer accepted");
            }

            @Override
            public void onSetFailure(String error) {
                Log.w(LOG_TAG, "remote WebRTC answer rejected");
                fail("answer-rejected");
            }
        }, new SessionDescription(SessionDescription.Type.ANSWER, sdp));
    }

    public boolean sendRealtimeEvent(JSONObject event) {
        if (Looper.myLooper() != handler.getLooper() || closed || event == null
                || dataChannel == null || dataChannel.state() != DataChannel.State.OPEN) return false;
        byte[] bytes = event.toString().getBytes(StandardCharsets.UTF_8);
        // Reserve before send so concurrent capture conservatively sees the new backlog.
        dataChannelBufferedBytes = dataChannel.bufferedAmount() + bytes.length;
        boolean sent = dataChannel.send(new DataChannel.Buffer(ByteBuffer.wrap(bytes), false));
        dataChannelBufferedBytes = dataChannel.bufferedAmount();
        return sent;
    }

    /** Thread-safe conservative snapshot; no JNI work on the capture thread. */
    public long bufferedAmount() { return dataChannelBufferedBytes; }

    /** Refresh on the native owner's thread; other threads retain snapshot-only access. */
    long refreshBufferedAmount() {
        if (Looper.myLooper() == handler.getLooper() && !closed && dataChannel != null) {
            dataChannelBufferedBytes = dataChannel.bufferedAmount();
        }
        return dataChannelBufferedBytes;
    }

    /** Closes admission synchronously, even if stopping the native recorder takes longer. */
    public void setCaptureEnabled(boolean enabled) {
        synchronized (captureLock) {
            if (closed || failurePosted.get()) return;
            if (enabled && !captureEnabled) {
                captureOpenedAtNanos = System.nanoTime();
                captureFrameCount = captureByteCount = staleCaptureFrameCount = 0;
                capturePeak = 0;
            } else if (!enabled && captureEnabled) {
                Log.i(LOG_TAG, "PTT capture closed frames=" + captureFrameCount
                        + " bytes=" + captureByteCount + " staleFrames=" + staleCaptureFrameCount
                        + " peak=" + capturePeak);
            }
            captureEnabled = enabled;
        }
        onMain(this::updateCapture);
    }

    /** Mutes locally while native decoding/playout keeps consuming the remote stream. */
    public void setPlaybackEnabled(boolean enabled) {
        playbackEnabled = enabled;
        onMain(() -> {
            if (!closed && audioDevice != null) audioDevice.setSpeakerMute(!playbackEnabled);
        });
    }

    private void updateCapture() {
        if (closed || audioDevice == null || recordingRequested == captureEnabled) return;
        try {
            recordingGeneration++;
            recordingRequested = captureEnabled;
            if (recordingRequested) audioDevice.requestStartRecording();
            else audioDevice.requestStopRecording();
        } catch (RuntimeException | AssertionError exception) {
            // The pinned ADM may assert after reporting an AudioRecord init failure.
            fail("audio-capture-change-failed");
        }
    }

    private long captureAudio(ByteBuffer buffer, int format, int channels, int sampleRate,
                              int bytesRead, long captureTimeNanos) {
        synchronized (captureLock) {
            if (closed || !captureEnabled || failurePosted.get()) return captureTimeNanos;
            if (format != AudioFormat.ENCODING_PCM_16BIT || channels != 1 || sampleRate != 24_000
                    || bytesRead <= 0 || (bytesRead & 1) != 0 || bytesRead > buffer.capacity()) {
                fail("audio-capture-format-invalid");
                return captureTimeNanos;
            }
            // The SDK supplies a CLOCK_MONOTONIC timestamp, or zero when unavailable.
            long timestamp = captureTimeNanos > 0 ? captureTimeNanos : System.nanoTime();
            if (timestamp < captureOpenedAtNanos) {
                staleCaptureFrameCount++;
                return captureTimeNanos;
            }
            byte[] pcm = new byte[bytesRead];
            ByteBuffer source = buffer.duplicate();
            source.position(0);
            source.limit(bytesRead);
            source.get(pcm);
            captureFrameCount++;
            captureByteCount += bytesRead;
            for (int offset = 0; offset < pcm.length; offset += 2) {
                int sample = (short) ((pcm[offset] & 0xff) | (pcm[offset + 1] << 8));
                capturePeak = Math.max(capturePeak, Math.abs(sample));
            }
            listener.onAudioFrame(pcm, timestamp);
        }
        return captureTimeNanos;
    }

    private void recordingChanged(boolean started) {
        long generation = recordingGeneration;
        handler.post(() -> {
            if (closed || generation != recordingGeneration) return;
            boolean active = started && captureEnabled && !failurePosted.get();
            if (active && audioDevice != null) {
                // The capture callback precedes native software APM: report platform effects only.
                JavaAudioDeviceModule.PlatformAudioProcessingState state =
                        audioDevice.getPlatformAudioProcessingState();
                Log.i(LOG_TAG, "capture platform AEC active=" + state.echoCancellation.isActive
                        + " available=" + state.echoCancellation.isAvailable
                        + " NS active=" + state.noiseSuppression.isActive
                        + " available=" + state.noiseSuppression.isAvailable);
            }
            if (capturing != active) {
                capturing = active;
                listener.onCaptureChanged(active);
            }
            if (!started && captureEnabled && !failurePosted.get()) fail("audio-record-stopped");
        });
    }

    public void close() {
        synchronized (captureLock) {
            if (closed) return;
            closed = true;
            captureEnabled = false;
        }
        onMain(this::closeOnMain);
    }

    private void closeOnMain() {
        handler.removeCallbacksAndMessages(null);
        if (audioDevice != null) {
            audioDevice.setSpeakerMute(true);
            audioDevice.requestStopRecording();
        }
        if (dataChannel != null) {
            dataChannel.unregisterObserver();
            dataChannel.close();
            dataChannel.dispose();
        }
        if (peer != null) {
            peer.close();
            peer.dispose();
        }
        if (factory != null) factory.dispose();
        if (audioDevice != null) audioDevice.release();
        dataChannel = null;
        peer = null;
        factory = null;
        audioDevice = null;
        dataChannelBufferedBytes = 0;
        if (audioManager != null) {
            if (audioFocusRequest != null) audioManager.abandonAudioFocusRequest(audioFocusRequest);
            audioManager.setSpeakerphoneOn(previousSpeakerphoneOn);
            audioManager.setMode(previousAudioMode);
        }
        if (capturing) {
            capturing = false;
            listener.onCaptureChanged(false);
        }
    }

    private void onMain(Runnable action) {
        if (Looper.myLooper() == handler.getLooper()) action.run();
        else handler.post(action);
    }

    private void ensureInitialized() {
        synchronized (FACTORY_LOCK) {
            if (initialized) return;
            PeerConnectionFactory.initialize(
                    PeerConnectionFactory.InitializationOptions.builder(context)
                            .setEnableInternalTracer(false)
                            .createInitializationOptions());
            initialized = true;
        }
    }

    private void deliverOffer() {
        if (closed || peer == null || !offerDelivered.compareAndSet(false, true)) return;
        SessionDescription local = peer.getLocalDescription();
        if (local == null || local.description == null || local.description.isBlank()) {
            fail("local-sdp-missing");
            return;
        }
        Log.i(LOG_TAG, "local WebRTC offer ready");
        listener.onOffer(local.description);
    }

    private void fail(String reason) {
        if (closed || !failurePosted.compareAndSet(false, true)) return;
        synchronized (captureLock) { captureEnabled = false; }
        // Never release native recording/peer handles from one of their own callbacks.
        handler.post(() -> {
            if (closed) return;
            Log.w(LOG_TAG, "native peer failure reason=" + reason);
            close();
            listener.onFailure(reason);
        });
    }

    /**
     * ICE CLOSED is also emitted when this client deliberately tears down its peer.  The
     * data-channel observer is the authoritative unexpected-transport-close signal; only
     * ICE FAILED denotes an ICE connectivity failure here.
     */
    static boolean isIceConnectivityFailure(PeerConnection.IceConnectionState state) {
        return state == PeerConnection.IceConnectionState.FAILED;
    }

    private final class OfferObserver extends SimpleSdpObserver {
        @Override
        public void onCreateSuccess(SessionDescription offer) {
            handler.post(() -> {
                if (closed || peer == null) return;
                peer.setLocalDescription(new SimpleSdpObserver() {
                    @Override
                    public void onSetSuccess() {
                        handler.postDelayed(NativeVoicePeer.this::deliverOffer, 800);
                    }

                    @Override
                    public void onSetFailure(String error) {
                        fail("local-sdp-rejected");
                    }
                }, offer);
            });
        }

        @Override
        public void onCreateFailure(String error) {
            fail("offer-failed");
        }
    }

    private final class PeerObserver implements PeerConnection.Observer {
        @Override public void onSignalingChange(PeerConnection.SignalingState state) {
            Log.i(LOG_TAG, "WebRTC signaling state=" + state);
        }
        @Override public void onIceConnectionChange(PeerConnection.IceConnectionState state) {
            Log.i(LOG_TAG, "WebRTC ICE state=" + state);
            if (isIceConnectivityFailure(state)) fail("ice-failed");
        }
        @Override public void onIceConnectionReceivingChange(boolean receiving) {}
        @Override public void onIceGatheringChange(PeerConnection.IceGatheringState state) {
            Log.i(LOG_TAG, "WebRTC ICE gathering=" + state);
            if (state == PeerConnection.IceGatheringState.COMPLETE) {
                handler.post(NativeVoicePeer.this::deliverOffer);
            }
        }
        @Override public void onIceCandidate(IceCandidate candidate) {}
        @Override public void onIceCandidatesRemoved(IceCandidate[] candidates) {}
        @Override public void onAddStream(MediaStream stream) {}
        @Override public void onRemoveStream(MediaStream stream) {}
        @Override public void onDataChannel(DataChannel channel) {}
        @Override public void onRenegotiationNeeded() {}
        @Override public void onAddTrack(RtpReceiver receiver, MediaStream[] streams) {
            handler.post(() -> {
                if (!closed && receiver.track() instanceof AudioTrack remote) remote.setEnabled(true);
            });
        }
    }

    private final class DataObserver implements DataChannel.Observer {
        @Override public void onBufferedAmountChange(long previousAmount) {
            if (closed || !bufferedUpdatePosted.compareAndSet(false, true)) return;
            handler.post(() -> {
                bufferedUpdatePosted.set(false);
                refreshBufferedAmount();
            });
        }
        @Override public void onStateChange() {
            handler.post(() -> {
                if (dataChannel == null || closed) return;
                DataChannel.State state = dataChannel.state();
                Log.i(LOG_TAG, "WebRTC data channel=" + state);
                if (state == DataChannel.State.OPEN) listener.onLive();
                if (state == DataChannel.State.CLOSED) fail("data-channel-closed");
            });
        }
        @Override public void onMessage(DataChannel.Buffer buffer) {
            if (closed) return;
            if (buffer.binary || buffer.data.remaining() > 262_144) {
                fail("data-channel-message-invalid");
                return;
            }
            ByteBuffer source = buffer.data.slice();
            byte[] bytes = new byte[source.remaining()];
            source.get(bytes);
            String json = new String(bytes, StandardCharsets.UTF_8);
            handler.post(() -> {
                if (!closed) listener.onRealtimeEvent(json);
            });
        }
    }

    private abstract static class SimpleSdpObserver implements SdpObserver {
        @Override public void onCreateSuccess(SessionDescription description) {}
        @Override public void onSetSuccess() {}
        @Override public void onCreateFailure(String error) {}
        @Override public void onSetFailure(String error) {}
    }
}
