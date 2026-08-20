package com.resonolabs.feature.tasks;

import android.app.Activity;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.os.Handler;
import android.os.Looper;
import android.view.MotionEvent;
import android.view.View;
import com.resonolabs.runtime.host.TaskClient;
import com.resonolabs.ui.design.ReSonoTheme;
import com.resonolabs.ui.input.UiInputIntent;
import org.json.JSONArray;
import org.json.JSONObject;

/** Native 480x640 active Tasks list/detail projection. */
public final class TaskPageView extends View implements AutoCloseable {
    private static final float W = 480f, H = 640f;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final TaskClient client = new TaskClient();
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Runnable openVoice;
    private JSONArray tasks = new JSONArray();
    private int selected;
    private boolean detail;
    private float downX, downY, manualPan;
    private long focusAt = System.currentTimeMillis();

    public TaskPageView(Activity activity, Runnable openVoice) {
        super(activity); this.openVoice = openVoice; setFocusable(true);
        setContentDescription("Active tasks");
    }
    public void start() { handler.removeCallbacks(refresh); handler.post(refresh); }
    public void stop() { handler.removeCallbacks(refresh); }
    private final Runnable refresh = new Runnable() {
        @Override public void run() {
            client.loadActive(getContext(), new TaskClient.Callback() {
                @Override public void onTasks(JSONObject value) {
                    tasks = value.optJSONArray("tasks");
                    if (tasks == null) tasks = new JSONArray();
                    selected = Math.min(selected, Math.max(0, tasks.length() - 1));
                    if (tasks.length() == 0) detail = false;
                    invalidate();
                }
                @Override public void onFailure() {}
            });
            handler.postDelayed(this, 2000);
        }
    };

    public boolean onInput(UiInputIntent input) {
        if (input == UiInputIntent.BACK) {
            if (detail) { detail = false; invalidate(); return true; }
            return false;
        }
        if (detail) { if (input == UiInputIntent.ACTIVATE) openVoice.run(); return true; }
        if (input == UiInputIntent.NEXT) move(1);
        else if (input == UiInputIntent.PREVIOUS) move(-1);
        else if (input == UiInputIntent.ACTIVATE && tasks.length() > 0) { detail = true; invalidate(); }
        else return false;
        return true;
    }

    private void move(int delta) {
        if (tasks.length() == 0) return;
        selected = (selected + delta + tasks.length()) % tasks.length();
        focusAt = System.currentTimeMillis(); manualPan = 0; invalidate();
    }

    @Override public boolean onTouchEvent(MotionEvent event) {
        float x = event.getX() * W / Math.max(1, getWidth());
        float y = event.getY() * H / Math.max(1, getHeight());
        if (event.getActionMasked() == MotionEvent.ACTION_DOWN) { downX = x; downY = y; return true; }
        if (event.getActionMasked() == MotionEvent.ACTION_MOVE && !detail && Math.abs(x-downX) > Math.abs(y-downY)) {
            manualPan = Math.max(0, manualPan-(x-downX)); downX=x; invalidate(); return true;
        }
        if (event.getActionMasked() != MotionEvent.ACTION_UP) return true;
        if (detail) { if (y < 82) detail=false; else if (y >= 520) openVoice.run(); invalidate(); return true; }
        if (y >= 92 && y < 572 && tasks.length() > 0) {
            int next = Math.min(tasks.length()-1, (selected/5)*5+(int)((y-92)/96));
            if (next == selected) detail=true;
            else { selected=next; focusAt=System.currentTimeMillis(); manualPan=0; }
            invalidate();
        }
        return true;
    }

    @Override protected void onDraw(Canvas canvas) {
        canvas.drawColor(ReSonoTheme.BACKGROUND); canvas.save();
        canvas.scale(getWidth()/W, getHeight()/H); header(canvas);
        if (detail) drawDetail(canvas); else drawList(canvas); canvas.restore();
    }

    private void header(Canvas c) {
        ReSonoTheme.text(c,paint,"Tasks",55,45,30,ReSonoTheme.INK,Paint.Align.LEFT,false);
        ReSonoTheme.text(c,paint,detail?"TASK DETAILS":"OPEN",56,67,16,ReSonoTheme.MUTED,Paint.Align.LEFT,true);
        paint.setColor(0xffffd166); c.drawCircle(372,40,5,paint);
        ReSonoTheme.text(c,paint,"LOCAL",384,45,14,0xffffd166,Paint.Align.LEFT,true);
    }

