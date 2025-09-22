# Add any ProGuard configurations specific to this
# extension here.

-keep public class * extends android.app.Service
-keep public class * extends android.app.IntentService

# Keep audio streaming classes
-keep class com.sadistic.audiostreamer.** { *; }

# Keep NanoHTTPD classes
-keep class fi.iki.elonen.** { *; }