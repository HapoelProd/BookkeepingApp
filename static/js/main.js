/**
 * Hapoel Jerusalem Basketball - Bookkeeping Web App
 * Main JavaScript functionality
 */

// Global app state
window.HapoelApp = {
    currentSheet: 'without_ad',
    uploadInProgress: false,
    maxFileSize: 16 * 1024 * 1024, // 16MB
    allowedExtensions: ['csv']
};

/**
 * Initialize application when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * Main app initialization
 */
function initializeApp() {
    console.log('Hapoel Jerusalem Bookkeeping App initialized');

    // Initialize upload functionality
    initializeUpload();

    // Initialize results functionality (if on results page)
    initializeResults();

    // Initialize common UI features
    initializeCommonUI();
}

/**
 * Upload page functionality
 */
function initializeUpload() {
    const fileInput = document.getElementById('file');
    const uploadForm = document.getElementById('uploadForm');
    const uploadBtn = document.getElementById('uploadBtn');

    if (!fileInput || !uploadForm) return; // Not on upload page

    // File selection handler
    fileInput.addEventListener('change', handleFileSelection);

    // Form submission handler
    uploadForm.addEventListener('submit', handleFormSubmission);

    // Drag and drop functionality
    initializeDragAndDrop();
}

/**
 * Handle file selection
 */
function handleFileSelection(event) {
    const file = event.target.files[0];
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const fileLabelText = document.getElementById('file-label-text');
    const uploadBtn = document.getElementById('uploadBtn');

    if (!file) {
        resetFileSelection();
        return;
    }

    // Validate file
    const validation = validateFile(file);
    if (!validation.valid) {
        showError(validation.message);
        resetFileSelection();
        return;
    }

    // Update UI with file info
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    fileInfo.style.display = 'flex';
    uploadBtn.disabled = false;
    fileLabelText.textContent = 'קובץ נבחר בהצלחה ✓';

    // Add success styling
    const fileLabel = document.querySelector('.file-label');
    fileLabel.classList.add('file-selected');
}

/**
 * Validate uploaded file
 */
function validateFile(file) {
    // Check file size
    if (file.size > HapoelApp.maxFileSize) {
        return {
            valid: false,
            message: `גודל הקובץ גדול מדי. מקסימום: ${formatFileSize(HapoelApp.maxFileSize)}`
        };
    }

    // Check file extension
    const extension = file.name.split('.').pop().toLowerCase();
    if (!HapoelApp.allowedExtensions.includes(extension)) {
        return {
            valid: false,
            message: 'סוג קובץ לא נתמך. אנא העלה קובץ CSV בלבד.'
        };
    }

    return { valid: true };
}

/**
 * Reset file selection
 */
function resetFileSelection() {
    const fileInfo = document.getElementById('fileInfo');
    const fileLabelText = document.getElementById('file-label-text');
    const uploadBtn = document.getElementById('uploadBtn');
    const fileLabel = document.querySelector('.file-label');

    if (fileInfo) fileInfo.style.display = 'none';
    if (uploadBtn) uploadBtn.disabled = true;
    if (fileLabelText) fileLabelText.textContent = 'בחר קובץ CSV';
    if (fileLabel) fileLabel.classList.remove('file-selected');
}

/**
 * Handle form submission
 */
function handleFormSubmission(event) {
    if (HapoelApp.uploadInProgress) {
        event.preventDefault();
        return false;
    }

    HapoelApp.uploadInProgress = true;
    showLoadingModal();

    // Update button state
    const uploadBtn = document.getElementById('uploadBtn');
    if (uploadBtn) {
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> מעבד...';
    }
}

/**
 * Drag and drop functionality
 */
function initializeDragAndDrop() {
    const fileLabel = document.querySelector('.file-label');
    if (!fileLabel) return;

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        fileLabel.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight drop area
    ['dragenter', 'dragover'].forEach(eventName => {
        fileLabel.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        fileLabel.addEventListener(eventName, unhighlight, false);
    });

    // Handle dropped files
    fileLabel.addEventListener('drop', handleDrop, false);

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight(e) {
        fileLabel.classList.add('drag-over');
    }

    function unhighlight(e) {
        fileLabel.classList.remove('drag-over');
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;

        if (files.length > 0) {
            const fileInput = document.getElementById('file');
            fileInput.files = files;
            fileInput.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }
}

/**
 * Results page functionality
 */
function initializeResults() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    if (tabBtns.length === 0) return; // Not on results page

    // Tab switching functionality
    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const sheetName = this.dataset.sheet;
            switchTab(sheetName);
        });
    });

    // Initialize table features
    initializeTableFeatures();

    // Initialize export options
    initializeExportOptions();
}

/**
 * Switch between tabs
 */
function switchTab(sheetName) {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    // Remove active class from all buttons and contents
    tabBtns.forEach(btn => btn.classList.remove('active'));
    tabContents.forEach(content => content.classList.remove('active'));

    // Add active class to selected elements
    const activeBtn = document.querySelector(`[data-sheet="${sheetName}"]`);
    const activeContent = document.getElementById(`tab-${sheetName}`);

    if (activeBtn) activeBtn.classList.add('active');
    if (activeContent) activeContent.classList.add('active');

    // Update app state
    HapoelApp.currentSheet = sheetName;

    // Trigger custom event for other components
    document.dispatchEvent(new CustomEvent('sheetChanged', {
        detail: { sheetName }
    }));
}

/**
 * Table features
 */
function initializeTableFeatures() {
    const tables = document.querySelectorAll('.data-table');

    tables.forEach(table => {
        addTableUtilities(table);
    });
}

/**
 * Add utilities to tables
 */