    private void drawList(Canvas c) {
        if (tasks.length()==0) {
            ReSonoTheme.text(c,paint,"No open tasks",240,330,25,ReSonoTheme.INK,Paint.Align.CENTER,false);
            ReSonoTheme.text(c,paint,"Ask Voice to add one.",240,365,18,ReSonoTheme.MUTED,Paint.Align.CENTER,false); return;
        }
        int start=(selected/5)*5;
        for (int row=0; row<5 && start+row<tasks.length(); row++) {
            int i=start+row; JSONObject item=tasks.optJSONObject(i); float top=92+row*96;
            paint.setColor(i==selected?ReSonoTheme.PANEL_RAISED:ReSonoTheme.PANEL);
            c.drawRoundRect(new RectF(18,top,462,top+84),18,18,paint);
            paint.setStyle(Paint.Style.STROKE); paint.setStrokeWidth(i==selected?2:1);
            paint.setColor(i==selected?0xffffd166:ReSonoTheme.LINE);
            c.drawRoundRect(new RectF(18,top,462,top+84),18,18,paint); paint.setStyle(Paint.Style.FILL);
            line(c,item.optString("text","Task"),42,top+40,31,444,i==selected);
            ReSonoTheme.text(c,paint,"OPEN",42,top+68,21,i==selected?0xffffd166:ReSonoTheme.MUTED,Paint.Align.LEFT,true);
        }
        ReSonoTheme.text(c,paint,(selected+1)+" / "+tasks.length(),456,608,18,ReSonoTheme.MUTED,Paint.Align.RIGHT,false);
    }

    private void line(Canvas c,String text,float x,float baseline,float size,float right,boolean focused) {
        paint.setTextSize(size); float overflow=Math.max(0,paint.measureText(text)-(right-x));
        float offset=Math.min(manualPan,overflow);
        if (focused && overflow>0 && manualPan==0) {
            long elapsed=System.currentTimeMillis()-focusAt; float distance=overflow+18;
            long travel=Math.max(700,(long)(distance*28)); long position=elapsed%(1800+travel);
            if (position>900) offset=Math.min(distance,(position-900)*distance/travel); postInvalidateDelayed(33);
        }
        c.save(); c.clipRect(x,baseline-size-4,right,baseline+7);
        ReSonoTheme.text(c,paint,text,x-offset,baseline,size,focused?ReSonoTheme.INK:ReSonoTheme.MUTED,Paint.Align.LEFT,false); c.restore();
    }

    private void drawDetail(Canvas c) {
        JSONObject item=tasks.optJSONObject(selected); if(item==null)return;
        paint.setColor(ReSonoTheme.PANEL); c.drawRoundRect(new RectF(18,95,462,500),26,26,paint);
        paint.setStyle(Paint.Style.STROKE); paint.setStrokeWidth(2); paint.setColor(0xffffd166);
        c.drawRoundRect(new RectF(18,95,462,500),26,26,paint); paint.setStyle(Paint.Style.FILL);
        wrapped(c,item.optString("text","Task"),38,150,32,40,404);
        paint.setColor(ReSonoTheme.MINT); c.drawRoundRect(new RectF(18,528,462,592),18,18,paint);
        ReSonoTheme.text(c,paint,"EDIT WITH VOICE",240,568,20,ReSonoTheme.BACKGROUND,Paint.Align.CENTER,true);
    }

    private void wrapped(Canvas c,String value,float x,float y,float size,float line,float width) {
        paint.setTextSize(size); String rest=value.trim();
        while(!rest.isEmpty()&&y<465){int count=paint.breakText(rest,true,width,null);
            if(count<rest.length()){int space=rest.lastIndexOf(' ',Math.max(0,count-1));if(space>0)count=space;}
            ReSonoTheme.text(c,paint,rest.substring(0,Math.max(1,count)).trim(),x,y,size,ReSonoTheme.INK,Paint.Align.LEFT,false);
            rest=rest.substring(Math.min(rest.length(),Math.max(1,count))).trim();y+=line;}
    }
    @Override public void close(){stop();client.close();}
}
