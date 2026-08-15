package com.resonolabs.feature.voice;

import android.content.Context;
import android.media.AudioAttributes;
import android.media.AudioFocusRequest;
import android.media.AudioManager;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import org.json.JSONObject;

import org.webrtc.AudioSource;
import org.webrtc.AudioTrack;
import org.webrtc.DataChannel;
import org.webrtc.IceCandidate;
import org.webrtc.audio.JavaAudioDeviceModule;
import org.webrtc.MediaConstraints;
import org.webrtc.MediaStream;
import org.webrtc.PeerConnection;
import org.webrtc.PeerConnectionFactory;
import org.webrtc.RtpReceiver;
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
    }

    private static final Object FACTORY_LOCK = new Object();
    private static boolean initialized;

    private final Context context;
    private final Listener listener;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final AtomicBoolean offerDelivered = new AtomicBoolean();
    private JavaAudioDeviceModule audioDevice;
    private PeerConnectionFactory factory;
    private PeerConnection peer;
    private AudioSource audioSource;
    private AudioTrack audioTrack;
    private DataChannel dataChannel;
    private AudioManager audioManager;
    private AudioFocusRequest audioFocusRequest;
    private int previousAudioMode = AudioManager.MODE_NORMAL;
    private boolean previousSpeakerphoneOn;
    private boolean closed;

    public NativeVoicePeer(Context context, Listener listener) {
        this.context = context.getApplicationContext();
        this.listener = listener;
    }

    public void createOffer() {
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
                    .setOnAudioFocusChangeListener(change -> { })
                    .build();
            audioManager.requestAudioFocus(audioFocusRequest);
            // Match the R1's full-range media/notification speaker path. MODE_IN_COMMUNICATION
            // selects the quieter voice-call curve, while Settings controls STREAM_MUSIC.
            audioManager.setMode(AudioManager.MODE_NORMAL);
            audioManager.setSpeakerphoneOn(true);
            JavaAudioDeviceModule.Builder audioBuilder = JavaAudioDeviceModule.builder(context);
            audioBuilder.setAudioAttributes(playbackAttributes);
            audioBuilder.setUseLowLatency(true);
            audioBuilder.setEnableVolumeLogger(true);
            audioBuilder.setUseHardwareAcousticEchoCanceler(
                    JavaAudioDeviceModule.isBuiltInAcousticEchoCancelerSupported());
            audioBuilder.setUseHardwareNoiseSuppressor(
                    JavaAudioDeviceModule.isBuiltInNoiseSuppressorSupported());
            audioDevice = audioBuilder.createAudioDeviceModule();
            factory = PeerConnectionFactory.builder()
                    .setAudioDeviceModule(audioDevice)
                    .createPeerConnectionFactory();
            PeerConnection.RTCConfiguration config = new PeerConnection.RTCConfiguration(
                    Collections.emptyList());
            config.sdpSemantics = PeerConnection.SdpSemantics.UNIFIED_PLAN;
            peer = factory.createPeerConnection(config, new PeerObserver());
            if (peer == null) throw new IllegalStateException("peer creation failed");

            audioSource = factory.createAudioSource(new MediaConstraints());
            audioTrack = factory.createAudioTrack("resono-microphone", audioSource);
            audioTrack.setEnabled(true);
            peer.addTrack(audioTrack, Collections.singletonList("resono-audio"));

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
        if (closed || peer == null || sdp == null || sdp.isBlank()) {
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
        if (closed || dataChannel == null || dataChannel.state() != DataChannel.State.OPEN) return false;
        byte[] bytes = event.toString().getBytes(StandardCharsets.UTF_8);
        return dataChannel.send(new DataChannel.Buffer(ByteBuffer.wrap(bytes), false));
    }

    public void close() {
        if (closed) return;
        closed = true;
        handler.removeCallbacksAndMessages(null);
        if (audioTrack != null) audioTrack.setEnabled(false);
        if (dataChannel != null) {
            dataChannel.unregisterObserver();
            dataChannel.close();
            dataChannel.dispose();
        }
        if (peer != null) {
            peer.close();
            peer.dispose();
        }
        if (audioTrack != null) audioTrack.dispose();
        if (audioSource != null) audioSource.dispose();
        if (factory != null) factory.dispose();
        if (audioDevice != null) audioDevice.release();
        if (audioManager != null) {
            if (audioFocusRequest != null) audioManager.abandonAudioFocusRequest(audioFocusRequest);
            audioManager.setSpeakerphoneOn(previousSpeakerphoneOn);
            audioManager.setMode(previousAudioMode);
        }
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
        Log.w(LOG_TAG, "native peer failure reason=" + reason);
        close();
        listener.onFailure(reason);
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
            if (state == PeerConnection.IceGatheringState.COMPLETE) deliverOffer();
        }
        @Override public void onIceCandidate(IceCandidate candidate) {}
        @Override public void onIceCandidatesRemoved(IceCandidate[] candidates) {}
        @Override public void onAddStream(MediaStream stream) {}
        @Override public void onRemoveStream(MediaStream stream) {}
        @Override public void onDataChannel(DataChannel channel) {}
        @Override public void onRenegotiationNeeded() {}
        @Override public void onAddTrack(RtpReceiver receiver, MediaStream[] streams) {
            if (receiver.track() instanceof AudioTrack remote) remote.setEnabled(true);
        }
    }

    private final class DataObserver implements DataChannel.Observer {
        @Override public void onBufferedAmountChange(long previousAmount) {}
        @Override public void onStateChange() {
            if (dataChannel == null || closed) return;
            Log.i(LOG_TAG, "WebRTC data channel=" + dataChannel.state());
            if (dataChannel.state() == DataChannel.State.OPEN) listener.onLive();
            if (dataChannel.state() == DataChannel.State.CLOSED) fail("data-channel-closed");
        }
        @Override public void onMessage(DataChannel.Buffer buffer) {
            if (buffer.binary || buffer.data.remaining() > 262_144) {
                fail("data-channel-message-invalid");
                return;
            }
            ByteBuffer source = buffer.data.slice();
            byte[] bytes = new byte[source.remaining()];
            source.get(bytes);
            listener.onRealtimeEvent(new String(bytes, StandardCharsets.UTF_8));
        }
    }

    private abstract static class SimpleSdpObserver implements SdpObserver {
        @Override public void onCreateSuccess(SessionDescription description) {}
        @Override public void onSetSuccess() {}
        @Override public void onCreateFailure(String error) {}
        @Override public void onSetFailure(String error) {}
    }
}

