package com.resonolabs.feature.calendar;

import android.app.Activity;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.os.Handler;
import android.os.Looper;
import android.view.MotionEvent;
import android.view.View;
import com.resonolabs.runtime.host.CalendarEventClient;
import com.resonolabs.ui.design.ReSonoTheme;
import com.resonolabs.ui.input.UiInputIntent;
import org.json.JSONArray;
import org.json.JSONObject;
import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;

/** 480x640 donor-proven upcoming Calendar list/detail projection. */
public final class CalendarPageView extends View implements AutoCloseable {
    private static final float W=480f,H=640f;
    private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
    private final CalendarEventClient client=new CalendarEventClient();
    private final Runnable closeCalendar;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final Runnable openVoice;
    private JSONArray events=new JSONArray();
    private int selected; private boolean detail; private float downX,downY,detailScroll,maxDetailScroll,manualPan;
    private long focusAt=System.currentTimeMillis();

    public CalendarPageView(Activity activity,Runnable openVoice,Runnable closeCalendar){super(activity);this.openVoice=openVoice;this.closeCalendar=closeCalendar;setFocusable(true);setContentDescription("Upcoming calendar events");}
    public void start(){handler.removeCallbacks(refresh);handler.post(refresh);}
    public void stop(){handler.removeCallbacks(refresh);}
    private final Runnable refresh=new Runnable(){@Override public void run(){client.loadUpcoming(getContext(),new CalendarEventClient.Callback(){public void onEvents(JSONObject value){events=value.optJSONArray("events");if(events==null)events=new JSONArray();selected=Math.min(selected,Math.max(0,events.length()-1));invalidate();}public void onFailure(){}});handler.postDelayed(this,5000);}};

    public boolean onInput(UiInputIntent input){if(input==UiInputIntent.BACK){if(detail){detail=false;detailScroll=0;invalidate();return true;}return false;}if(detail){if(input==UiInputIntent.NEXT)detailScroll=Math.min(maxDetailScroll,detailScroll+45);else if(input==UiInputIntent.PREVIOUS)detailScroll=Math.max(0,detailScroll-45);else if(input==UiInputIntent.ACTIVATE&&current().optBoolean("editable"))openVoice.run();invalidate();return true;}if(input==UiInputIntent.NEXT)move(1);else if(input==UiInputIntent.PREVIOUS)move(-1);else if(input==UiInputIntent.ACTIVATE)openDetail();else return false;return true;}
    private void move(int delta){if(events.length()==0)return;selected=(selected+delta+events.length())%events.length();focusAt=System.currentTimeMillis();manualPan=0;invalidate();}
    private void openDetail(){if(events.length()==0)return;detail=true;detailScroll=0;invalidate();}
    private JSONObject current(){JSONObject value=events.optJSONObject(selected);return value==null?new JSONObject():value;}

    @Override public boolean onTouchEvent(MotionEvent event){float x=event.getX()*W/Math.max(1,getWidth()),y=event.getY()*H/Math.max(1,getHeight());if(event.getActionMasked()==MotionEvent.ACTION_DOWN){downX=x;downY=y;return true;}if(event.getActionMasked()==MotionEvent.ACTION_MOVE){float dx=x-downX,dy=y-downY;if(detail&&Math.abs(dy)>Math.abs(dx)){detailScroll=Math.max(0,Math.min(maxDetailScroll,detailScroll-dy));downY=y;invalidate();}else if(!detail&&downX>=88&&Math.abs(dx)>Math.abs(dy)){manualPan=Math.max(0,manualPan-dx);downX=x;invalidate();}return true;}if(event.getActionMasked()!=MotionEvent.ACTION_UP)return true;if(y<82){if(detail){detail=false;detailScroll=0;invalidate();}else closeCalendar.run();return true;}if(detail){if(y>=528&&current().optBoolean("editable"))openVoice.run();invalidate();return true;}if(y>=92&&y<572&&events.length()>0){int row=(int)((y-92)/96);int next=Math.min(events.length()-1,(selected/5)*5+row);if(next==selected)openDetail();else{selected=next;focusAt=System.currentTimeMillis();manualPan=0;invalidate();}}return true;}

