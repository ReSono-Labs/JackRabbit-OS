package com.resonolabs.voice;

import android.app.Activity;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.widget.FrameLayout;

import com.resonolabs.feature.voice.VoicePageView;
import com.resonolabs.feature.settings.SettingsPanelView;
import com.resonolabs.feature.settings.ManagementPairingSource;
import com.resonolabs.feature.cards.CardsPageView;
import com.resonolabs.runtime.host.ManagementOpenAiSource;
import com.resonolabs.feature.camera.CameraHandoffPage;
import com.resonolabs.hardware.motor.R1MotorServiceClient;
import com.resonolabs.ui.input.HardwareInputRouter;
import com.resonolabs.ui.input.UiInputIntent;

final class ProductRootView extends FrameLayout {
    private final VoicePageView voice;
    private final SettingsPanelView settings;
    private final CardsPageView cards;
    private final ProductChromeView chrome;
    private final R1MotorServiceClient motor;
    private final CameraHandoffPage camera;
    private boolean settingsOpen;
    private boolean cardsOpen;
    private boolean cameraOpen;
    private boolean cardContentOpen;
    private float gestureDownX;
    private float gestureDownY;
    private boolean horizontalGesture;

    ProductRootView(
            Activity activity,
            Runnable restart,
            ManagementPairingSource managementPairing,
            ManagementOpenAiSource openAiSource
    ) {
        super(activity);
        motor = new R1MotorServiceClient(activity);
        voice = new VoicePageView(activity, this::openCameraHandoff);
        camera = new CameraHandoffPage(activity, motor, voice, this::returnFromCamera);
        camera.setVisibility(GONE);
        cards = new CardsPageView(activity, this::openVoice, this::showCreation);
        cards.setVisibility(GONE);
        chrome = new ProductChromeView(activity, this::openSettings, this::openVoice, this::openCards);
        settings = new SettingsPanelView(activity, this::closeSettings, restart, managementPairing, openAiSource);
        settings.setVisibility(GONE);
        addView(voice, match());
        addView(cards, match());
        addView(camera, match());
        LayoutParams chromeParams = new LayoutParams(LayoutParams.MATCH_PARENT, 142);
        addView(chrome, chromeParams);
        addView(settings, match());
        setFocusable(true);
        setFocusableInTouchMode(true);
        setContentDescription("ReSono R1 HOME");
    }

    private LayoutParams match() {
        return new LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT);
    }

    private void openSettings() {
        settingsOpen = true;
        voice.setVisibility(GONE);
        cards.setVisibility(GONE);
        cards.stop();
        chrome.setVisibility(GONE);
        settings.setVisibility(VISIBLE);
        settings.requestFocus();
    }

    private void closeSettings() {
        settingsOpen = false;
        settings.setVisibility(GONE);
        chrome.setVisibility(VISIBLE);
        if (cardsOpen) {
            cards.setVisibility(VISIBLE);
            cards.start();
            cards.requestFocus();
        } else {
            voice.setVisibility(VISIBLE);
            voice.requestFocus();
        }
    }

    private void openCards() {
        cardsOpen = true;
        chrome.showCards(true);
        voice.setVisibility(GONE);
        cards.setVisibility(VISIBLE);
        cards.start();
        cards.requestFocus();
    }

    private void openVoice() {
        cardsOpen = false;
        chrome.showCards(false);
        cards.stop();
        cards.setVisibility(GONE);
        voice.setVisibility(VISIBLE);
        voice.requestFocus();
    }

    private void showCreation(boolean visible) {
        cardContentOpen = visible;
        chrome.setVisibility(visible ? GONE : VISIBLE);
    }

    private void openCameraHandoff() {
        cameraOpen = true;
        voice.setVisibility(GONE); cards.setVisibility(GONE); chrome.setVisibility(GONE);
        camera.setVisibility(VISIBLE); camera.startHandoff(); camera.requestFocus();
    }

    private void openCamera() {
        if (settingsOpen || cameraOpen) return;
        cameraOpen = true;
        voice.setVisibility(GONE); cards.setVisibility(GONE); chrome.setVisibility(GONE);
        camera.setVisibility(VISIBLE); camera.startPreview(); camera.requestFocus();
    }

    private void returnFromCamera() {
        cameraOpen = false;
        camera.setVisibility(GONE); chrome.setVisibility(cardContentOpen ? GONE : VISIBLE);
        if (cardsOpen) {
            cards.setVisibility(VISIBLE); cards.start(); cards.requestFocus();
        } else {
            voice.setVisibility(VISIBLE); voice.requestFocus();
        }
    }

    @Override public boolean onInterceptTouchEvent(MotionEvent event) {
        if (settingsOpen) return false;
        switch (event.getActionMasked()) {
            case MotionEvent.ACTION_DOWN -> {
                gestureDownX = event.getX();
                gestureDownY = event.getY();
                horizontalGesture = false;
            }
            case MotionEvent.ACTION_MOVE -> {
                float dx = event.getX() - gestureDownX;
                float dy = event.getY() - gestureDownY;
                if (Math.abs(dx) >= 42f && Math.abs(dx) > Math.abs(dy) * 1.4f) {
                    horizontalGesture = true;
                    return true;
                }
            }
            default -> { }
        }
        return false;
    }

    @Override public boolean onTouchEvent(MotionEvent event) {
        if (!horizontalGesture) return true;
        if (event.getActionMasked() == MotionEvent.ACTION_UP) {
            float dx = event.getX() - gestureDownX;
            if (dx <= -72f && !cameraOpen) openCamera();
            else if (dx >= 72f && cameraOpen) {
                camera.stop();
                returnFromCamera();
            }
            horizontalGesture = false;
        } else if (event.getActionMasked() == MotionEvent.ACTION_CANCEL) {
            horizontalGesture = false;
        }
        return true;
    }

    boolean onHardwareKey(KeyEvent event) {
        UiInputIntent intent = HardwareInputRouter.keyIntent(event.getKeyCode());
        if (intent == null) return false;
        if (event.getAction() == KeyEvent.ACTION_DOWN) dispatch(intent);
        return true;
    }

    boolean onHardwareMotion(MotionEvent event) {
        UiInputIntent intent = HardwareInputRouter.motionIntent(event);
        if (intent == null) return false;
        dispatch(intent);
        return true;
    }

    boolean navigateBack() {
        if (cameraOpen) {
            camera.stop();
            returnFromCamera();
            return true;
        }
        if (settingsOpen) return settings.onInput(UiInputIntent.BACK);
        if (cardsOpen) return cards.onInput(UiInputIntent.BACK);
        return true;
    }

    private void dispatch(UiInputIntent intent) {
        if (settingsOpen) settings.onInput(intent);
        else if (cardsOpen) cards.onInput(intent);
        else voice.onInput(intent);
    }

    void close() {
        voice.close();
        cards.close();
        camera.close();
        motor.close();
    }
}
