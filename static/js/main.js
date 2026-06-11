/**
 * ============================================
 * TELKOM ENTERPRISE PRODUCTIVITY SUITE
 * Main JavaScript — Vanilla JS
 * ============================================
 */

/* ============================================
 * GLOBAL: Sidebar & Navigation
 * ============================================ */

(function () {
  "use strict";

  const hamburger = document.getElementById("hamburgerBtn");
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("sidebarOverlay");

  // Toggle sidebar di mobile
  if (hamburger) {
    hamburger.addEventListener("click", function () {
      sidebar.classList.toggle("sidebar--open");
      overlay.classList.toggle("sidebar-overlay--visible");
    });
  }

  // Tutup sidebar saat klik overlay
  if (overlay) {
    overlay.addEventListener("click", function () {
      sidebar.classList.remove("sidebar--open");
      overlay.classList.remove("sidebar-overlay--visible");
    });
  }
})();

/* ============================================
 * HALAMAN: Absensi
 * ============================================ */

function initAbsensiForm() {
  const form = document.getElementById("absensiForm");
  if (!form) return;

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    submitAbsensi();
  });
}

/**
 * Submit form absensi secara async via fetch API.
 * Menampilkan banner sukses/error, refresh tabel audit log.
 */
async function submitAbsensi() {
  const submitBtn = document.getElementById("submitBtn");
  const successBanner = document.getElementById("successBanner");
  const errorBanner = document.getElementById("errorBanner");
  const successMessage = document.getElementById("successMessage");
  const errorMessage = document.getElementById("errorMessage");

  // Ambil nilai form
  const nama = document.getElementById("namaKaryawan").value;
  const status = document.getElementById("statusKehadiran").value;
  const catatan = document.getElementById("catatan").value;

  // Validasi
  if (!nama || !status) {
    showBanner(errorBanner, "Nama dan status wajib diisi");
    hideBanner(successBanner);
    return;
  }

  // Loading state
  submitBtn.disabled = true;
  submitBtn.classList.add("btn--loading");
  hideBanner(successBanner);
  hideBanner(errorBanner);

  try {
    const response = await fetch("/absensi/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nama, status, catatan }),
    });

    const data = await response.json();

    if (response.ok && data.success) {
      showBanner(successBanner, data.message || "Absensi berhasil dicatat");
      hideBanner(errorBanner);

      // Reset form
      document.getElementById("absensiForm").reset();

      // Refresh tabel audit log
      await refreshAuditLog();
    } else {
      showBanner(
        errorBanner,
        data.message || "Terjadi kesalahan saat menyimpan",
      );
      hideBanner(successBanner);
    }
  } catch (err) {
    console.error("Error submit absensi:", err);
    showBanner(errorBanner, "Gagal terhubung ke server");
    hideBanner(successBanner);
  } finally {
    submitBtn.disabled = false;
    submitBtn.classList.remove("btn--loading");
  }
}

/**
 * Refresh tabel audit log dengan data terbaru dari server.
 */
async function refreshAuditLog() {
  try {
    const response = await fetch("/absensi/api/log");
    const data = await response.json();

    const tbody = document.getElementById("auditLogBody");
    if (!tbody) return;

    if (!data.log || data.log.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="4" class="empty-state">Belum ada data kehadiran</td></tr>';
      return;
    }

    tbody.innerHTML = data.log
      .map(function (row) {
        let chipClass = "";
        if (row.Status === "Hadir" || row.Status === "WFH")
          chipClass = "chip--success";
        else if (row.Status === "Izin") chipClass = "chip--pending";
        else if (row.Status === "Sakit") chipClass = "chip--critical";

        return (
          "<tr>" +
          "<td>" +
          escapeHtml(row.Timestamp || "") +
          "</td>" +
          "<td>" +
          escapeHtml(row.Nama || "") +
          "</td>" +
          '<td><span class="chip ' +
          chipClass +
          '">' +
          escapeHtml(row.Status || "") +
          "</span></td>" +
          "<td>" +
          escapeHtml(row.Catatan || "-") +
          "</td>" +
          "</tr>"
        );
      })
      .join("");
  } catch (err) {
    console.error("Error refresh audit log:", err);
  }
}

