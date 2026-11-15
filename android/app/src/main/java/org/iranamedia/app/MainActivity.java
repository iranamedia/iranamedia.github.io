package org.iranamedia.app;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;

/** رسانه ایرانا: تارنمای ایرانا (خبرنامه‌ی هر ساعت، رادیو و سیما) در یک اپ. پیوندهای بیرونی
 *  (تلگرام، یوتیوب، منابع خبر) در اپ خودشان باز می‌شوند. */
public class MainActivity extends Activity {
    static final String HOME = "https://iranamedia.github.io/";
    static final String HOST = "iranamedia.github.io";
    WebView web;
    long pausedAt = 0;
    View fullView;
    WebChromeClient.CustomViewCallback fullCallback;
    WebChromeClient chrome;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.parseColor("#0a1530"));
        web = new WebView(this);
        web.setBackgroundColor(Color.parseColor("#0a1530"));
        root.addView(web);
        setContentView(root);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setCacheMode(online() ? WebSettings.LOAD_DEFAULT : WebSettings.LOAD_CACHE_ELSE_NETWORK);
        s.setUserAgentString(s.getUserAgentString() + " IranaApp");

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
                Uri u = r.getUrl();
                if (HOST.equals(u.getHost())) return false;          // تارنمای ایرانا: در اپ
                try { startActivity(new Intent(Intent.ACTION_VIEW, u)); } catch (Exception e) { }
                return true;                                         // بیرونی: تلگرام، یوتیوب، مرورگر
            }
        });
        chrome = new WebChromeClient() {                              // ویدیوی تمام‌صفحه
            @Override
            public void onShowCustomView(View view, CustomViewCallback cb) {
                fullView = view; fullCallback = cb;
                root.addView(view, new FrameLayout.LayoutParams(-1, -1));
                web.setVisibility(View.GONE);
            }
            @Override
            public void onHideCustomView() {
                if (fullView != null) root.removeView(fullView);
                fullView = null; web.setVisibility(View.VISIBLE);
                if (fullCallback != null) fullCallback.onCustomViewHidden();
            }
        };
        web.setWebChromeClient(chrome);

        Uri link = getIntent() != null ? getIntent().getData() : null;
        if (state != null) web.restoreState(state);
        else web.loadUrl(link != null && HOST.equals(link.getHost()) ? link.toString() : HOME);
    }

    boolean online() {
        ConnectivityManager cm = (ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
        NetworkInfo n = cm != null ? cm.getActiveNetworkInfo() : null;
        return n != null && n.isConnected();
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        Uri link = intent.getData();
        if (link != null && HOST.equals(link.getHost())) web.loadUrl(link.toString());
    }

    @Override
    protected void onPause() { super.onPause(); pausedAt = System.currentTimeMillis(); }

    @Override
    protected void onResume() {
        super.onResume();
        // پس از ۱۵ دقیقه بیرون از اپ، خبرنامه‌ی تازه بارگذاری می‌شود
        if (pausedAt > 0 && System.currentTimeMillis() - pausedAt > 15 * 60 * 1000 && online()) {
            web.getSettings().setCacheMode(WebSettings.LOAD_DEFAULT);
            web.reload();
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle out) { super.onSaveInstanceState(out); web.saveState(out); }

    @Override
    public void onBackPressed() {
        if (fullView != null) { chrome.onHideCustomView(); return; }
        if (web.canGoBack()) web.goBack(); else super.onBackPressed();
    }
}
