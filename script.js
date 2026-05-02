/* =============================================
   SMART BOARD NOTES — SCRIPT.JS
   ============================================= */

(function() {
  'use strict';

  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const previewArea = document.getElementById('previewArea');
  const previewImg = document.getElementById('previewImg');
  const previewFilename = document.getElementById('previewFilename');
  const clearBtn = document.getElementById('clearBtn');
  const generateBtn = document.getElementById('generateBtn');
  const sampleBtn = document.getElementById('sampleBtn');
  const uploadPanel = document.getElementById('uploadPanel');
  const outputPanel = document.getElementById('outputPanel');
  const notesRender = document.getElementById('notesRender');
  const notesWrapper = document.getElementById('notesWrapper');
  const downloadBtn = document.getElementById('downloadBtn');
  const copyBtn = document.getElementById('copyBtn');
  const newBtn = document.getElementById('newBtn');
  const ocrDetails = document.getElementById('ocrDetails');
  const ocrPreview = document.getElementById('ocrPreview');
  const loadingOverlay = document.getElementById('loadingOverlay');
  const loaderSub = document.getElementById('loaderSub');
  const darkToggle = document.getElementById('darkToggle');
  const toast = document.getElementById('toast');

  let selectedFile = null;
  let toastTimer = null;

  // ---- DARK MODE ----
  function initDark() {
    if (localStorage.getItem('dark') === '1') document.body.setAttribute('data-dark', '');
    updateDarkIcon();
  }
  function updateDarkIcon() {
    darkToggle.textContent = document.body.hasAttribute('data-dark') ? '☀️' : '🌙';
  }
  darkToggle.addEventListener('click', () => {
    document.body.toggleAttribute('data-dark');
    localStorage.setItem('dark', document.body.hasAttribute('data-dark') ? '1' : '0');
    updateDarkIcon();
  });
  initDark();

  // ---- TOAST ----
  function showToast(msg, duration = 3000) {
    toast.textContent = msg;
    toast.classList.add('show');
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), duration);
  }

  // ---- FILE HANDLING ----
  function handleFile(file) {
    if (!file) return;
    const allowed = ['image/png','image/jpeg','image/jpg','image/gif','image/bmp','image/webp'];
    if (!allowed.includes(file.type)) { showToast('❌ Please upload a valid image file'); return; }
    if (file.size > 16 * 1024 * 1024) { showToast('❌ File too large. Max 16MB.'); return; }
    selectedFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
      previewImg.src = e.target.result;
      previewFilename.textContent = `${file.name} · ${(file.size/1024).toFixed(0)} KB`;
      previewArea.style.display = 'block';
      generateBtn.disabled = false;
      dropzone.style.display = 'none';
    };
    reader.readAsDataURL(file);
  }

  // The <label for="fileInput"> inside the dropzone already opens the file dialog natively.
  // Adding a separate dropzone click listener would fire it twice — so we skip it.
  fileInput.addEventListener('change', () => handleFile(fileInput.files[0]));
  dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('drag-over'); });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
  dropzone.addEventListener('drop', (e) => { e.preventDefault(); dropzone.classList.remove('drag-over'); handleFile(e.dataTransfer.files[0]); });

  clearBtn.addEventListener('click', () => {
    selectedFile = null; fileInput.value = '';
    previewArea.style.display = 'none'; dropzone.style.display = 'block'; generateBtn.disabled = true;
  });

  // ---- LOADER ----
  function setLoaderStep(stepNum, subText) {
    loaderSub.textContent = subText;
    ['step1','step2','step3'].forEach((id, i) => {
      const el = document.getElementById(id);
      el.className = 'step';
      if (i < stepNum - 1) el.classList.add('done');
      else if (i === stepNum - 1) el.classList.add('active');
    });
  }
  function showLoader() { loadingOverlay.style.display = 'flex'; setLoaderStep(1, 'Extracting text from board...'); }
  function hideLoader() { loadingOverlay.style.display = 'none'; }

  // ---- GENERATE ----
  generateBtn.addEventListener('click', async () => {
    if (!selectedFile) return;
    showLoader();
    const formData = new FormData();
    formData.append('image', selectedFile);
    const t2 = setTimeout(() => setLoaderStep(2, 'AI is processing your notes...'), 1800);
    const t3 = setTimeout(() => setLoaderStep(3, 'Formatting beautiful notes...'), 4000);
    try {
      const res = await fetch('/process', { method: 'POST', body: formData });
      clearTimeout(t2); clearTimeout(t3);
      const data = await res.json();
      if (!res.ok || data.error) { hideLoader(); showToast('❌ ' + (data.error || 'Processing failed.'), 5000); return; }
      hideLoader(); renderNotes(data.notes_html, data.ocr_text); showToast('✅ Notes generated successfully!');
    } catch (err) {
      clearTimeout(t2); clearTimeout(t3); hideLoader();
      showToast('❌ Network error. Is the Flask server running?', 5000);
    }
  });

  // ---- SAMPLE ----
  sampleBtn.addEventListener('click', async () => {
    showLoader(); setLoaderStep(2, 'Loading sample notes...');
    try {
      const res = await fetch('/sample', { method: 'POST' });
      const data = await res.json();
      hideLoader();
      if (data.notes_html) { renderNotes(data.notes_html, ''); showToast('📚 Sample notes loaded!'); }
    } catch(e) { hideLoader(); showToast('❌ Could not load sample.'); }
  });

  // ---- RENDER ----
  function renderNotes(html, ocr) {
    notesRender.innerHTML = html;
    uploadPanel.style.display = 'none';
    outputPanel.style.display = 'block';
    if (ocr && ocr.length > 5) {
      ocrPreview.textContent = ocr;
      ocrDetails.style.display = 'block';
    } else {
      ocrDetails.style.display = 'none';
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // ---- COPY NOTES ----
  copyBtn.addEventListener('click', () => {
    const text = notesRender.innerText;
    if (!text) { showToast('❌ Nothing to copy'); return; }
    navigator.clipboard.writeText(text).then(() => {
      copyBtn.textContent = '✅ Copied!';
      setTimeout(() => { copyBtn.textContent = '📋 Copy Text'; }, 2500);
    }).catch(() => showToast('❌ Copy failed'));
  });

  // ---- NEW IMAGE ----
  newBtn.addEventListener('click', () => {
    outputPanel.style.display = 'none'; uploadPanel.style.display = 'block';
    notesRender.innerHTML = ''; ocrDetails.style.display = 'none';
    selectedFile = null; fileInput.value = '';
    previewArea.style.display = 'none'; dropzone.style.display = 'block'; generateBtn.disabled = true;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  // ---- LOAD SCRIPT HELPER ----
  function loadScript(src) {
    return new Promise((resolve, reject) => {
      if (document.querySelector(`script[src="${src}"]`)) { resolve(); return; }
      const s = document.createElement('script');
      s.src = src; s.onload = resolve;
      s.onerror = () => reject(new Error('Failed to load: ' + src));
      document.head.appendChild(s);
    });
  }

  // ---- PDF DOWNLOAD — pixel-perfect via html2canvas + jsPDF ----
  downloadBtn.addEventListener('click', async () => {
    if (!notesRender.innerHTML) { showToast('❌ No notes to download'); return; }

    downloadBtn.disabled = true;
    downloadBtn.textContent = '⏳ Preparing...';
    showToast('⏳ Capturing notes, please wait...', 15000);

    try {
      await loadScript('https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js');
      await loadScript('https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js');

      // Temporarily force grid background (since ::before pseudoelement may not capture)
      notesWrapper.style.setProperty('background-image',
        'linear-gradient(rgba(180,200,220,0.35) 1px, transparent 1px), linear-gradient(90deg, rgba(180,200,220,0.35) 1px, transparent 1px)');
      notesWrapper.style.setProperty('background-size', '32px 32px');
      notesWrapper.style.setProperty('background-color', '#fffdf9');

      const canvas = await html2canvas(notesWrapper, {
        scale: 2,
        useCORS: true,
        allowTaint: true,
        backgroundColor: '#fffdf9',
        logging: false,
        scrollX: 0,
        scrollY: -window.scrollY,
        width: notesWrapper.scrollWidth,
        height: notesWrapper.scrollHeight,
        onclone: (clonedDoc) => {
          const el = clonedDoc.getElementById('notesWrapper');
          if (el) {
            el.style.borderRadius = '0';
            el.style.boxShadow = 'none';
            el.style.border = 'none';
            el.style.backgroundImage = 'linear-gradient(rgba(180,200,220,0.35) 1px, transparent 1px), linear-gradient(90deg, rgba(180,200,220,0.35) 1px, transparent 1px)';
            el.style.backgroundSize = '32px 32px';
            el.style.backgroundColor = '#fffdf9';
          }
          // Force CSS variables to resolve in clone
          clonedDoc.documentElement.style.setProperty('--highlight-yellow', '#fff3b0');
          clonedDoc.documentElement.style.setProperty('--highlight-pink', '#ffd6e0');
          clonedDoc.documentElement.style.setProperty('--highlight-green', '#ccf5d6');
          clonedDoc.documentElement.style.setProperty('--highlight-blue', '#cce5ff');
          clonedDoc.documentElement.style.setProperty('--highlight-purple', '#e8d5ff');
          clonedDoc.documentElement.style.setProperty('--accent', '#4a90d9');
          clonedDoc.documentElement.style.setProperty('--border', '#e0d8ce');
          clonedDoc.documentElement.style.setProperty('--text', '#2d2a25');
          clonedDoc.documentElement.style.setProperty('--bg', '#f5f0eb');
          clonedDoc.documentElement.style.setProperty('--paper', '#fffdf9');
        }
      });

      // Restore styles
      notesWrapper.style.removeProperty('background-image');
      notesWrapper.style.removeProperty('background-size');
      notesWrapper.style.removeProperty('background-color');

      const { jsPDF } = window.jspdf;
      const A4_W = 210, A4_H = 297; // mm
      const pxPerMm = canvas.width / A4_W;
      const totalHeightMm = canvas.height / pxPerMm;

      const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
      let yMm = 0, page = 0;

      while (yMm < totalHeightMm) {
        if (page > 0) pdf.addPage();

        const sliceHeightMm = Math.min(A4_H, totalHeightMm - yMm);
        const sliceHeightPx = Math.ceil(sliceHeightMm * pxPerMm);
        const yOffsetPx = Math.floor(yMm * pxPerMm);

        const slice = document.createElement('canvas');
        slice.width = canvas.width;
        slice.height = sliceHeightPx;
        const ctx = slice.getContext('2d');
        ctx.fillStyle = '#fffdf9';
        ctx.fillRect(0, 0, slice.width, slice.height);
        ctx.drawImage(canvas, 0, yOffsetPx, canvas.width, sliceHeightPx, 0, 0, canvas.width, sliceHeightPx);

        pdf.addImage(slice.toDataURL('image/png'), 'PNG', 0, 0, A4_W, sliceHeightMm, '', 'FAST');

        yMm += A4_H;
        page++;
      }

      pdf.save('smart-board-notes.pdf');
      showToast('✅ PDF downloaded with full colors & formatting!');

    } catch (err) {
      console.error('PDF error:', err);
      showToast('❌ PDF failed: ' + err.message, 6000);
    } finally {
      downloadBtn.disabled = false;
      downloadBtn.textContent = '⬇ Download PDF';
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && loadingOverlay.style.display !== 'none') showToast('⏳ Please wait...');
  });

})();