/* ============================================
 * HALAMAN: Dashboard
 * ============================================ */

// Simpan referensi chart agar bisa di-destroy saat update
let dailyChart = null;
let donutChart = null;
let lineChart = null;

/**
 * Inisialisasi dashboard — fetch data dan render semua chart.
 * @param {string} period - 'week', 'month', atau 'all'
 */
async function initDashboard(period) {
  try {
    const response = await fetch(
      "/dashboard/api/data?period=" + encodeURIComponent(period),
    );
    const data = await response.json();

    if (!response.ok) {
      console.error("Error fetching dashboard data:", data);
      return;
    }

    renderDailyBarChart(data.daily || {});
    renderStatusDonutChart(data.status_distribution || {});
    renderWeeklyLineChart(data.weekly_trend || {});
    renderRekapTable(data.rekap || []);
    updatePresentCard(data.present_count, period); // tambah ini
  } catch (err) {
    console.error("Error loading dashboard:", err);
  }
}

function updatePresentCard(presentCount, period) {
  var percentEl = document.getElementById("presentPercent");
  var detailEl = document.getElementById("presentDetail");
  if (!percentEl || !detailEl) return;

  if (!presentCount) {
    percentEl.textContent = "--%";
    detailEl.textContent = "Gagal memuat data";
    return;
  }

  var labelPeriod =
    period === "week"
      ? "minggu ini"
      : period === "month"
        ? "bulan ini"
        : "semua waktu"; // tambah ini

  percentEl.textContent = presentCount.percent + "%";
  detailEl.textContent =
    presentCount.hadir_count +
    " kehadiran dari " +
    presentCount.total_record +
    " total absensi (" +
    labelPeriod +
    ")";
}

/**
 * Callback untuk tombol filter period.
 */
function changeFilter(period, btn) {
  // Update tombol aktif
  const buttons = document.querySelectorAll(
    "#periodFilter .segmented-control__btn",
  );
  buttons.forEach(function (b) {
    b.classList.remove("segmented-control__btn--active");
  });
  btn.classList.add("segmented-control__btn--active");

  // Re-fetch data
  initDashboard(period);
}

/**
 * Render bar chart — Kehadiran Harian.
 */
function renderDailyBarChart(dailyData) {
  const ctx = document.getElementById("dailyBarChart");
  if (!ctx) return;

  if (dailyChart) dailyChart.destroy();

  const labels = Object.keys(dailyData);
  const values = Object.values(dailyData);

  dailyChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Jumlah Hadir",
          data: values,
          backgroundColor: "#CC0000",
          borderRadius: 4,
          maxBarThickness: 40,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            font: { family: "Inter", size: 12 },
            color: "#666666",
          },
        },
        y: {
          beginAtZero: true,
          grid: { color: "#F0F0F0" },
          ticks: {
            font: { family: "Inter", size: 12 },
            color: "#666666",
            stepSize: 1,
          },
        },
      },
    },
  });
}

/**
 * Render donut chart — Distribusi Status.
 */
function renderStatusDonutChart(statusData) {
  const ctx = document.getElementById("statusDonutChart");
  if (!ctx) return;

  if (donutChart) donutChart.destroy();

  const labels = Object.keys(statusData);
  const values = Object.values(statusData);
  const colors = labels.map(function (label) {
    switch (label) {
      case "Hadir":
        return "#1E7E34";
      case "WFH":
        return "#28A745";
      case "Izin":
        return "#B45309";
      case "Sakit":
        return "#CC0000";
      default:
        return "#999999";
    }
  });

  donutChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [
        {
          data: values,
          backgroundColor: colors,
          borderWidth: 0,
          hoverOffset: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "60%",
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            font: { family: "Inter", size: 12 },
            color: "#1A1C1C",
            padding: 16,
            usePointStyle: true,
            pointStyleWidth: 10,
          },
        },
      },
    },
  });
}

