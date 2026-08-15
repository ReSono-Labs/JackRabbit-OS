package com.resonolabs.voice;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.AlertDialog;
import android.Manifest;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.os.PowerManager;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowInsets;
import android.view.WindowInsetsController;

import com.resonolabs.ui.power.DisplayPolicy;
import com.resonolabs.runtime.host.RuntimeHealthClient;
import com.resonolabs.runtime.host.RuntimeManagementClient;
import com.resonolabs.runtime.host.RuntimeService;
import com.resonolabs.feature.settings.ManagementPairingState;

public final class MainActivity extends Activity {
    private ProductRootView root;
    private RuntimeHealthClient runtimeHealth;
    private RuntimeManagementClient runtimeManagement;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        SystemSetupState.markComplete(this);
        RuntimeService.start(this);
        runtimeHealth = new RuntimeHealthClient();
        runtimeManagement = new RuntimeManagementClient();
        runtimeHealth.checkUntilReady(this, health ->
                android.util.Log.i("ReSonoRuntime", "HOME boundary status=" + health.status()));
        setShowWhenLocked(true);
        setTurnScreenOn(true);
        root = new ProductRootView(this, this::confirmRestart, callback ->
                runtimeManagement.loadPairing(this, pairing -> callback.accept(
                        new ManagementPairingState(
                                pairing.status(),
                                pairing.code(),
                                pairing.address(),
                                pairing.expiresAt()))));
        setContentView(root);
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, 41);
        }
        DisplayPolicy.apply(getWindow());
        enterProductFullscreen();
    }

    @Override protected void onDestroy() {
        if (root != null) root.close();
        if (runtimeHealth != null) runtimeHealth.close();
        if (runtimeManagement != null) runtimeManagement.close();
        super.onDestroy();
    }

    private void confirmRestart() {
        new AlertDialog.Builder(this)
                .setTitle("Restart R1?")
                .setMessage("ReSono will restart and return to HOME.")
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Restart", (ignored, which) -> {
                    PowerManager power = getSystemService(PowerManager.class);
                    if (power != null) power.reboot("resono-settings");
                })
                .show();
    }

    @Override protected void onResume() {
        super.onResume();
        DisplayPolicy.applyInputPolicy(getWindow());
        enterProductFullscreen();
    }

    @Override public void onWindowFocusChanged(boolean focused) {
        super.onWindowFocusChanged(focused);
        if (focused) DisplayPolicy.applyInputPolicy(getWindow());
    }

    @Override public boolean dispatchKeyEvent(KeyEvent event) {
        if (root != null && root.onHardwareKey(event)) return true;
        return super.dispatchKeyEvent(event);
    }

    @Override public boolean onGenericMotionEvent(MotionEvent event) {
        if (root != null && root.onHardwareMotion(event)) return true;
        return super.onGenericMotionEvent(event);
    }

    @Override
    @SuppressLint("GestureBackNavigation")
    public void onBackPressed() {
        if (root != null) root.navigateBack();
    }

    private void enterProductFullscreen() {
        getWindow().setDecorFitsSystemWindows(false);
        WindowInsetsController controller = getWindow().getInsetsController();
        if (controller != null) {
            controller.hide(WindowInsets.Type.statusBars() | WindowInsets.Type.navigationBars());
            controller.setSystemBarsBehavior(
                    WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
        }
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                        | View.SYSTEM_UI_FLAG_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_STABLE);
    }
}
