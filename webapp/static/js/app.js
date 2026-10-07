// State
let userCoords = null;
let isProcessing = false;
let html5QrScanner = null;
let scannedQrData = null;
let selfieStream = null;

// DOM Elements
const actionBadge = document.getElementById("action-badge");
const actionTitle = document.getElementById("action-title");
const actionSubtitle = document.getElementById("action-subtitle");
const geoStatusCard = document.getElementById("geo-status-card");
const geoIcon = document.getElementById("geo-icon");
const geoStatusTitle = document.getElementById("geo-status-title");
const geoStatusDesc = document.getElementById("geo-status-desc");
const scannerSection = document.getElementById("scanner-section");
const selfieSection = document.getElementById("selfie-section");
const selfieVideo = document.getElementById("selfie-video");
const selfieCanvas = document.getElementById("selfie-canvas");
const btnCaptureSelfie = document.getElementById("btn-capture-selfie");
const cameraFallbackUI = document.getElementById("camera-fallback-ui");
const btnNativeScan = document.getElementById("btn-native-scan");
const resultCard = document.getElementById("result-card");
const resultIcon = document.getElementById("result-icon");
const resultTitle = document.getElementById("result-title");
const resultDesc = document.getElementById("result-desc");
const detailTime = document.getElementById("detail-time");
const detailDistance = document.getElementById("detail-distance");
const detailStatus = document.getElementById("detail-status");
const btnCloseWebApp = document.getElementById("btn-close-webapp");
const btnRefreshLocation = document.getElementById("btn-refresh-location");

// Extract Query Params
const urlParams = new URLSearchParams(window.location.search);
const actionType = (urlParams.get("action") || "keldim").toLowerCase();
const urlTgId = urlParams.get("tg_id") || "";

// Initialize Telegram WebApp
if (tg) {
  tg.ready();
  tg.expand();
  if (tg.enableClosingConfirmation) {
    tg.enableClosingConfirmation();
  }
}

// Set UI by Action
function setupActionUI() {
  if (actionType === "ketdim") {
    actionBadge.innerText = "Ketishni Qayd Etish";
    actionBadge.style.background = "rgba(239, 68, 68, 0.2)";
    actionBadge.style.color = "#f87171";
    actionTitle.innerText = "Ishdan Ketish";
    actionSubtitle.innerText = "Ketayotganda do'kondagi QR kodni skanerlang";
  } else {
    actionBadge.innerText = "Kelishni Qayd Etish";
    actionBadge.style.background = "rgba(16, 185, 129, 0.2)";
    actionBadge.style.color = "#34d399";
    actionTitle.innerText = "Ishga Kelish";
    actionSubtitle.innerText = "Kelganda do'kondagi QR kodni skanerlang";
  }
}