/**
 * Render line chart — Tren Mingguan.
 */
function renderWeeklyLineChart(weeklyData) {
  const ctx = document.getElementById("weeklyLineChart");
  if (!ctx) return;

  if (lineChart) lineChart.destroy();

  const labels = Object.keys(weeklyData);
  const values = Object.values(weeklyData);

  lineChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Total Kehadiran",
          data: values,
          borderColor: "#CC0000",
          backgroundColor: "rgba(204, 0, 0, 0.05)",
          fill: true,
          tension: 0.3,
          pointRadius: 4,
          pointBackgroundColor: "#CC0000",
          pointBorderColor: "#FFFFFF",
          pointBorderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            font: { family: "Inter", size: 12 },
            color: "#666666",
          },
        },
        y: {
          beginAtZero: true,
          grid: { color: "#F0F0F0" },
          ticks: {
            font: { family: "Inter", size: 12 },
            color: "#666666",
            stepSize: 1,
          },
        },
      },
    },
  });
}

/**
 * Render tabel rekap per karyawan (termasuk label kluster).
 */
function renderRekapTable(rekapData) {
  const tbody = document.getElementById("rekapBody");
  if (!tbody) return;

  if (!rekapData || rekapData.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="5" class="empty-state">Belum ada data untuk ditampilkan</td></tr>';
    return;
  }

  tbody.innerHTML = rekapData
    .map(function (row) {
      let chipClass = "";
      if (row.kluster === "Konsisten") chipClass = "chip--success";
      else if (row.kluster === "Sering Izin") chipClass = "chip--pending";
      else if (row.kluster === "Tidak Konsisten") chipClass = "chip--critical";

      return (
        "<tr>" +
        "<td>" +
        escapeHtml(row.nama || "") +
        "</td>" +
        "<td>" +
        (row.total_hadir || 0) +
        "</td>" +
        "<td>" +
        (row.izin || 0) +
        "</td>" +
        "<td>" +
        (row.sakit || 0) +
        "</td>" +
        '<td><span class="chip ' +
        chipClass +
        '">' +
        escapeHtml(row.kluster || "-") +
        "</span></td>" +
        "</tr>"
      );
    })
    .join("");
}

/**
 * Export data rekap ke file .xlsx.
 */
function exportXlsx() {
  window.location.href = "/dashboard/api/export";
}

/* ============================================
 * HALAMAN: Artikel Generator
 * ============================================ */

// State artikel
let currentTone = "formal";
let articleGenerated = false;

function initArtikelForm() {
  const form = document.getElementById("artikelForm");
  if (!form) return;

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    generateArtikel();
  });
}

/**
 * Set tone (Formal / Santai) melalui segmented control.
 */
function setTone(tone, btn) {
  currentTone = tone;
  const buttons = document.querySelectorAll(
    "#toneControl .segmented-control__btn",
  );
  buttons.forEach(function (b) {
    b.classList.remove("segmented-control__btn--active");
  });
  btn.classList.add("segmented-control__btn--active");
}

/**
 * Generate artikel via Groq API.
 */