function addTableUtilities(table) {
    const rows = table.querySelectorAll('tbody tr');

    rows.forEach(row => {
        row.addEventListener('click', function() {
            // Remove previous selections
            rows.forEach(r => r.classList.remove('selected'));
            // Add selection to current row
            this.classList.add('selected');
        });
    });
}

/**
 * Export options
 */
function initializeExportOptions() {
    const downloadBtns = document.querySelectorAll('.download-btn');

    downloadBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            // Add loading state
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> מוריד...';
            this.style.pointerEvents = 'none';

            // Reset after delay
            setTimeout(() => {
                this.innerHTML = '<i class="fas fa-download"></i> הורד קובץ Excel';
                this.style.pointerEvents = 'auto';
            }, 3000);
        });
    });
}

/**
 * Common UI functionality
 */
function initializeCommonUI() {
    // Auto-hide flash messages
    initializeFlashMessages();

    // Initialize responsive features
    initializeResponsiveFeatures();

    // Add keyboard shortcuts
    initializeKeyboardShortcuts();
}

/**
 * Flash messages auto-hide
 */
function initializeFlashMessages() {
    const flashMessages = document.querySelectorAll('.flash-message');

    flashMessages.forEach(message => {
        // Auto-hide success messages after 5 seconds
        if (message.classList.contains('flash-success')) {
            setTimeout(() => {
                message.style.opacity = '0';
                setTimeout(() => message.remove(), 300);
            }, 5000);
        }

        // Close button functionality
        const closeBtn = message.querySelector('.close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                message.style.opacity = '0';
                setTimeout(() => message.remove(), 300);
            });
        }
    });
}

/**
 * Responsive features
 */
function initializeResponsiveFeatures() {
    // Table horizontal scroll indicators
    addTableScrollIndicators();

    // Window resize handler
    window.addEventListener('resize', handleResize);
}

/**
 * Add scroll indicators to tables
 */
function addTableScrollIndicators() {
    const tableContainers = document.querySelectorAll('.table-container');

    tableContainers.forEach(container => {
        const table = container.querySelector('table');
        if (!table) return;

        // Check if table is scrollable
        function checkScroll() {
            const isScrollable = table.scrollWidth > container.clientWidth;
            container.classList.toggle('scrollable', isScrollable);
        }

        checkScroll();
        window.addEventListener('resize', checkScroll);
    });
}

/**
 * Keyboard shortcuts
 */
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + U: Go to upload page
        if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
            e.preventDefault();
            window.location.href = '/';
        }

        // Escape: Close modals
        if (e.key === 'Escape') {
            closeAllModals();
        }

        // Arrow keys: Navigate tabs (on results page)
        if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
            navigateTabsWithKeys(e.key);
        }
    });
}

/**
 * Navigate tabs with keyboard
 */
function navigateTabsWithKeys(direction) {
    const tabBtns = document.querySelectorAll('.tab-btn');
    if (tabBtns.length === 0) return;

    const activeTab = document.querySelector('.tab-btn.active');
    if (!activeTab) return;

    const currentIndex = Array.from(tabBtns).indexOf(activeTab);
    let nextIndex;

    if (direction === 'ArrowRight') {
        nextIndex = currentIndex > 0 ? currentIndex - 1 : tabBtns.length - 1;
    } else {
        nextIndex = currentIndex < tabBtns.length - 1 ? currentIndex + 1 : 0;
    }

    tabBtns[nextIndex].click();
}

/**
 * Utility Functions
 */

/**
 * Format file size for display
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Show loading modal
 */
function showLoadingModal() {
    const modal = document.getElementById('loadingModal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

/**
 * Hide loading modal
 */
function hideLoadingModal() {
    const modal = document.getElementById('loadingModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Close all modals
 */
function closeAllModals() {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.style.display = 'none';
    });
}

/**
 * Show error message
 */
function showError(message) {
    // Create flash message
    const flashContainer = document.querySelector('.flash-messages') ||
                          createFlashContainer();

    const flashMessage = document.createElement('div');
    flashMessage.className = 'flash-message flash-error';
    flashMessage.innerHTML = `
        <i class="fas fa-exclamation-triangle"></i>
        ${message}
        <button onclick="this.parentElement.remove()" class="close-btn">×</button>
    `;

    flashContainer.appendChild(flashMessage);

    // Auto-remove after 8 seconds
    setTimeout(() => {
        if (flashMessage.parentNode) {
            flashMessage.remove();
        }
    }, 8000);
}

/**
 * Show success message
 */
function showSuccess(message) {
    const flashContainer = document.querySelector('.flash-messages') ||
                          createFlashContainer();

    const flashMessage = document.createElement('div');
    flashMessage.className = 'flash-message flash-success';
    flashMessage.innerHTML = `
        <i class="fas fa-check-circle"></i>
        ${message}
        <button onclick="this.parentElement.remove()" class="close-btn">×</button>
    `;

    flashContainer.appendChild(flashMessage);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (flashMessage.parentNode) {
            flashMessage.remove();
        }
    }, 5000);
}

/**
 * Create flash message container if it doesn't exist
 */
function createFlashContainer() {
    const container = document.createElement('div');
    container.className = 'flash-messages';

    const mainContent = document.querySelector('.main-content .container');
    if (mainContent) {
        mainContent.insertBefore(container, mainContent.firstChild);
    }

    return container;
}

/**
 * Handle window resize
 */
function handleResize() {
    // Recalculate table scroll indicators
    addTableScrollIndicators();
}

// Export for external use
window.HapoelApp.utils = {
    formatFileSize,
    showError,
    showSuccess,
    showLoadingModal,
    hideLoadingModal,
    switchTab
};

console.log('Hapoel Jerusalem Basketball App JavaScript loaded successfully');