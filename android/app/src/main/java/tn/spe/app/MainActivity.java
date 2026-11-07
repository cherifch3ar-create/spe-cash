package tn.spe.app;

import android.app.Activity;
import android.app.DownloadManager;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.webkit.*;

/** SPE Workspace : ouvre l'application en ligne (GitHub Pages + Supabase). */
public class MainActivity extends Activity {
  static final String ADRESSE = "https://cherifch3ar-create.github.io/spe-cash/workspace/";
  static final int CHOIX_FICHIER = 1;
  WebView vue;
  ValueCallback<Uri[]> rappelFichier;

  @Override protected void onCreate(Bundle b) {
    super.onCreate(b);
    vue = new WebView(this);
    WebSettings s = vue.getSettings();
    s.setJavaScriptEnabled(true);
    s.setDomStorageEnabled(true);
    s.setDatabaseEnabled(true);
    vue.setWebViewClient(new WebViewClient() {
      @Override public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
        Uri u = r.getUrl();
        if (u.toString().startsWith("https://cherifch3ar-create.github.io/")) return false;
        startActivity(new Intent(Intent.ACTION_VIEW, u)); // WhatsApp, TUNEPS, PDF… dans l'application du téléphone
        return true;
      }
    });
    vue.setWebChromeClient(new WebChromeClient() {
      @Override public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> cb, FileChooserParams p) {
        rappelFichier = cb;
        try { startActivityForResult(p.createIntent(), CHOIX_FICHIER); } catch (Exception e) { rappelFichier = null; return false; }
        return true;
      }
    });
    vue.setDownloadListener((url, ua, cd, type, len) -> {
      if (!url.startsWith("http")) return;
      DownloadManager.Request r = new DownloadManager.Request(Uri.parse(url));
      r.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
      r.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, URLUtil.guessFileName(url, cd, type));
      ((DownloadManager) getSystemService(DOWNLOAD_SERVICE)).enqueue(r);
    });
    setContentView(vue);
    if (b != null) vue.restoreState(b); else vue.loadUrl(ADRESSE);
  }

  @Override protected void onActivityResult(int code, int res, Intent data) {
    if (code == CHOIX_FICHIER && rappelFichier != null) {
      rappelFichier.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(res, data));
      rappelFichier = null;
    } else super.onActivityResult(code, res, data);
  }
  @Override protected void onSaveInstanceState(Bundle b) { super.onSaveInstanceState(b); vue.saveState(b); }
  @Override public void onBackPressed() { if (vue.canGoBack()) vue.goBack(); else super.onBackPressed(); }
}