    @Override protected void onDraw(Canvas canvas){canvas.drawColor(ReSonoTheme.BACKGROUND);canvas.save();canvas.scale(getWidth()/W,getHeight()/H);header(canvas);if(detail)drawDetail(canvas);else drawList(canvas);canvas.restore();}
    private void header(Canvas c){ReSonoTheme.text(c,paint,"Calendar",55,45,30,ReSonoTheme.INK,Paint.Align.LEFT,false);ReSonoTheme.text(c,paint,detail?"EVENT DETAILS":"UPCOMING",56,67,16,ReSonoTheme.MUTED,Paint.Align.LEFT,true);paint.setColor(ReSonoTheme.MINT);c.drawCircle(372,40,5,paint);ReSonoTheme.text(c,paint,"LIVE",384,45,14,ReSonoTheme.MINT,Paint.Align.LEFT,true);}
    private void drawList(Canvas c){if(events.length()==0){ReSonoTheme.text(c,paint,"No upcoming events",240,330,25,ReSonoTheme.INK,Paint.Align.CENTER,false);ReSonoTheme.text(c,paint,"Calendar is up to date.",240,365,18,ReSonoTheme.MUTED,Paint.Align.CENTER,false);return;}int pageStart=(selected/5)*5;for(int row=0;row<5&&pageStart+row<events.length();row++){int i=pageStart+row;JSONObject item=events.optJSONObject(i);float top=92+row*96;paint.setColor(i==selected?ReSonoTheme.PANEL_RAISED:ReSonoTheme.PANEL);c.drawRoundRect(new RectF(18,top,462,top+84),18,18,paint);paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(i==selected?2:1);paint.setColor(i==selected?0xffff5ca8:ReSonoTheme.LINE);c.drawRoundRect(new RectF(18,top,462,top+84),18,18,paint);paint.setStyle(Paint.Style.FILL);ReSonoTheme.text(c,paint,"□",53,top+51,28,0xffff5ca8,Paint.Align.CENTER,false);drawLine(c,item.optString("title","Untitled event"),92,top+38,31,444,i==selected,28);String secondary=friendly(item.optString("startsAt"));String location=item.optString("location","");if(!location.isBlank())secondary+=" · "+location;drawLine(c,secondary,92,top+66,21,444,i==selected,34);}ReSonoTheme.text(c,paint,(selected+1)+" / "+events.length(),456,608,18,ReSonoTheme.MUTED,Paint.Align.RIGHT,false);}
    private void drawLine(Canvas c,String text,float x,float baseline,float size,float right,boolean focused,float msPerPixel){paint.setTextSize(size);float overflow=Math.max(0,paint.measureText(text)-(right-x));float offset=Math.min(manualPan,overflow);if(focused&&overflow>0&&manualPan==0){long elapsed=System.currentTimeMillis()-focusAt;float distance=overflow+18;long travel=Math.max(700,(long)(distance*msPerPixel));long cycle=900+travel+900;if(elapsed%cycle>900)offset=Math.min(distance,(elapsed%cycle-900)*distance/travel);postInvalidateDelayed(33);}c.save();c.clipRect(x,baseline-size-4,right,baseline+7);ReSonoTheme.text(c,paint,text,x-offset,baseline,size,focused?ReSonoTheme.INK:ReSonoTheme.MUTED,Paint.Align.LEFT,false);c.restore();}
    private void drawDetail(Canvas c){JSONObject item=current();boolean editable=item.optBoolean("editable");float contentBottom=editable?510:560;paint.setColor(ReSonoTheme.PANEL);c.drawRoundRect(new RectF(18,88,462,622),26,26,paint);paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(2);paint.setColor(0xffff5ca8);c.drawRoundRect(new RectF(18,88,462,622),26,26,paint);paint.setStyle(Paint.Style.FILL);c.save();c.clipRect(30,102,450,contentBottom);float y=138-detailScroll;y=wrapped(c,item.optString("title","Untitled event"),30,y,32,38,420,ReSonoTheme.INK)+18;y=field(c,"STARTS",friendly(item.optString("startsAt")),y);y=field(c,"ENDS",friendly(item.optString("endsAt")),y);y=field(c,"LOCATION",item.optString("location"),y);y=field(c,"CALENDAR",item.optString("calendar"),y);y=field(c,"ORGANIZER",item.optString("organizer"),y);y=field(c,"DESCRIPTION",item.optString("description"),y);maxDetailScroll=Math.max(0,y+detailScroll-contentBottom+24);detailScroll=Math.min(detailScroll,maxDetailScroll);c.restore();ReSonoTheme.text(c,paint,editable?"DRAG TO SCROLL":"READ ONLY",38,594,15,ReSonoTheme.MUTED,Paint.Align.LEFT,true);ReSonoTheme.text(c,paint,"DRAG TO SCROLL",442,594,15,ReSonoTheme.MUTED,Paint.Align.RIGHT,true);if(editable){paint.setColor(ReSonoTheme.MINT);c.drawRoundRect(new RectF(30,528,450,608),18,18,paint);ReSonoTheme.text(c,paint,"EDIT WITH VOICE",240,577,20,ReSonoTheme.BACKGROUND,Paint.Align.CENTER,true);}}
    private float field(Canvas c,String label,String value,float y){if(value==null||value.isBlank())return y;ReSonoTheme.text(c,paint,label,30,y,17,0xffff5ca8,Paint.Align.LEFT,true);return wrapped(c,value,30,y+32,25,32,420,ReSonoTheme.INK)+15;}
    private float wrapped(Canvas c,String value,float x,float y,float size,float line,float width,int color){paint.setTextSize(size);String rest=value.trim();while(!rest.isEmpty()){int count=paint.breakText(rest,true,width,null);if(count<rest.length()){int space=rest.lastIndexOf(' ',Math.max(0,count-1));if(space>0)count=space;}String part=rest.substring(0,Math.max(1,count)).trim();ReSonoTheme.text(c,paint,part,x,y,size,color,Paint.Align.LEFT,false);rest=rest.substring(Math.min(rest.length(),Math.max(1,count))).trim();y+=line;}return y;}
    private static String friendly(String value){if(value==null||value.isBlank())return "";try{return OffsetDateTime.parse(value).format(DateTimeFormatter.ofPattern("EEE, MMM d · h:mm a"));}catch(Exception ignored){return value;}}
    @Override public void close(){stop();client.close();}
}
