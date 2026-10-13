.class public Lcom/abhimanyu/watchlist/MainActivity;
.super Landroid/app/Activity;
.source "MainActivity.java"


# instance fields
.field private web:Landroid/webkit/WebView;


# direct methods
.method public constructor <init>()V
    .registers 1

    invoke-direct {p0}, Landroid/app/Activity;-><init>()V

    return-void
.end method


# virtual methods
.method protected onCreate(Landroid/os/Bundle;)V
    .registers 7

    invoke-super {p0, p1}, Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V

    new-instance v0, Landroid/webkit/WebView;

    invoke-direct {v0, p0}, Landroid/webkit/WebView;-><init>(Landroid/content/Context;)V

    iput-object v0, p0, Lcom/abhimanyu/watchlist/MainActivity;->web:Landroid/webkit/WebView;

    # Dark background (#121419) so there is no white flash while the page loads.
    const v4, -0xedebe7

    invoke-virtual {v0, v4}, Landroid/webkit/WebView;->setBackgroundColor(I)V

    invoke-virtual {v0}, Landroid/webkit/WebView;->getSettings()Landroid/webkit/WebSettings;

    move-result-object v1

    const/4 v2, 0x1

    invoke-virtual {v1, v2}, Landroid/webkit/WebSettings;->setJavaScriptEnabled(Z)V

    invoke-virtual {v1, v2}, Landroid/webkit/WebSettings;->setDomStorageEnabled(Z)V

    # The bundled starter page fetches newer app pages from GitHub Pages.
    invoke-virtual {v1, v2}, Landroid/webkit/WebSettings;->setAllowUniversalAccessFromFileURLs(Z)V

    # Pages inside the app stay in the app; other links (WhatsApp, Drive, GitHub) open in their own apps.
    new-instance v3, Lcom/abhimanyu/watchlist/Client;

    invoke-direct {v3}, Lcom/abhimanyu/watchlist/Client;-><init>()V

    invoke-virtual {v0, v3}, Landroid/webkit/WebView;->setWebViewClient(Landroid/webkit/WebViewClient;)V

    const-string v3, "file:///android_asset/index.html"

    invoke-virtual {v0, v3}, Landroid/webkit/WebView;->loadUrl(Ljava/lang/String;)V

    invoke-virtual {p0, v0}, Lcom/abhimanyu/watchlist/MainActivity;->setContentView(Landroid/view/View;)V

    return-void
.end method

# The phone's back button steps back one screen inside the app; from the first screen it closes the app.
.method public onBackPressed()V
    .registers 3

    iget-object v0, p0, Lcom/abhimanyu/watchlist/MainActivity;->web:Landroid/webkit/WebView;

    if-eqz v0, :cond_super

    invoke-virtual {v0}, Landroid/webkit/WebView;->canGoBack()Z

    move-result v1

    if-eqz v1, :cond_super

    invoke-virtual {v0}, Landroid/webkit/WebView;->goBack()V

    return-void

    :cond_super
    invoke-super {p0}, Landroid/app/Activity;->onBackPressed()V

    return-void
.end method