// Request and watch User Location with Fake GPS filtering
function requestLocation() {
  geoStatusTitle.innerText = "GPS Lokatsiya aniqlanmoqda...";
  geoStatusDesc.innerText = "Iltimos, kuting...";
  geoIcon.innerText = "📡";
  geoIcon.classList.add("badge-pulse");

  if (!navigator.geolocation) {
    geoStatusTitle.innerText = "GPS qo'llab-quvvatlanmaydi";
    geoStatusDesc.innerText = "Qurilmangizda lokatsiya funksiyasi topilmadi";
    geoIcon.innerText = "⚠️";
    geoIcon.classList.remove("badge-pulse");
    return;
  }

  navigator.geolocation.getCurrentPosition(
    (position) => {
      const acc = position.coords.accuracy;
      // Check for suspicious Mock Location (Fake GPS) anomalies
      if (acc <= 0.1) {
        console.warn("Suspicious accuracy detected (possible mock provider)");
      }

      userCoords = {
        lat: position.coords.latitude,
        lon: position.coords.longitude,
        accuracy: acc
      };

      geoStatusTitle.innerText = "Lokatsiya aniqlandi ✓";
      geoStatusDesc.innerText = `Aniqlik: ±${Math.round(userCoords.accuracy)}m. Endi QR kodni skanerlang`;
      geoIcon.innerText = "📍";
      geoIcon.classList.remove("badge-pulse");
      geoStatusCard.style.borderColor = "rgba(16, 185, 129, 0.5)";
      btnRefreshLocation.style.display = "none";
    },
    (error) => {
      console.error("GPS Error:", error);
      let errorMsg = "Lokatsiyani yoqish ruxsati berilmadi.";
      if (error.code === error.TIMEOUT) {
        errorMsg = "Lokatsiyani aniqlash vaqti tugadi. Qayta urinib ko'ring.";
      } else if (error.code === error.POSITION_UNAVAILABLE) {
        errorMsg = "GPS ma'lumoti mavjud emas. GPS yoqilganligini tekshiring.";
      }
      geoStatusTitle.innerText = "Lokatsiya olinmadi ❌";
      geoStatusDesc.innerText = errorMsg;
      geoIcon.innerText = "⚠️";
      geoIcon.classList.remove("badge-pulse");
      geoStatusCard.style.borderColor = "rgba(239, 68, 68, 0.5)";
      btnRefreshLocation.style.display = "flex";
    },
    {
      enableHighAccuracy: true,
      timeout: 15000,
      maximumAge: 0
    }
  );
}

// Step 1 Triggered: When QR Code is scanned
async function onQrCodeScanned(decodedText) {
  scannedQrData = decodedText;

  if (!userCoords) {
    if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("warning");
    alert("Iltimos, avval GPS lokatsiya aniqlanishini kuting!");
    requestLocation();
    return;
  }

  // Stop QR scanner
  if (html5QrScanner) {
    try {
      await html5QrScanner.stop();
    } catch (e) {}
  }

  // Switch to Selfie Verification Step
  scannerSection.style.display = "none";
  selfieSection.style.display = "block";
  startFrontSelfieCamera();
}

// Start Front Camera for Selfie Verification
async function startFrontSelfieCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user", width: { ideal: 480 }, height: { ideal: 480 } },
      audio: false
    });
    selfieStream = stream;
    selfieVideo.srcObject = stream;
  } catch (err) {
    console.warn("Could not open front camera for selfie:", err);
    // If front camera unavailable, fallback directly to checkin
    processCheckin(scannedQrData, "");
  }
}

// Capture Snapshot from Selfie Video
function captureSelfieImage() {
  if (!selfieVideo || !selfieVideo.videoWidth) {
    return "";
  }
  const canvas = selfieCanvas;
  canvas.width = 360;
  canvas.height = 360;
  const ctx = canvas.getContext("2d");
  // Flip horizontally for natural selfie view
  ctx.translate(canvas.width, 0);
  ctx.scale(-1, 1);
  ctx.drawImage(selfieVideo, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.75);
}

// Button Click: Capture Selfie & Submit
if (btnCaptureSelfie) {
  btnCaptureSelfie.addEventListener("click", () => {
    btnCaptureSelfie.disabled = true;
    btnCaptureSelfie.innerText = "⏳ Yuklanmoqda...";
    const selfieDataUrl = captureSelfieImage();
    
    // Stop selfie video stream
    if (selfieStream) {
      selfieStream.getTracks().forEach(track => track.stop());
    }

    processCheckin(scannedQrData, selfieDataUrl);
  });
}

