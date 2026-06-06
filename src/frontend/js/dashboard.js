/**
 * dashboard.js
 *
 * Handles all file-management interactions on dashboard.html:
 *   • Load and render the user's file list
 *   • File upload (drag-and-drop + file picker)
 *   • Download (presigned URL)
 *   • Annotation edit (modal)
 *   • File delete
 */

"use strict";

// ---- DOM references ----
const fileTableBody       = document.getElementById("file-table-body");
const emptyState          = document.getElementById("empty-state");
const uploadZone          = document.getElementById("upload-zone");
const fileInput           = document.getElementById("file-input");
const annotationInput     = document.getElementById("upload-annotation");
const uploadProgressWrap  = document.getElementById("upload-progress-wrapper");
const uploadProgressBar   = document.getElementById("upload-progress-bar");
const toastContainer      = document.getElementById("toast-container");
const pageSpinner         = document.getElementById("page-spinner");

// Annotation edit modal (Bootstrap modal instance created in init)
let annotationModal;
let editingFileId = null;

// ============================================================
// Initialisation
// ============================================================

async function init() {
  // Guard: must be authenticated
  if (!AUTH.isAuthenticated()) {
    window.location.replace("index.html");
    return;
  }

  // Show user email in navbar
  const emailEl = document.getElementById("user-email");
  if (emailEl) emailEl.textContent = AUTH.getUserEmail();

  // Bootstrap modal
  annotationModal = new bootstrap.Modal(document.getElementById("annotation-modal"));

  // Wire up upload zone events
  uploadZone.addEventListener("click", () => fileInput.click());
  uploadZone.addEventListener("dragover",  e => { e.preventDefault(); uploadZone.classList.add("drag-over"); });
  uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("drag-over"));
  uploadZone.addEventListener("drop",      e => { e.preventDefault(); uploadZone.classList.remove("drag-over"); handleFileDrop(e.dataTransfer.files); });
  fileInput.addEventListener("change",    () => handleFileDrop(fileInput.files));

  // Save annotation button
  document.getElementById("btn-save-annotation").addEventListener("click", saveAnnotation);

  await loadFiles();
}

// ============================================================
// Load files
// ============================================================

async function loadFiles() {
  showSpinner(true);
  try {
    const res  = await AUTH.api("/api/files/");
    const data = await res.json();
    renderFiles(data.files ?? []);
  } catch (err) {
    showToast("Failed to load files: " + err.message, "danger");
  } finally {
    showSpinner(false);
  }
}

function renderFiles(files) {
  fileTableBody.innerHTML = "";

  if (files.length === 0) {
    emptyState.classList.remove("d-none");
    return;
  }
  emptyState.classList.add("d-none");

  files.forEach(f => {
    const row = document.createElement("tr");
    row.dataset.fileId = f.fileId;

    const annotation = f.annotation ?? "";
    const uploadDate = f.uploadDate
      ? new Date(f.uploadDate).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })
      : "—";
    const sizeLabel  = formatBytes(Number(f.fileSize ?? 0));
    const typeLabel  = (f.contentType ?? "").split("/")[1]?.toUpperCase() || "FILE";

    row.innerHTML = `
      <td>
        <div class="file-name" title="${esc(f.fileName)}">
          ${esc(f.fileName)}
        </div>
        <span class="badge-type">${esc(typeLabel)}</span>
      </td>
      <td class="text-nowrap">${uploadDate}</td>
      <td class="text-nowrap">${sizeLabel}</td>
      <td>
        <span class="annotation-cell ${annotation ? "" : "empty"}" title="${esc(annotation)}">
          ${annotation ? esc(annotation) : "No annotation"}
        </span>
      </td>
      <td class="text-nowrap">
        <button class="action-btn download" title="Download" onclick="downloadFile('${esc(f.fileId)}')">
          <i class="bi bi-download"></i>
        </button>
        <button class="action-btn edit" title="Edit annotation" onclick="openAnnotationModal('${esc(f.fileId)}', \`${esc(annotation)}\`)">
          <i class="bi bi-pencil"></i>
        </button>
        <button class="action-btn delete" title="Delete" onclick="deleteFile('${esc(f.fileId)}', '${esc(f.fileName)}')">
          <i class="bi bi-trash"></i>
        </button>
      </td>
    `;
    fileTableBody.appendChild(row);
  });
}

// ============================================================
// Upload
// ============================================================