async function generateArtikel() {
  const generateBtn = document.getElementById("generateBtn");
  const errorBanner = document.getElementById("artikelErrorBanner");
  const errorMessage = document.getElementById("artikelErrorMessage");
  const preview = document.getElementById("artikelPreview");
  const wordcloudImage = document.getElementById("wordcloudImage");
  const wordcloudPlaceholder = document.getElementById("wordcloudPlaceholder");

  // Ambil nilai form
  const topik = document.getElementById("topikArtikel").value.trim();
  const keywords = document.getElementById("keywords").value.trim();
  const panjangSlider = document.getElementById("panjangArtikel");
  const panjangMap = ["pendek", "sedang", "panjang"];
  const panjang = panjangMap[parseInt(panjangSlider.value)] || "sedang";

  // Validasi
  if (!topik) {
    showBanner(errorBanner, "Topik artikel wajib diisi");
    return;
  }

  // Loading state
  generateBtn.disabled = true;
  generateBtn.classList.add("btn--loading");
  hideBanner(errorBanner);
  preview.value = "Sedang membuat artikel...";

  try {
    const response = await fetch("/artikel/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topik: topik,
        keywords: keywords,
        tone: currentTone,
        panjang: panjang,
      }),
    });

    const data = await response.json();

    if (response.ok && data.success) {
      // Tampilkan artikel di preview
      preview.value = data.article_text || "";

      // Tampilkan word cloud
      if (data.wordcloud_url && wordcloudImage) {
        wordcloudImage.src = data.wordcloud_url;
        wordcloudImage.style.display = "block";
        if (wordcloudPlaceholder) wordcloudPlaceholder.style.display = "none";
      }

      // Aktifkan tombol download
      document.getElementById("downloadDocxBtn").disabled = false;
      var wcBtn = document.getElementById("downloadWordcloudBtn");
      if (wcBtn) wcBtn.disabled = false;
      articleGenerated = true;
    } else {
      showBanner(errorBanner, data.message || "Gagal generate artikel");
      preview.value = "";
    }
  } catch (err) {
    console.error("Error generate artikel:", err);
    showBanner(errorBanner, "Gagal terhubung ke server");
    preview.value = "";
  } finally {
    generateBtn.disabled = false;
    generateBtn.classList.remove("btn--loading");
  }
}

/**
 * Download artikel sebagai file .docx.
 */
function downloadDocx() {
  if (!articleGenerated) return;
  window.location.href = "/artikel/download/docx";
}

/**
 * Download word cloud sebagai file .png.
 */
function downloadWordcloud() {
  if (!articleGenerated) return;
  window.location.href = "/artikel/download/wordcloud";
}

/* ============================================
 * HALAMAN: Login & Face Verification
 * ============================================ */

// State untuk login dan face verification
let webcamStream = null;
let faceAttemptCount = 0;
let maxFaceAttempts = 3;
let lockoutTimerInterval = null;

/**
 * Inisialisasi form login — attach event handlers.
 */
function initLoginForm() {
  const form = document.getElementById("loginForm");
  if (!form) return;

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    submitLogin();
  });

  // Setup file upload fallback handler
  const uploadInput = document.getElementById("faceUploadInput");
  if (uploadInput) {
    uploadInput.addEventListener("change", handleFaceUpload);
  }
}

/**
 * Submit username + password ke backend.
 * Jika valid, buka modal face verification.
 */
async function submitLogin() {
  const submitBtn = document.getElementById("loginSubmitBtn");
  const errorBanner = document.getElementById("loginErrorBanner");
  const lockoutBanner = document.getElementById("lockoutBanner");

  const username = document.getElementById("loginUsername").value.trim();
  const password = document.getElementById("loginPassword").value.trim();

  // Validasi input
  if (!username || !password) {
    showBanner(errorBanner, "Username dan password wajib diisi");
    return;
  }

  // Loading state
  submitBtn.disabled = true;
  submitBtn.classList.add("btn--loading");
  hideBanner(errorBanner);
  hideBanner(lockoutBanner);

  try {
    const response = await fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: username, password: password }),
    });

    const data = await response.json();

    if (response.status === 423) {
      // Akun terkunci
      showBanner(lockoutBanner, data.message || "Akun terkunci");
      if (data.remaining_seconds) {
        startLockoutCountdown(data.remaining_seconds, "lockoutMessage");
      }
      return;
    }

    if (!response.ok || !data.success) {
      showBanner(errorBanner, data.message || "Username atau password salah");
      return;
    }

    if (data.needs_face_verification) {
      // Password valid — buka modal face verification
      faceAttemptCount = 0;
      openFaceModal();
    } else {
      // Login berhasil tanpa face verification
      window.location.href = "/absensi";
    }
  } catch (err) {
    console.error("Error login:", err);
    showBanner(errorBanner, "Gagal terhubung ke server");
  } finally {
    submitBtn.disabled = false;
    submitBtn.classList.remove("btn--loading");
  }
}