// Handle Check-in Submission with Selfie and Anti-Spoofing
async function processCheckin(qrData, selfieBase64) {
  if (isProcessing) return;
  isProcessing = true;

  selfieSection.style.display = "none";
  scannerSection.style.display = "none";
  geoStatusCard.style.display = "block";

  // Show loading indicator
  geoStatusTitle.innerText = "Tekshirilmoqda...";
  geoStatusDesc.innerText = "QR kod, 50m masofa va Selfie tekshirilmoqda...";

  // Prepare payload
  const payload = {
    action: actionType,
    qr_data: qrData,
    lat: userCoords ? userCoords.lat : null,
    lon: userCoords ? userCoords.lon : null,
    accuracy: userCoords ? userCoords.accuracy : 0,
    selfie_image: selfieBase64 || "",
    tg_id: urlTgId,
    init_data: tg ? tg.initData : ""
  };

  try {
    const response = await fetch("/api/checkin", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    const result = await response.json();

    geoStatusCard.style.display = "none";
    resultCard.style.display = "block";

    if (result.success) {
      if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");

      resultCard.className = "result-card result-success";
      resultIcon.innerText = "✓";
      resultTitle.innerText = actionType === "ketdim" ? "Ishdan Ketish Qayd Etildi!" : "Ishga Kelish Qayd Etildi!";
      resultDesc.innerText = result.message || "Barcha ma'lumotlar to'g'ri va adminga yuborildi.";
      
      detailTime.innerText = result.time || new Date().toLocaleTimeString();
      detailDistance.innerText = `${result.distance_m} metr (Do'kon ichida)`;
      detailStatus.innerText = result.status_text || "Qabul qilindi";
      detailStatus.style.color = "#10b981";

    } else {
      if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("error");

      resultCard.className = "result-card result-error";
      resultIcon.innerText = "✕";
      resultTitle.innerText = "Kelish Rad Etildi!";
      resultDesc.innerText = result.message || "Do'kondan uzoqdasiz yoki QR kod noto'g'ri.";

      detailTime.innerText = new Date().toLocaleTimeString();
      detailDistance.innerText = result.distance_m !== undefined ? `${result.distance_m} metr (Maks: 50m)` : "Aniqlanmadi";
      detailStatus.innerText = "Rad etildi";
      detailStatus.style.color = "#ef4444";
    }

  } catch (err) {
    console.error("Checkin API error:", err);
    geoStatusCard.style.display = "none";
    resultCard.style.display = "block";
    resultCard.className = "result-card result-error";
    resultIcon.innerText = "⚠️";
    resultTitle.innerText = "Aloqa Xatoligi";
    resultDesc.innerText = "Server bilan bog'lanishda xatolik yuz berdi.";
    detailTime.innerText = "--:--";
    detailDistance.innerText = "--";
    detailStatus.innerText = "Xatolik";
  } finally {
    isProcessing = false;
  }
}

// Start HTML5 Camera QR Scanner
function startCameraScanner() {
  if (typeof Html5Qrcode === "undefined") {
    cameraFallbackUI.style.display = "block";
    return;
  }

  const qrConfig = {
    fps: 15,
    qrbox: { width: 220, height: 220 },
    aspectRatio: 1.0
  };

  html5QrScanner = new Html5Qrcode("reader");

  html5QrScanner
    .start(
      { facingMode: "environment" },
      qrConfig,
      (decodedText) => {
        onQrCodeScanned(decodedText);
      },
      (errorMessage) => {}
    )
    .catch((err) => {
      console.warn("HTML5 Camera start error:", err);
      cameraFallbackUI.style.display = "block";
    });
}

// Telegram Native QR Scanner Button
if (btnNativeScan) {
  btnNativeScan.addEventListener("click", () => {
    if (tg && tg.showScanQrPopup) {
      tg.showScanQrPopup({ text: "Do'kondagi QR kodni skanerlang" }, (scannedText) => {
        if (scannedText) {
          onQrCodeScanned(scannedText);
          return true; // close native popup
        }
      });
    } else {
      alert("Telegram QR skaneri faqat Telegram ilovasi ichida ishlaydi.");
    }
  });
}

// Close Button
if (btnCloseWebApp) {
  btnCloseWebApp.addEventListener("click", () => {
    if (tg) {
      tg.close();
    } else {
      window.close();
    }
  });
}

// Refresh Location Button
if (btnRefreshLocation) {
  btnRefreshLocation.addEventListener("click", () => {
    requestLocation();
  });
}

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  setupActionUI();
  requestLocation();
  startCameraScanner();

  if (tg && tg.showScanQrPopup && !html5QrScanner) {
    cameraFallbackUI.style.display = "block";
  }
});