async function handleFileDrop(fileList) {
  if (!fileList || fileList.length === 0) return;

  const file       = fileList[0]; // single-file upload per interaction
  const annotation = annotationInput.value.trim();

  const formData = new FormData();
  formData.append("file",       file);
  formData.append("annotation", annotation);

  // Show progress bar
  uploadProgressWrap.style.display = "block";
  uploadProgressBar.style.width = "0%";
  uploadProgressBar.setAttribute("aria-valuenow", "0");

  // Use XMLHttpRequest for real progress events
  const token = AUTH.getAccessToken();
  const xhr   = new XMLHttpRequest();
  xhr.open("POST", `${CONFIG.API_BASE_URL}/api/files/upload`);
  xhr.setRequestHeader("Authorization", `Bearer ${token}`);

  xhr.upload.addEventListener("progress", e => {
    if (e.lengthComputable) {
      const pct = Math.round((e.loaded / e.total) * 100);
      uploadProgressBar.style.width = pct + "%";
      uploadProgressBar.setAttribute("aria-valuenow", pct);
      const pctEl = document.getElementById("upload-pct");
      if (pctEl) pctEl.textContent = pct + "%";
    }
  });

  xhr.addEventListener("load", async () => {
    uploadProgressWrap.style.display = "none";
    fileInput.value = "";
    annotationInput.value = "";

    if (xhr.status === 201) {
      showToast("File uploaded successfully!", "success");
      await loadFiles();
    } else if (xhr.status === 401) {
      AUTH.login();
    } else {
      let msg = "Upload failed.";
      try { msg = JSON.parse(xhr.responseText).error ?? msg; } catch (_) {}
      showToast(msg, "danger");
    }
  });

  xhr.addEventListener("error", () => {
    uploadProgressWrap.style.display = "none";
    showToast("Network error during upload.", "danger");
  });

  xhr.send(formData);
}

// ============================================================
// Download
// ============================================================

async function downloadFile(fileId) {
  try {
    const res  = await AUTH.api(`/api/files/${fileId}/download`);
    const data = await res.json();
    if (!data.download_url) throw new Error("No download URL returned");
    // Open in a hidden <a> to trigger browser download
    const a = document.createElement("a");
    a.href = data.download_url;
    a.style.display = "none";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  } catch (err) {
    showToast("Download failed: " + err.message, "danger");
  }
}

// ============================================================
// Annotation modal
// ============================================================

function openAnnotationModal(fileId, currentAnnotation) {
  editingFileId = fileId;
  document.getElementById("annotation-textarea").value = currentAnnotation;
  annotationModal.show();
}

async function saveAnnotation() {
  if (!editingFileId) return;

  const text = document.getElementById("annotation-textarea").value.trim();

  try {
    const res = await AUTH.api(`/api/files/${editingFileId}/annotation`, {
      method:  "PUT",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ annotation: text }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error ?? "Update failed");
    }
    annotationModal.hide();
    showToast("Annotation saved.", "success");
    await loadFiles();
  } catch (err) {
    showToast("Failed to save annotation: " + err.message, "danger");
  } finally {
    editingFileId = null;
  }
}

// ============================================================
// Delete
// ============================================================

async function deleteFile(fileId, filename) {
  if (!confirm(`Delete "${filename}"? This action cannot be undone.`)) return;

  try {
    const res = await AUTH.api(`/api/files/${fileId}`, { method: "DELETE" });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error ?? "Delete failed");
    }
    showToast("File deleted.", "success");
    await loadFiles();
  } catch (err) {
    showToast("Delete failed: " + err.message, "danger");
  }
}

// ============================================================
// Utilities
// ============================================================

function formatBytes(bytes) {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return (bytes / Math.pow(1024, i)).toFixed(1) + " " + units[i];
}

/** Minimal HTML escaping to prevent XSS when injecting user data into innerHTML */
function esc(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;")
    .replace(/`/g, "&#96;");
}

function showSpinner(visible) {
  pageSpinner.style.display = visible ? "flex" : "none";
}

function showToast(message, type = "success") {
  const id = "toast-" + Date.now();
  const html = `
    <div id="${id}" class="toast align-items-center text-bg-${type} border-0 show" role="alert">
      <div class="d-flex">
        <div class="toast-body">${esc(message)}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
      </div>
    </div>`;
  toastContainer.insertAdjacentHTML("beforeend", html);
  const el = document.getElementById(id);
  const toast = new bootstrap.Toast(el, { delay: 4000 });
  toast.show();
  el.addEventListener("hidden.bs.toast", () => el.remove());
}

// ============================================================
// Boot
// ============================================================
document.addEventListener("DOMContentLoaded", init);