/**
 * Buka modal face verification dan mulai webcam.
 */
function openFaceModal() {
  const modal = document.getElementById("faceModal");
  if (!modal) return;

  modal.classList.add("face-modal--visible");
  resetFaceModalUI();
  startWebcam();
}

/**
 * Tutup modal face verification dan hentikan webcam.
 */
function closeFaceModal() {
  const modal = document.getElementById("faceModal");
  if (!modal) return;

  modal.classList.remove("face-modal--visible");
  stopWebcam();
  clearLockoutTimer();
}

/**
 * Mulai webcam stream via getUserMedia.
 * Jika gagal (kamera tidak tersedia), tampilkan fallback upload.
 */
async function startWebcam() {
  const video = document.getElementById("webcamVideo");
  const placeholder = document.getElementById("webcamPlaceholder");
  const uploadFallback = document.getElementById("uploadFallback");
  const captureBtn = document.getElementById("captureBtn");

  if (!video) return;

  try {
    // Minta akses kamera
    webcamStream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 320 },
        height: { ideal: 240 },
        facingMode: "user",
      },
      audio: false,
    });

    video.srcObject = webcamStream;
    video.style.display = "block";

    // Sembunyikan placeholder setelah video mulai
    video.addEventListener("loadeddata", function () {
      if (placeholder) placeholder.classList.add("webcam-placeholder--hidden");
    });

    // Tampilkan tombol capture
    if (captureBtn) captureBtn.style.display = "flex";
    if (uploadFallback) uploadFallback.style.display = "none";
  } catch (err) {
    console.warn("Kamera tidak tersedia:", err);

    // Tampilkan fallback upload
    if (placeholder) {
      placeholder.innerHTML =
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">' +
        '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>' +
        '<line x1="1" y1="1" x2="23" y2="23"/>' +
        "</svg>" +
        "<span>Kamera tidak tersedia</span>";
    }

    if (captureBtn) captureBtn.style.display = "none";
    if (uploadFallback) uploadFallback.style.display = "block";
  }
}

/**
 * Hentikan webcam stream (matikan semua tracks).
 */
function stopWebcam() {
  if (webcamStream) {
    webcamStream.getTracks().forEach(function (track) {
      track.stop();
    });
    webcamStream = null;
  }

  const video = document.getElementById("webcamVideo");
  if (video) {
    video.srcObject = null;
    video.style.display = "block";
  }
}

/**
 * Ambil frame dari webcam, convert ke base64, kirim ke backend.
 */
async function captureFrame() {
  const video = document.getElementById("webcamVideo");
  const canvas = document.getElementById("webcamCanvas");
  if (!video || !canvas) return;

  // Setup canvas sesuai ukuran video
  canvas.width = video.videoWidth || 320;
  canvas.height = video.videoHeight || 240;

  // Draw frame dari video ke canvas
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  // Convert canvas ke base64 JPEG
  const imageBase64 = canvas.toDataURL("image/jpeg", 0.85);

  // Kirim ke backend untuk verifikasi
  await sendFaceVerification(imageBase64);
}

/**
 * Handle file upload sebagai fallback ketika kamera tidak tersedia.
 */
function handleFaceUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  // Validasi tipe file
  if (!file.type.startsWith("image/")) {
    alert("File harus berupa gambar (JPG, PNG, dll.)");
    return;
  }

  const reader = new FileReader();
  reader.onload = async function (e) {
    const imageBase64 = e.target.result;
    await sendFaceVerification(imageBase64);
  };
  reader.readAsDataURL(file);
}

/**
 * Kirim gambar base64 ke endpoint /verify-face.
 * Handle semua response: success, failed, locked.
 */
