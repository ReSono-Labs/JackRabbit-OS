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

import org.webrtc.AudioSource;
import org.webrtc.AudioTrack;
import org.webrtc.DataChannel;
import org.webrtc.IceCandidate;
import org.webrtc.audio.JavaAudioDeviceModule;
import org.webrtc.MediaConstraints;
import org.webrtc.MediaStream;
import org.webrtc.PeerConnection;
import org.webrtc.PeerConnectionFactory;
import org.webrtc.RTCStatsCollectorCallback;
import org.webrtc.RTCStatsReport;
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
    private static final int PCM_SAMPLE_RATE = 24_000;

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
    private android.media.AudioTrack pcmTrack;
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
            // The Voice backends (product /realtime/wm and Codex AVAS) expect a
            // pre-negotiated stream id 0; in-band negotiation gets the channel closed.
            init.negotiated = true;
            init.id = 0;
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
        applyAnswerVariant(sdp, "original");
    }

    /**
     * The AVAS broker answer fails to parse in the M144 WebRTC SDK
     * ("SessionDescription is NULL."), while the structurally identical realtime
     * 2.1 answer parses. On failure we retry with bisected variants to isolate
     * the offending attribute.
     */
    private void applyAnswerVariant(String sdp, String label) {
        if (closed || peer == null) {
            fail("answer-rejected");
            return;
        }
        Log.i(LOG_TAG, "applying remote answer variant=" + label + " len=" + sdp.length());
        peer.setRemoteDescription(new SimpleSdpObserver() {
            @Override
            public void onSetSuccess() {
                Log.i(LOG_TAG, "remote WebRTC answer accepted variant=" + label);
            }

            @Override
            public void onSetFailure(String error) {
                Log.w(LOG_TAG, "remote WebRTC answer rejected variant=" + label + " error=" + error);
                String next = nextVariant(sdp, label);
                if (next != null) {
                    applyAnswerVariant(next, nextLabel(label));
                    return;
                }
                fail("answer-rejected");
            }
        }, new SessionDescription(SessionDescription.Type.ANSWER, sdp));
    }

    private static String nextVariant(String sdp, String label) {
        String nl = sdp.contains("\r\n") ? "\r\n" : "\n";
        switch (label) {
            case "original":
                // The runtime strips the trailing CRLF from the broker answer
                // while the realtime-2.1 path preserves it; the M144 parser
                // rejects an SDP without a final line terminator.
                return sdp.endsWith(nl) ? null : sdp + nl;
            case "trailing-nl":
                return sdp.replace("a=setup:passive", "a=setup:active");
            case "flip-active":
                return sdp.replaceAll("(?m)^a=setup:[a-zA-Z]+\r?\n", "");
            case "strip-setup": {
                // Remove the a=sendrecv line from the application (SCTP) section only.
                int idx = sdp.indexOf("m=application");
                if (idx <= 0) return null;
                String head = sdp.substring(0, idx);
                String tail = sdp.substring(idx);
                String stripped = tail.replace(nl + "a=sendrecv" + nl, nl);
                if (stripped.equals(tail)) return null;
                return head + stripped;
            }
            case "app-no-sendrecv": {
                // Remove setup + sendrecv from the application section.
                int idx = sdp.indexOf("m=application");
                if (idx <= 0) return null;
                String head = sdp.substring(0, idx);
                String tail = sdp.substring(idx);
                String stripped = tail
                        .replaceAll("(?m)^a=setup:[a-zA-Z]+\r?\n", "")
                        .replace(nl + "a=sendrecv" + nl, nl);
                if (stripped.equals(tail)) return null;
                return head + stripped;
            }
            case "app-min": {
                // Keep only the essential SCTP attributes.
                int idx = sdp.indexOf("m=application");
                if (idx <= 0) return null;
                String head = sdp.substring(0, idx);
                String tail = sdp.substring(idx);
                String stripped = tail
                        .replaceAll("(?m)^a=setup:[a-zA-Z]+\r?\n", "")
                        .replace(nl + "a=sendrecv" + nl, nl)
                        .replaceAll("(?m)^a=candidate:.*\r?\n", "");
                if (stripped.equals(tail)) return null;
                return head + stripped;
            }
            case "app-no-sctp": {
                // Drop sctp-port and max-message-size from the application section.
                int idx = sdp.indexOf("m=application");
                if (idx <= 0) return null;
                String head = sdp.substring(0, idx);
                String tail = sdp.substring(idx);
                String stripped = tail
                        .replaceAll("(?m)^a=sctp-port:.*\r?\n", "")
                        .replaceAll("(?m)^a=max-message-size:.*\r?\n", "");
                if (stripped.equals(tail)) return null;
                return head + stripped;
            }
            default:
                return null;
        }
    }

    private static String nextLabel(String label) {
        switch (label) {
            case "original": return "trailing-nl";
            case "trailing-nl": return "flip-active";
            case "flip-active": return "strip-setup";
            case "strip-setup": return "app-no-sendrecv";
            case "app-no-sendrecv": return "app-min";
            case "app-min": return "app-no-sctp";
            case "app-no-sctp": return "audio-only";
            case "audio-only": return "no-candidates";
            case "no-candidates": return "no-ssrc";
            case "no-ssrc": return "no-extmap";
            case "no-extmap": return "no-rtcp-rsize";
            default: return "";
        }
    }

    /**
     * AVAS (gpt-live-1) streams model audio as base64 PCM 24 kHz mono
     * {@code output_audio.delta} events over the data channel instead of RTP,
     * so it is decoded here and played through a dedicated AudioTrack.
     */
    public synchronized void playPcm(byte[] pcm) {
        if (closed || pcm == null || pcm.length == 0) return;
        try {
            if (pcmTrack == null) {
                int minBuf = android.media.AudioTrack.getMinBufferSize(
                        PCM_SAMPLE_RATE, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_16BIT);
                pcmTrack = new android.media.AudioTrack.Builder()
                        .setAudioAttributes(new AudioAttributes.Builder()
                                .setUsage(AudioAttributes.USAGE_MEDIA)
                                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                                .build())
                        .setAudioFormat(new AudioFormat.Builder()
                                .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                                .setSampleRate(PCM_SAMPLE_RATE)
                                .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                                .build())
                        .setBufferSizeInBytes(Math.max(minBuf * 4, 8192))
                        .setTransferMode(android.media.AudioTrack.MODE_STREAM)
                        .build();
                pcmTrack.play();
            }
            if (pcmTrack.getPlayState() != android.media.AudioTrack.PLAYSTATE_PLAYING) pcmTrack.play();
            pcmTrack.write(pcm, 0, pcm.length);
        } catch (Exception exception) {
            Log.w(LOG_TAG, "PCM playback failed: " + exception);
        }
    }

    public boolean sendRealtimeEvent(JSONObject event) {
        if (closed || dataChannel == null || dataChannel.state() != DataChannel.State.OPEN) {
            Log.w(LOG_TAG, "sendRealtimeEvent dropped, channel state="
                    + (dataChannel == null ? "null" : String.valueOf(dataChannel.state())));
            return false;
        }
        byte[] bytes = event.toString().getBytes(StandardCharsets.UTF_8);
        Log.i(LOG_TAG, "-> data channel send: " + event.toString().replace("\r", " ").replace("\n", " "));
        boolean sent = dataChannel.send(new DataChannel.Buffer(ByteBuffer.wrap(bytes), false));
        Log.i(LOG_TAG, "-> data channel send result=" + sent);
        return sent;
    }

    /** TEMP DEBUG: dump inbound/outbound audio RTP stats every 2s so we can tell
     *  whether the AVAS broker is streaming output audio over the audio track. */
    private void startStatsMonitor() {
        handler.postDelayed(new Runnable() {
            @Override public void run() {
                if (closed || peer == null) return;
                try {
                    peer.getStats(new RTCStatsCollectorCallback() {
                        @Override public void onStatsDelivered(RTCStatsReport report) {
                            long inPackets = -1, inBytes = -1, outPackets = -1;
                            double audioLevel = -1;
                            for (org.webrtc.RTCStats stats : report.getStatsMap().values()) {
                                if (!"inbound-rtp".equals(stats.getType())
                                        && !"outbound-rtp".equals(stats.getType())) continue;
                                Object kind = stats.getMembers().get("kind");
                                if (!"audio".equals(kind)) continue;
                                Object packets = stats.getMembers().get("packetsReceived");
                                if (packets == null) packets = stats.getMembers().get("packetsSent");
                                Object bytes = stats.getMembers().get("bytesReceived");
                                if (bytes == null) bytes = stats.getMembers().get("bytesSent");
                                Object level = stats.getMembers().get("audioLevel");
                                if ("inbound-rtp".equals(stats.getType())) {
                                    inPackets = packets == null ? -1 : ((Number) packets).longValue();
                                    inBytes = bytes == null ? -1 : ((Number) bytes).longValue();
                                    audioLevel = level == null ? -1 : ((Number) level).doubleValue();
                                } else {
                                    outPackets = packets == null ? -1 : ((Number) packets).longValue();
                                }
                            }
                            Log.i(LOG_TAG, String.format(
                                    "RTP stats: in_pkts=%d in_bytes=%d audioLevel=%.3f out_pkts=%d",
                                    inPackets, inBytes, audioLevel, outPackets));
                        }
                    });
                } catch (Exception exception) {
                    Log.w(LOG_TAG, "getStats failed: " + exception);
                }
                handler.postDelayed(this, 2000);
            }
        }, 2000);
    }

    public void close() {
        if (closed) return;
        closed = true;
        handler.removeCallbacksAndMessages(null);
        if (audioTrack != null) audioTrack.setEnabled(false);
        if (pcmTrack != null) {
            try {
                pcmTrack.pause();
                pcmTrack.flush();
                pcmTrack.release();
            } catch (Exception ignored) {
            }
            pcmTrack = null;
        }
        if (dataChannel != null) {
            dataChannel.unregisterObserver();
            dataChannel.close();
        }
        // Teardown the native WebRTC objects off the signaling thread. The
        // setRemoteDescription / createOffer failure callbacks run on the
        // signaling thread; disposing peer/factory synchronously there destroys
        // a mutex the signaling thread may still lock (FORTIFY abort: pthread
        // mutex_lock on a destroyed mutex). Post the disposal to the main looper
        // and let the signaling thread unwind first.
        final DataChannel channelToDispose = dataChannel;
        final PeerConnection peerToDispose = peer;
        final AudioTrack trackToDispose = audioTrack;
        final AudioSource sourceToDispose = audioSource;
        final PeerConnectionFactory factoryToDispose = factory;
        peer = null;
        dataChannel = null;
        audioTrack = null;
        audioSource = null;
        factory = null;
        handler.post(() -> {
            if (channelToDispose != null) channelToDispose.dispose();
            if (peerToDispose != null) {
                peerToDispose.close();
                peerToDispose.dispose();
            }
            if (trackToDispose != null) trackToDispose.dispose();
            if (sourceToDispose != null) sourceToDispose.dispose();
            if (factoryToDispose != null) factoryToDispose.dispose();
        });
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
        Log.i(LOG_TAG, "local WebRTC offer ready full="
                + local.description.replace("\r\n", " | ").replace("\n", " | "));
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
            if (state == PeerConnection.IceConnectionState.CONNECTED) startStatsMonitor();
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
            Log.i(LOG_TAG, "<- data channel recv: " + new String(bytes, StandardCharsets.UTF_8)
                    .replace("\r", " ").replace("\n", " "));
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

