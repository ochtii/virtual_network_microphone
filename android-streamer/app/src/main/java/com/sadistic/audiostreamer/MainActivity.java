package com.sadistic.audiostreamer;

import android.Manifest;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.content.pm.PackageManager;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.net.wifi.WifiInfo;
import android.net.wifi.WifiManager;
import android.os.Bundle;
import android.os.IBinder;
import android.text.format.Formatter;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.SeekBar;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

public class MainActivity extends AppCompatActivity {
    private static final int PERMISSION_REQUEST_CODE = 666; // Evil number, naturally

    private TextView statusText;
    private TextView ipAddressText;
    private TextView portText;
    private EditText portInput;
    private Switch voiceActivationSwitch;
    private SeekBar thresholdSlider;
    private TextView thresholdValueText;
    private TextView currentLevelText;
    private Button startStopButton;
    private Button minimizeButton;
    private View dbScaleView;

    private AudioStreamingService streamingService;
    private boolean serviceBound = false;
    private boolean isStreaming = false;

    private ServiceConnection serviceConnection = new ServiceConnection() {
        @Override
        public void onServiceConnected(ComponentName name, IBinder service) {
            AudioStreamingService.LocalBinder binder = (AudioStreamingService.LocalBinder) service;
            streamingService = binder.getService();
            serviceBound = true;
            
            // Set up audio level callback
            streamingService.setAudioLevelCallback(level -> runOnUiThread(() -> {
                updateAudioLevel(level);
                updateDbScale(level);
            }));
        }

        @Override
        public void onServiceDisconnected(ComponentName name) {
            streamingService = null;
            serviceBound = false;
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        initializeViews();
        setupListeners();
        displayLocalIP();
        
        // Check for evil permissions
        if (!hasAudioPermission()) {
            requestAudioPermission();
        }
    }

    private void initializeViews() {
        statusText = findViewById(R.id.statusText);
        ipAddressText = findViewById(R.id.ipAddressText);
        portText = findViewById(R.id.portText);
        portInput = findViewById(R.id.portInput);
        voiceActivationSwitch = findViewById(R.id.voiceActivationSwitch);
        thresholdSlider = findViewById(R.id.thresholdSlider);
        thresholdValueText = findViewById(R.id.thresholdValueText);
        currentLevelText = findViewById(R.id.currentLevelText);
        startStopButton = findViewById(R.id.startStopButton);
        minimizeButton = findViewById(R.id.minimizeButton);
        dbScaleView = findViewById(R.id.dbScaleView);
    }

    private void setupListeners() {
        startStopButton.setOnClickListener(v -> toggleStreaming());
        
        minimizeButton.setOnClickListener(v -> {
            moveTaskToBack(true);
            Toast.makeText(this, "Running in background... 😈", Toast.LENGTH_SHORT).show();
        });

        thresholdSlider.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            @Override
            public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
                if (fromUser) {
                    float dbValue = progressToDb(progress);
                    thresholdValueText.setText(getString(R.string.threshold_setting, dbValue));
                    if (serviceBound && streamingService != null) {
                        streamingService.setVoiceThreshold(dbValue);
                    }
                }
            }

            @Override
            public void onStartTrackingTouch(SeekBar seekBar) {}

            @Override
            public void onStopTrackingTouch(SeekBar seekBar) {}
        });

        voiceActivationSwitch.setOnCheckedChangeListener((buttonView, isChecked) -> {
            if (serviceBound && streamingService != null) {
                streamingService.setVoiceActivationEnabled(isChecked);
            }
        });

        // Initialize threshold display
        float initialThreshold = progressToDb(thresholdSlider.getProgress());
        thresholdValueText.setText(getString(R.string.threshold_setting, initialThreshold));
    }

    private void toggleStreaming() {
        if (!hasAudioPermission()) {
            requestAudioPermission();
            return;
        }

        if (!isStreaming) {
            startStreaming();
        } else {
            stopStreaming();
        }
    }

    private void startStreaming() {
        int port = Integer.parseInt(portInput.getText().toString());
        boolean voiceActivation = voiceActivationSwitch.isChecked();
        float threshold = progressToDb(thresholdSlider.getProgress());

        Intent intent = new Intent(this, AudioStreamingService.class);
        intent.putExtra("port", port);
        intent.putExtra("voiceActivation", voiceActivation);
        intent.putExtra("threshold", threshold);
        
        startForegroundService(intent);
        bindService(intent, serviceConnection, Context.BIND_AUTO_CREATE);

        isStreaming = true;
        startStopButton.setText(R.string.stop_streaming);
        startStopButton.setBackgroundTintList(getResources().getColorStateList(android.R.color.holo_red_dark));
        statusText.setText("Status: Broadcasting evil... 😈");
        
        Toast.makeText(this, "Audio stream started on port " + port, Toast.LENGTH_SHORT).show();
    }

    private void stopStreaming() {
        if (serviceBound) {
            unbindService(serviceConnection);
            serviceBound = false;
        }
        
        Intent intent = new Intent(this, AudioStreamingService.class);
        stopService(intent);

        isStreaming = false;
        startStopButton.setText(R.string.start_streaming);
        startStopButton.setBackgroundTintList(getResources().getColorStateList(R.color.design_default_color_primary));
        statusText.setText(R.string.streaming_status);
        currentLevelText.setText("");
        
        Toast.makeText(this, "Audio stream stopped", Toast.LENGTH_SHORT).show();
    }

    private void displayLocalIP() {
        WifiManager wifiManager = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
        WifiInfo wifiInfo = wifiManager.getConnectionInfo();
        int ipAddress = wifiInfo.getIpAddress();
        String ip = Formatter.formatIpAddress(ipAddress);
        ipAddressText.setText(getString(R.string.local_ip, ip));
    }

    private void updateAudioLevel(float dbLevel) {
        currentLevelText.setText(getString(R.string.current_level, dbLevel));
    }

    private void updateDbScale(float currentLevel) {
        // This would be better implemented with a custom View, but for simplicity:
        // The dbScaleView will be updated with a simple color change based on level
        if (currentLevel > progressToDb(thresholdSlider.getProgress())) {
            dbScaleView.setBackgroundColor(Color.RED); // Above threshold
        } else {
            dbScaleView.setBackgroundColor(Color.GREEN); // Below threshold
        }
    }

    private float progressToDb(int progress) {
        // Convert slider progress (0-100) to dB range (-60 to 0)
        return -60f + (progress * 0.6f);
    }

    private boolean hasAudioPermission() {
        return ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) 
                == PackageManager.PERMISSION_GRANTED;
    }

    private void requestAudioPermission() {
        ActivityCompat.requestPermissions(this, 
                new String[]{Manifest.permission.RECORD_AUDIO}, 
                PERMISSION_REQUEST_CODE);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, 
                                         @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        
        if (requestCode == PERMISSION_REQUEST_CODE) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                Toast.makeText(this, "Permission granted! Ready for evil... 😈", Toast.LENGTH_SHORT).show();
            } else {
                Toast.makeText(this, "Audio permission required for streaming", Toast.LENGTH_LONG).show();
            }
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (serviceBound) {
            unbindService(serviceConnection);
        }
    }
}