async function sendFaceVerification(imageBase64) {
  const captureBtn = document.getElementById("captureBtn");
  const retryBtn = document.getElementById("retryBtn");
  const processing = document.getElementById("faceProcessing");
  const successBanner = document.getElementById("faceSuccessBanner");
  const failBanner = document.getElementById("faceFailBanner");
  const lockoutDisplay = document.getElementById("faceLockout");
  const attemptCurrent = document.getElementById("attemptCurrent");

  // Tampilkan loading
  if (captureBtn) captureBtn.disabled = true;
  if (processing) processing.style.display = "flex";
  if (successBanner) successBanner.style.display = "none";
  if (failBanner) failBanner.style.display = "none";

  try {
    const response = await fetch("/verify-face", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: imageBase64 }),
    });

    const data = await response.json();

    // Sembunyikan processing
    if (processing) processing.style.display = "none";

    if (response.status === 423) {
      // Akun terkunci
      if (captureBtn) captureBtn.style.display = "none";
      if (retryBtn) retryBtn.style.display = "none";
      if (lockoutDisplay) lockoutDisplay.style.display = "flex";

      if (data.remaining_seconds) {
        startLockoutCountdown(data.remaining_seconds, "lockoutTimerDisplay");
      }
      return;
    }

    // Show fallback-mode badge if opencv was used instead of face_recognition
    if (data.face_method === "opencv_fallback") {
      _showFallbackToast();
    }

    if (data.match) {
      // Verifikasi berhasil
      if (successBanner) {
        successBanner.style.display = "flex";
        var successMsg = document.getElementById("faceSuccessMessage");
        if (successMsg)
          successMsg.textContent = data.message || "Verifikasi berhasil!";
      }

      if (captureBtn) captureBtn.style.display = "none";
      if (retryBtn) retryBtn.style.display = "none";

      // Stop webcam
      stopWebcam();

      // Auto-redirect setelah 2 detik
      setTimeout(function () {
        window.location.href = "/absensi";
      }, 2000);
    } else {
      // Verifikasi gagal
      faceAttemptCount++;
      if (attemptCurrent) attemptCurrent.textContent = faceAttemptCount;

      if (failBanner) {
        failBanner.style.display = "flex";
        var failMsg = document.getElementById("faceFailMessage");
        if (failMsg)
          failMsg.textContent = data.message || "Wajah tidak dikenali";
      }

      if (captureBtn) captureBtn.disabled = false;
      if (retryBtn) retryBtn.style.display = "flex";
    }
  } catch (err) {
    console.error("Error verifikasi wajah:", err);
    if (processing) processing.style.display = "none";

    if (failBanner) {
      failBanner.style.display = "flex";
      var failMsg = document.getElementById("faceFailMessage");
      if (failMsg) failMsg.textContent = "Gagal terhubung ke server";
    }

    if (captureBtn) captureBtn.disabled = false;
  }
}

/**
 * Reset UI modal face verification untuk percobaan ulang.
 */
function retryFaceCapture() {
  var failBanner = document.getElementById("faceFailBanner");
  var captureBtn = document.getElementById("captureBtn");
  var retryBtn = document.getElementById("retryBtn");
  var uploadInput = document.getElementById("faceUploadInput");

  if (failBanner) failBanner.style.display = "none";
  if (captureBtn) captureBtn.disabled = false;
  if (retryBtn) retryBtn.style.display = "none";
  if (uploadInput) uploadInput.value = "";
}

/**
 * Reset semua element di face modal ke state awal.
 */
function resetFaceModalUI() {
  var processing = document.getElementById("faceProcessing");
  var successBanner = document.getElementById("faceSuccessBanner");
  var failBanner = document.getElementById("faceFailBanner");
  var lockoutDisplay = document.getElementById("faceLockout");
  var captureBtn = document.getElementById("captureBtn");
  var retryBtn = document.getElementById("retryBtn");
  var attemptCurrent = document.getElementById("attemptCurrent");
  var placeholder = document.getElementById("webcamPlaceholder");

  if (processing) processing.style.display = "none";
  if (successBanner) successBanner.style.display = "none";
  if (failBanner) failBanner.style.display = "none";
  if (lockoutDisplay) lockoutDisplay.style.display = "none";
  if (captureBtn) {
    captureBtn.style.display = "flex";
    captureBtn.disabled = false;
  }
  if (retryBtn) retryBtn.style.display = "none";
  if (attemptCurrent) attemptCurrent.textContent = "0";
  if (placeholder) placeholder.classList.remove("webcam-placeholder--hidden");
}

