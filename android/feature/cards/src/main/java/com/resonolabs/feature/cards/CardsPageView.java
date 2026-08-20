package com.resonolabs.feature.cards;

import android.app.Activity;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.widget.FrameLayout;

import com.resonolabs.runtime.host.CreationCatalogClient;
import com.resonolabs.feature.calendar.CalendarPageView;
import com.resonolabs.feature.tasks.TaskPageView;
import com.resonolabs.ui.input.UiInputIntent;

import org.json.JSONObject;

public final class CardsPageView extends FrameLayout implements AutoCloseable {
    private final Activity activity;
    private final Runnable openVoice;
    private final java.util.function.Consumer<Boolean> creationVisibility;
    private final CreationCatalogClient client = new CreationCatalogClient();
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final CardsDeckView deck;
    private final CardsBackButton back;
    private CreationWebViewHost creation;
    private CalendarPageView calendar;
    private TaskPageView tasks;
    private int generation = -1;

    public CardsPageView(Activity activity, Runnable openVoice,
                         java.util.function.Consumer<Boolean> creationVisibility) {
        super(activity);
        this.activity = activity;
        this.openVoice = openVoice;
        this.creationVisibility = creationVisibility;
        deck = new CardsDeckView(activity, this::openCreation);
        addView(deck, match());
        back = new CardsBackButton(activity, this::navigateBack);
        back.setVisibility(GONE);
        addView(back, new LayoutParams(58, 82));
    }

    public void start() {
        handler.removeCallbacks(refresh);
        handler.post(refresh);
        if (calendar != null) calendar.start();
        if (tasks != null) tasks.start();
    }

    public void stop() {
        handler.removeCallbacks(refresh);
        if (calendar != null) calendar.stop();
        if (tasks != null) tasks.stop();
    }

    public boolean onInput(UiInputIntent input) {
        if (input == UiInputIntent.BACK) { navigateBack(); return true; }
        if (calendar != null) { boolean handled=calendar.onInput(input);if(input==UiInputIntent.BACK&&!handled)closeCalendar();return true; }
        if (tasks != null) { boolean handled=tasks.onInput(input);if(input==UiInputIntent.BACK&&!handled)closeTasks();return true; }
        if (creation != null) return creation.onInput(input);
        deck.onInput(input);
        return true;
    }

    private void navigateBack() {
        if (calendar != null) { if (!calendar.onInput(UiInputIntent.BACK)) closeCalendar(); return; }
        if (tasks != null) { if (!tasks.onInput(UiInputIntent.BACK)) closeTasks(); return; }
        if (creation != null) { closeCreation(); return; }
        openVoice.run();
    }

    private final Runnable refresh = new Runnable() {
        @Override public void run() {
            client.load(activity, new CreationCatalogClient.Callback() {
                @Override public void onCatalog(JSONObject catalog) {
                    int next = catalog.optInt("generation", -1);
                    if (next != generation) {
                        generation = next;
                        deck.showCatalog(catalog);
                        if (creation != null) closeCreation();
                    }
                }
                @Override public void onFailure() {}
            });
            handler.postDelayed(this, 2000);
        }
    };

    private void openCreation(JSONObject item) {
        if ("builtin_calendar".equals(item.optString("sourceType"))) { openCalendar(); return; }
        if ("builtin_tasks".equals(item.optString("sourceType"))) { openTasks(); return; }
        if (creation != null) closeCreation();
        creation = new CreationWebViewHost(activity, client, item, this::closeCreation);
        deck.setVisibility(GONE);
        float density = getResources().getDisplayMetrics().density;
        LayoutParams params = new LayoutParams(Math.round(240f * density), Math.round(282f * density));
        params.gravity = Gravity.CENTER;
        addView(creation, params);
        back.setVisibility(VISIBLE);
        back.bringToFront();
        creationVisibility.accept(true);
    }

    private void openCalendar() {
        if (calendar != null) return;
        calendar = new CalendarPageView(activity, openVoice, this::closeCalendar);
        deck.setVisibility(GONE);
        addView(calendar, match());
        back.setVisibility(VISIBLE);
        back.bringToFront();
        creationVisibility.accept(true);
        calendar.start(); calendar.requestFocus();
    }

    private void closeCalendar() {
        if (calendar == null) return;
        removeView(calendar); calendar.close(); calendar=null; deck.setVisibility(VISIBLE); back.setVisibility(GONE); creationVisibility.accept(false);
    }

    private void openTasks() {
        if (tasks != null) return;
        tasks = new TaskPageView(activity, openVoice);
        deck.setVisibility(GONE); addView(tasks, match()); back.setVisibility(VISIBLE); back.bringToFront(); creationVisibility.accept(true); tasks.start(); tasks.requestFocus();
    }

    private void closeTasks() {
        if (tasks == null) return;
        removeView(tasks); tasks.close(); tasks=null; deck.setVisibility(VISIBLE); back.setVisibility(GONE); creationVisibility.accept(false);
    }

    private void closeCreation() {
        if (creation == null) return;
        removeView(creation);
        creation.destroy();
        creation = null;
        deck.setVisibility(VISIBLE);
        back.setVisibility(GONE);
        creationVisibility.accept(false);
    }

    private LayoutParams match() {
        return new LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT);
    }

    @Override public void close() {
        stop();
        closeCreation();
        closeCalendar();
        closeTasks();
        client.close();
    }
}