/**
 * Batal verifikasi wajah — tutup modal, kembali ke form login.
 */
function cancelFaceVerification() {
  closeFaceModal();
}

/**
 * Mulai countdown timer lockout.
 * @param {number} seconds - Detik tersisa lockout
 * @param {string} displayElementId - ID element untuk tampilkan timer
 */
function startLockoutCountdown(seconds, displayElementId) {
  clearLockoutTimer();

  var remaining = seconds;
  var display = document.getElementById(displayElementId);

  function updateDisplay() {
    var mins = Math.floor(remaining / 60);
    var secs = remaining % 60;
    if (display) {
      display.textContent = mins + ":" + (secs < 10 ? "0" : "") + secs;
    }
  }

  updateDisplay();

  lockoutTimerInterval = setInterval(function () {
    remaining--;
    if (remaining <= 0) {
      clearLockoutTimer();
      // Reload halaman untuk reset state
      window.location.reload();
    } else {
      updateDisplay();
    }
  }, 1000);
}

/**
 * Bersihkan interval countdown lockout.
 */
function clearLockoutTimer() {
  if (lockoutTimerInterval) {
    clearInterval(lockoutTimerInterval);
    lockoutTimerInterval = null;
  }
}

/* ============================================
 * UTILITY FUNCTIONS
 * ============================================ */

/**
 * Tampilkan banner dengan pesan tertentu.
 */
function showBanner(banner, message) {
  if (!banner) return;
  const span = banner.querySelector("span");
  if (span && message) span.textContent = message;
  banner.classList.add("banner--visible");

  // Auto-hide setelah 5 detik
  setTimeout(function () {
    hideBanner(banner);
  }, 5000);
}

/**
 * Sembunyikan banner.
 */
function hideBanner(banner) {
  if (!banner) return;
  banner.classList.remove("banner--visible");
}

/**
 * Escape HTML untuk mencegah XSS.
 */
function escapeHtml(str) {
  if (!str) return "";
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Tampilkan toast/badge kuning ketika face verification menggunakan
 * fallback mode OpenCV (bukan face_recognition).
 * Toast akan hilang otomatis setelah 6 detik.
 */
function _showFallbackToast() {
  // Reuse existing element if already in DOM
  var toastId = "fallbackModeToast";
  var existing = document.getElementById(toastId);
  if (existing) {
    existing.style.display = "flex";
    return;
  }

  var toast = document.createElement("div");
  toast.id = toastId;
  toast.setAttribute(
    "style",
    [
      "position:fixed",
      "top:1rem",
      "right:1rem",
      "z-index:9999",
      "display:flex",
      "align-items:center",
      "gap:0.5rem",
      "padding:0.6rem 1rem",
      "background:#FEF3C7",
      "border:1.5px solid #D97706",
      "border-radius:8px",
      "color:#92400E",
      "font-size:0.82rem",
      "font-family:Inter,sans-serif",
      "box-shadow:0 2px 8px rgba(0,0,0,0.12)",
      "max-width:320px",
    ].join(";"),
  );

  toast.innerHTML =
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0">' +
    '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>' +
    '<line x1="12" y1="9" x2="12" y2="13"/>' +
    '<line x1="12" y1="17" x2="12.01" y2="17"/>' +
    "</svg>" +
    "<span><strong>Mode Fallback Aktif</strong> &mdash; Verifikasi menggunakan OpenCV (akurasi lebih rendah). Instal <code>face_recognition</code> untuk akurasi penuh.</span>";

  document.body.appendChild(toast);

  // Auto-hide after 6s
  setTimeout(function () {
    if (toast.parentNode) toast.parentNode.removeChild(toast);
  }, 6000);
}
