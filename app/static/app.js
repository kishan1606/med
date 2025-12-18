// Medical Report PDF Processor - Frontend JavaScript

// State
let uploadedFile = null;
let currentJobId = null;
let websocket = null;
let currentPages = [];

// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const uploadedFileDiv = document.getElementById('uploadedFile');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const removeFileBtn = document.getElementById('removeFile');
const processBtn = document.getElementById('processBtn');
const toggleConfigBtn = document.getElementById('toggleConfig');
const configContent = document.getElementById('configContent');
const progressSection = document.getElementById('progressSection');
const progressFill = document.getElementById('progressFill');
const progressStatus = document.getElementById('progressStatus');
const progressStep = document.getElementById('progressStep');
const progressDetail = document.getElementById('progressDetail');
const resultsSection = document.getElementById('resultsSection');
const resultsSummary = document.getElementById('resultsSummary');
const reportsContainer = document.getElementById('reportsContainer');
const jobsContainer = document.getElementById('jobsContainer');
const refreshJobsBtn = document.getElementById('refreshJobs');
const healthStatus = document.getElementById('healthStatus');
const configPresetSelect = document.getElementById('configPreset');
const loadPresetBtn = document.getElementById('loadPreset');
const applyOptimizedBtn = document.getElementById('applyOptimizedBtn');
const presetDescription = document.getElementById('presetDescription');
const presetMetadata = document.getElementById('presetMetadata');
const pageSelectionSection = document.getElementById('pageSelectionSection');
const pagesGrid = document.getElementById('pagesGrid');
const generatePdfBtn = document.getElementById('generatePdfBtn');
const selectAllBtn = document.getElementById('selectAllBtn');
const deselectAllBtn = document.getElementById('deselectAllBtn');
const selectUniquesBtn = document.getElementById('selectUniquesBtn');
const selectionCount = document.getElementById('selectionCount');

// Initialize (run immediately if DOM already loaded)
function init() {
    setupEventListeners();
    checkHealth();
    loadJobs();
    loadAvailableConfigs();

    // Diagnostic: Make functions available globally for testing
    window.testGeneratePdf = generatePdfWithSelection;
    window.applyOptimizedPreset = applyOptimizedPreset;
    console.log('🧪 Test function available: window.testGeneratePdf(), window.applyOptimizedPreset()');
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

function setupEventListeners() {
    // Upload area
    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);

    // File input
    fileInput.addEventListener('change', handleFileSelect);

    // Remove file
    removeFileBtn.addEventListener('click', removeFile);

    // Process button
    processBtn.addEventListener('click', startProcessing);

    // Toggle config
    toggleConfigBtn.addEventListener('click', toggleConfig);

    // Refresh jobs
    refreshJobsBtn.addEventListener('click', loadJobs);

    // Config preset
    configPresetSelect.addEventListener('change', updatePresetDescription);
    loadPresetBtn.addEventListener('click', loadSelectedPreset);
    if (applyOptimizedBtn) applyOptimizedBtn.addEventListener('click', applyOptimizedPreset);

    // Page selection
    selectAllBtn.addEventListener('click', selectAllPages);
    deselectAllBtn.addEventListener('click', deselectAllPages);
    selectUniquesBtn.addEventListener('click', selectOnlyUniques);

    console.log('📌 Setting up generatePdfBtn event listener');
    console.log('generatePdfBtn element:', generatePdfBtn);
    console.log('generatePdfBtn ID:', generatePdfBtn?.id);
    generatePdfBtn.addEventListener('click', generatePdfWithSelection);
    console.log('✅ generatePdfBtn event listener attached');

    // COMMENTED OUT: Report splitting disabled - no longer need dependency handling
    // const reportSplittingCheckbox = document.getElementById('enableReportSplitting');
    // const duplicateDetectionCheckbox = document.getElementById('enableDuplicateDetection');

    // reportSplittingCheckbox.addEventListener('change', function() {
    //     if (!this.checked) {
    //         // If report splitting is disabled, disable duplicate detection too
    //         duplicateDetectionCheckbox.checked = false;
    //         duplicateDetectionCheckbox.disabled = true;
    //         duplicateDetectionCheckbox.parentElement.style.opacity = '0.5';
    //     } else {
    //         // If report splitting is enabled, allow duplicate detection to be toggled
    //         duplicateDetectionCheckbox.disabled = false;
    //         duplicateDetectionCheckbox.parentElement.style.opacity = '1';
    //     }
    // });

    // // Initialize the state on page load
    // if (!reportSplittingCheckbox.checked) {
    //     duplicateDetectionCheckbox.checked = false;
    //     duplicateDetectionCheckbox.disabled = true;
    //     duplicateDetectionCheckbox.parentElement.style.opacity = '0.5';
    // }
}

// Health Check
async function checkHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();

        const statusDot = healthStatus.querySelector('.status-dot');
        const statusText = healthStatus.querySelector('span:last-child');

        if (data.status === 'healthy') {
            statusDot.classList.remove('error');
            statusText.textContent = data.tesseract_available
                ? 'System Ready (OCR Available)'
                : 'System Ready (OCR Not Available)';
        } else {
            statusDot.classList.add('error');
            statusText.textContent = 'System Error';
        }
    } catch (error) {
        console.error('Health check failed:', error);
        healthStatus.querySelector('.status-dot').classList.add('error');
        healthStatus.querySelector('span:last-child').textContent = 'Connection Error';
    }
}

// File Upload Handlers
function handleDragOver(e) {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

async function handleFile(file) {
    // Validate file type
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        alert('Please select a PDF file');
        return;
    }

    // Validate file size (100 MB)
    const maxSize = 100 * 1024 * 1024;
    if (file.size > maxSize) {
        alert('File size exceeds 100 MB limit');
        return;
    }

    // Upload file
    const formData = new FormData();
    formData.append('file', file);

    try {
        processBtn.disabled = true;
        processBtn.textContent = 'Uploading...';

        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const data = await response.json();

        // Update UI
        uploadedFile = data.filename;
        fileName.textContent = data.filename;
        fileSize.textContent = `${data.size_mb} MB`;
        uploadArea.style.display = 'none';
        uploadedFileDiv.style.display = 'flex';
        processBtn.disabled = false;
        processBtn.textContent = 'Process PDF';

    } catch (error) {
        console.error('Upload error:', error);
        alert(`Upload failed: ${error.message}`);
        processBtn.disabled = true;
        processBtn.textContent = 'Process PDF';
    }
}

function removeFile() {
    uploadedFile = null;
    uploadArea.style.display = 'block';
    uploadedFileDiv.style.display = 'none';
    fileInput.value = '';
    processBtn.disabled = true;
    resultsSection.style.display = 'none';
    progressSection.style.display = 'none';
}

// Configuration
function toggleConfig() {
    if (configContent.style.display === 'none') {
        configContent.style.display = 'grid';
        toggleConfigBtn.textContent = 'Hide Options';
    } else {
        configContent.style.display = 'none';
        toggleConfigBtn.textContent = 'Show Options';
    }
}

function getConfiguration() {
    return {
        pdf_dpi: parseInt(document.getElementById('pdfDpi').value),
        variance_threshold: parseFloat(document.getElementById('varianceThreshold').value),
        edge_threshold: parseInt(document.getElementById('edgeThreshold').value),
        white_pixel_ratio: parseFloat(document.getElementById('whitePixelRatio').value),
        use_edge_detection: document.getElementById('useEdgeDetection').checked,
        // Report splitting fields commented out - functionality disabled
        // enable_report_splitting: document.getElementById('enableReportSplitting').checked,
        // use_ocr: document.getElementById('useOcr').checked,
        // ocr_language: document.getElementById('ocrLanguage').value,
        // min_confidence: parseInt(document.getElementById('minConfidence').value),
        enable_duplicate_detection: document.getElementById('enableDuplicateDetection').checked,
        hash_algorithm: document.getElementById('hashAlgorithm').value,
        similarity_threshold: parseFloat(document.getElementById('similarityThreshold').value),
        hamming_distance_threshold: parseInt(document.getElementById('hammingDistance').value),
    };
}

// Processing
async function startProcessing() {
    if (!uploadedFile) {
        alert('Please upload a file first');
        return;
    }

    const config = getConfiguration();
    console.log('Starting processing with config:', config);

    try {
        processBtn.disabled = true;
        processBtn.textContent = 'Starting...';
        resultsSection.style.display = 'none';

        const response = await fetch(`/api/process?filename=${encodeURIComponent(uploadedFile)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Processing failed to start');
        }

        const data = await response.json();
        currentJobId = data.job_id;

        // Show progress section
        progressSection.style.display = 'block';
        progressSection.scrollIntoView({ behavior: 'smooth' });

        // Connect WebSocket for real-time updates
        connectWebSocket(currentJobId);

        // Also poll status as backup
        pollJobStatus(currentJobId);

    } catch (error) {
        console.error('Processing error:', error);
        alert(`Failed to start processing: ${error.message}`);
        processBtn.disabled = false;
        processBtn.textContent = 'Process PDF';
    }
}

function connectWebSocket(jobId) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws/${jobId}`;

    websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
        console.log('WebSocket connected');
    };

    websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateProgress(data);
    };

    websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    websocket.onclose = () => {
        console.log('WebSocket closed');
    };
}

async function pollJobStatus(jobId) {
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`/api/jobs/${jobId}`);
            const data = await response.json();

            if (data.status === 'completed') {
                clearInterval(interval);
                if (websocket) websocket.close();
                showResults(data.result);
                processBtn.disabled = false;
                processBtn.textContent = 'Process Another PDF';
                loadJobs();
            } else if (data.status === 'failed') {
                clearInterval(interval);
                if (websocket) websocket.close();
                showError(data.error);
                processBtn.disabled = false;
                processBtn.textContent = 'Try Again';
                loadJobs();
            }
        } catch (error) {
            console.error('Status poll error:', error);
        }
    }, 2000);
}

function updateProgress(data) {
    progressFill.style.width = `${data.progress}%`;

    // Map progress percentage to step number and milestone
    let currentStep = 1;
    let totalSteps = 5;
    let milestone = data.current_step || data.message || 'Processing...';

    // Determine current step based on progress percentage
    if (data.progress <= 20) {
        currentStep = 1;
        if (!milestone || milestone === 'Processing...') {
            milestone = 'Extracting PDF pages';
        }
    } else if (data.progress <= 40) {
        currentStep = 2;
        if (!milestone || milestone === 'Processing...') {
            milestone = 'Detecting blank pages';
        }
    } else if (data.progress <= 60) {
        currentStep = 3;
        if (!milestone || milestone === 'Processing...') {
            milestone = 'Analyzing reports';
        }
    } else if (data.progress <= 80) {
        currentStep = 4;
        if (!milestone || milestone === 'Processing...') {
            milestone = 'Checking for duplicates';
        }
    } else if (data.progress < 100) {
        currentStep = 5;
        if (!milestone || milestone === 'Processing...') {
            milestone = 'Saving processed reports';
        }
    } else {
        currentStep = 5;
        milestone = 'Completed';
    }

    // Update UI elements
    progressStatus.textContent = milestone;
    progressStep.textContent = `Step ${currentStep} of ${totalSteps}`;

    // Show detailed message if available
    if (data.message && data.message !== milestone) {
        progressDetail.textContent = data.message;
    } else if (data.current_step && data.current_step !== milestone) {
        progressDetail.textContent = data.current_step;
    } else {
        progressDetail.textContent = '';
    }
}

function showResults(result) {
    if (!result) return;

    currentJobId = result.job_id;

    // Hide progress
    progressSection.style.display = 'none';

    // Check if user selection is required
    if (result.requires_user_selection && result.pages && result.pages.length > 0) {
        // Show page selection UI
        showPageSelection(result);
        return;
    }

    // Normal results display
    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth' });

    // Summary stats
    resultsSummary.innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${result.total_pages}</div>
            <div class="stat-label">Total Pages</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${result.blank_pages}</div>
            <div class="stat-label">Blank Pages Removed</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${result.reports_found}</div>
            <div class="stat-label">Reports Found</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${result.duplicate_reports}</div>
            <div class="stat-label">Duplicates Removed</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${result.unique_reports}</div>
            <div class="stat-label">Unique Reports</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${result.processing_time_seconds.toFixed(1)}s</div>
            <div class="stat-label">Processing Time</div>
        </div>
    `;

    // Reports
    reportsContainer.innerHTML = result.reports.map(report => `
        <div class="report-card">
            <div class="report-title">${report.filename}</div>
            <div class="report-meta">
                <span>${report.page_count} pages</span>
                <span>${report.file_size_mb} MB</span>
            </div>
            <button class="btn-download" onclick="downloadReport('${report.filename}')">
                Download PDF
            </button>
        </div>
    `).join('');
}

function showError(error) {
    progressSection.style.display = 'none';
    alert(`Processing failed: ${error}`);
}

function downloadReport(filename) {
    window.location.href = `/api/download/${filename}`;
}

// Jobs History
async function loadJobs() {
    try {
        const response = await fetch('/api/jobs');
        const data = await response.json();

        if (data.jobs.length === 0) {
            jobsContainer.innerHTML = '<p style="text-align: center; color: var(--text-muted);">No jobs yet</p>';
            return;
        }

        jobsContainer.innerHTML = data.jobs.map(job => `
            <div class="job-item ${job.status}">
                <div class="job-header">
                    <span class="job-id">${job.job_id.substring(0, 8)}...</span>
                    <span class="job-status ${job.status}">${job.status.toUpperCase()}</span>
                </div>
                <div class="job-info">
                    Created: ${new Date(job.created_at).toLocaleString()}
                    ${job.result ? `| Reports: ${job.result.unique_reports}` : ''}
                    ${job.progress < 100 ? `| Progress: ${job.progress}%` : ''}
                </div>
                ${job.result ? `
                    <div class="job-actions">
                        <button class="btn-view-details" onclick='viewJobDetails(${JSON.stringify(job).replace(/'/g, "&apos;")})'>
                            View Details
                        </button>
                    </div>
                ` : ''}
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading jobs:', error);
    }
}

function viewJobDetails(job) {
    if (job.result) {
        showResults(job.result);
    }
}

// Config Preset Functions
async function loadAvailableConfigs() {
    try {
        const response = await fetch('/api/configs/list');
        const data = await response.json();

        // Update existing options based on availability
        data.configs.forEach(config => {
            const option = configPresetSelect.querySelector(`option[value="${config.name}"]`);
            if (option) {
                option.disabled = !config.available;
                if (!config.available) {
                    option.textContent = config.label + ' (Not Available)';
                } else {
                    option.textContent = config.label;
                }
            }
        });

        // Update description for the default selected option
        updatePresetDescription();

    } catch (error) {
        console.error('Error loading configs:', error);
    }
}

function updatePresetDescription() {
    const selectedValue = configPresetSelect.value;

    const descriptions = {
        'current': 'Current default configuration from config.py',
        'optimized': 'Auto-optimized parameters from sample analysis (run tools/optimize_parameters.py)',
        'tuned': 'Manually tuned parameters from interactive tool (run tools/interactive_tuner.py)'
    };

    presetDescription.textContent = descriptions[selectedValue] || '';

    // If the user selects 'optimized' from the dropdown, apply the fine-tuned values immediately
    if (selectedValue === 'optimized') {
        // Ensure the config panel is visible so changes are visible to the user
        if (configContent.style.display === 'none' || configContent.style.display === '') {
            toggleConfig();
        }

        const vElem = document.getElementById('varianceThreshold');
        const eElem = document.getElementById('edgeThreshold');
        const wElem = document.getElementById('whitePixelRatio');

        if (vElem) vElem.value = 238.83;
        if (eElem) eElem.value = 12386;
        if (wElem) wElem.value = 0.992;

        console.log('Applied optimized preset (selection-time override)');
        // enable the apply button when optimized is selected
        if (applyOptimizedBtn) applyOptimizedBtn.disabled = false;
    } else {
        if (applyOptimizedBtn) applyOptimizedBtn.disabled = true;
    }
}

// Force-apply optimized values when the user clicks the Apply button
function applyOptimizedPreset() {
    try {
        console.log('applyOptimizedPreset() called');

        if (configContent.style.display === 'none' || configContent.style.display === '') toggleConfig();

        const vElem = document.getElementById('varianceThreshold');
        const eElem = document.getElementById('edgeThreshold');
        const wElem = document.getElementById('whitePixelRatio');

        // Use valueAsNumber for numeric inputs where possible, and fall back to .value
        if (vElem) {
            if (typeof vElem.valueAsNumber !== 'undefined' && !isNaN(vElem.valueAsNumber)) {
                vElem.value = 238.83;
            } else {
                vElem.value = '238.83';
            }
            vElem.dispatchEvent(new Event('input'));
            vElem.dispatchEvent(new Event('change'));
        }

        if (eElem) {
            eElem.value = '12386';
            eElem.dispatchEvent(new Event('input'));
            eElem.dispatchEvent(new Event('change'));
        }

        if (wElem) {
            wElem.value = '0.992';
            wElem.dispatchEvent(new Event('input'));
            wElem.dispatchEvent(new Event('change'));
        }

        try {
            presetMetadata.querySelector('small').textContent = 'Optimized preset applied (manual)';
            presetMetadata.style.display = 'block';
        } catch (e) {
            console.warn('presetMetadata element not available to show feedback');
        }

        // brief feedback on the button
        if (applyOptimizedBtn) {
            const old = applyOptimizedBtn.textContent;
            applyOptimizedBtn.textContent = '✓ Applied';
            setTimeout(() => applyOptimizedBtn.textContent = old, 1200);
        }

        console.log('Optimized values applied via Apply button');
    } catch (err) {
        console.error('Failed to apply optimized preset:', err);
    }
}

async function loadSelectedPreset() {
    const selectedConfig = configPresetSelect.value;

    try {
        loadPresetBtn.disabled = true;
        loadPresetBtn.textContent = 'Loading...';

        console.log(`Loading config preset: ${selectedConfig}`);
        // If user selected the optimized preset, apply the fine-tuned values client-side
        if (selectedConfig === 'optimized') {
            // Ensure the config panel is visible so changes are visible to the user
            if (configContent.style.display === 'none' || configContent.style.display === '') {
                toggleConfig();
            }

            const vElem = document.getElementById('varianceThreshold');
            const eElem = document.getElementById('edgeThreshold');
            const wElem = document.getElementById('whitePixelRatio');

            if (vElem) vElem.value = 238.83;
            if (eElem) eElem.value = 12386;
            if (wElem) wElem.value = 0.992;

            // Show simple metadata / feedback
            try {
                presetMetadata.querySelector('small').textContent = 'Optimized preset applied (fine-tuned values)';
                presetMetadata.style.display = 'block';
            } catch (e) {
                console.warn('Could not show preset metadata:', e);
            }

            loadPresetBtn.textContent = '✓ Loaded!';
            setTimeout(() => {
                loadPresetBtn.textContent = 'Load Selected Preset';
                loadPresetBtn.disabled = false;
            }, 1000);

            console.log('Applied optimized preset client-side');
            return;
        }

        // Default behavior: fetch preset from server
        const response = await fetch(`/api/configs/${selectedConfig}`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load config');
        }

        const data = await response.json();
        console.log('Loaded config data:', data);

        // Expand config section FIRST so user can see the changes
        if (configContent.style.display === 'none' || configContent.style.display === '') {
            toggleConfig();
        }

        // Apply blank detection parameters
        if (data.parameters && data.parameters.blank_detection) {
            const params = data.parameters.blank_detection;
            console.log('Applying blank detection params:', params);

            document.getElementById('varianceThreshold').value = params.variance_threshold || 100;
            document.getElementById('edgeThreshold').value = params.edge_threshold || 50;
            document.getElementById('whitePixelRatio').value = params.white_pixel_ratio || 0.95;
            document.getElementById('useEdgeDetection').checked = params.use_edge_detection !== false;
        }

        // Apply duplicate detection parameters
        if (data.parameters && data.parameters.duplicate_detection) {
            const params = data.parameters.duplicate_detection;
            console.log('Applying duplicate detection params:', params);
            document.getElementById('enableDuplicateDetection').checked = params.enabled !== false;
        }

        // Show metadata if available
        if (data.metadata) {
            let metadataText = '';

            if (data.metadata.overall_confidence) {
                const confidence = (data.metadata.overall_confidence * 100).toFixed(1);
                metadataText += `Overall Confidence: ${confidence}% | `;
            }

            if (data.metadata.sample_count) {
                metadataText += `Samples: ${data.metadata.sample_count.blank} blank, ${data.metadata.sample_count.non_blank} non-blank | `;
            }

            if (data.metadata.samples_used) {
                metadataText += `Samples Used: ${data.metadata.samples_used} | `;
            }

            if (data.metadata.performance) {
                const perf = data.metadata.performance;
                metadataText += `Accuracy: ${(perf.accuracy * 100).toFixed(1)}%, F1: ${perf.f1_score.toFixed(3)}`;
            }

            if (metadataText) {
                presetMetadata.querySelector('small').textContent = metadataText;
                presetMetadata.style.display = 'block';
                console.log('Showing metadata:', metadataText);
            } else {
                presetMetadata.style.display = 'none';
            }
        } else {
            presetMetadata.style.display = 'none';
        }

        // Show success feedback
        loadPresetBtn.textContent = '✓ Loaded!';
        console.log('Config loaded successfully');
        setTimeout(() => {
            loadPresetBtn.textContent = 'Load Selected Preset';
            loadPresetBtn.disabled = false;
        }, 2000);

    } catch (error) {
        console.error('Error loading preset:', error);
        alert(`Failed to load preset: ${error.message}`);
        loadPresetBtn.textContent = 'Load Selected Preset';
        loadPresetBtn.disabled = false;
    }
}

// Page Selection Functions
function showPageSelection(result) {
    console.log('📄 showPageSelection called with result:', result);
    currentPages = result.pages || [];
    console.log('Total pages:', currentPages.length);

    pageSelectionSection.style.display = 'block';
    resultsSection.style.display = 'none';
    pageSelectionSection.scrollIntoView({ behavior: 'smooth' });

    // Render page grid
    pagesGrid.innerHTML = currentPages.map(page => `
        <div class="page-card ${page.is_duplicate ? 'duplicate' : ''} ${!page.is_duplicate ? 'selected' : ''}"
             data-page-index="${page.page_index}">
            <div class="page-card-header">
                <div class="page-card-title">Page ${page.page_number}</div>
                <input type="checkbox" class="page-checkbox"
                       data-page-index="${page.page_index}"
                       ${!page.is_duplicate ? 'checked' : ''}>
            </div>
            <img src="${page.preview_url}" alt="Page ${page.page_number}" class="page-card-preview" loading="lazy">
            <div>
                ${page.is_duplicate
                    ? `<span class="page-card-badge badge-duplicate">Duplicate of Page ${page.duplicate_of + 1}</span>`
                    : `<span class="page-card-badge badge-unique">Unique</span>`
                }
            </div>
        </div>
    `).join('');

    // Add click handlers for checkboxes and cards
    document.querySelectorAll('.page-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', updateSelectionCount);
    });

    document.querySelectorAll('.page-card').forEach(card => {
        card.addEventListener('click', (e) => {
            if (e.target.type !== 'checkbox') {
                const checkbox = card.querySelector('.page-checkbox');
                checkbox.checked = !checkbox.checked;
                checkbox.dispatchEvent(new Event('change'));
            }
        });
    });

    updateSelectionCount();

    // Re-attach all button event listeners to ensure they work
    console.log('🔄 Re-attaching page selection button event listeners');

    // Re-attach Generate PDF button
    const newGeneratePdfBtn = document.getElementById('generatePdfBtn');
    if (newGeneratePdfBtn) {
        const oldBtn = newGeneratePdfBtn;
        const newBtn = oldBtn.cloneNode(true);
        oldBtn.parentNode.replaceChild(newBtn, oldBtn);
        newBtn.addEventListener('click', generatePdfWithSelection);
        console.log('✅ Event listener re-attached to generatePdfBtn');
    }

    // Re-attach Select All button
    const newSelectAllBtn = document.getElementById('selectAllBtn');
    if (newSelectAllBtn) {
        const oldBtn = newSelectAllBtn;
        const newBtn = oldBtn.cloneNode(true);
        oldBtn.parentNode.replaceChild(newBtn, oldBtn);
        newBtn.addEventListener('click', selectAllPages);
        console.log('✅ Event listener re-attached to selectAllBtn');
    }

    // Re-attach Deselect All button
    const newDeselectAllBtn = document.getElementById('deselectAllBtn');
    if (newDeselectAllBtn) {
        const oldBtn = newDeselectAllBtn;
        const newBtn = oldBtn.cloneNode(true);
        oldBtn.parentNode.replaceChild(newBtn, oldBtn);
        newBtn.addEventListener('click', deselectAllPages);
        console.log('✅ Event listener re-attached to deselectAllBtn');
    }

    // Re-attach Select Uniques button
    const newSelectUniquesBtn = document.getElementById('selectUniquesBtn');
    if (newSelectUniquesBtn) {
        const oldBtn = newSelectUniquesBtn;
        const newBtn = oldBtn.cloneNode(true);
        oldBtn.parentNode.replaceChild(newBtn, oldBtn);
        newBtn.addEventListener('click', selectOnlyUniques);
        console.log('✅ Event listener re-attached to selectUniquesBtn');
    }
}

function updateSelectionCount() {
    const checkboxes = document.querySelectorAll('.page-checkbox');
    const checked = Array.from(checkboxes).filter(cb => cb.checked);

    selectionCount.textContent = `${checked.length} page${checked.length !== 1 ? 's' : ''} selected`;

    // Get fresh reference to the button in case it was replaced
    const btn = document.getElementById('generatePdfBtn');
    if (btn) {
        btn.disabled = checked.length === 0;
    }

    // Update card styling
    checkboxes.forEach(checkbox => {
        const card = checkbox.closest('.page-card');
        if (checkbox.checked) {
            card.classList.add('selected');
        } else {
            card.classList.remove('selected');
        }
    });
}

function selectAllPages() {
    document.querySelectorAll('.page-checkbox').forEach(cb => {
        cb.checked = true;
    });
    updateSelectionCount();
}

function deselectAllPages() {
    document.querySelectorAll('.page-checkbox').forEach(cb => {
        cb.checked = false;
    });
    updateSelectionCount();
}

function selectOnlyUniques() {
    document.querySelectorAll('.page-checkbox').forEach(cb => {
        const pageIndex = parseInt(cb.dataset.pageIndex);
        const page = currentPages.find(p => p.page_index === pageIndex);
        cb.checked = page && !page.is_duplicate;
    });
    updateSelectionCount();
}

async function generatePdfWithSelection(event) {
    console.log('🔥 generatePdfWithSelection CALLED!');
    console.log('Event:', event);

    // Get fresh reference to the button
    const btn = document.getElementById('generatePdfBtn');
    console.log('Button element:', btn);
    console.log('Button disabled?', btn?.disabled);

    const checkboxes = document.querySelectorAll('.page-checkbox:checked');
    const selectedIndices = Array.from(checkboxes).map(cb => parseInt(cb.dataset.pageIndex));

    console.log('Generate PDF clicked - Selected indices:', selectedIndices);
    console.log('Current job ID:', currentJobId);

    if (selectedIndices.length === 0) {
        alert('Please select at least one page');
        return;
    }

    if (!currentJobId) {
        alert('Job ID not found. Please re-process the PDF.');
        console.error('currentJobId is null or undefined');
        return;
    }

    try {
        if (btn) {
            btn.disabled = true;
            btn.textContent = 'Generating PDF...';
        }

        console.log('Sending request to /api/generate-pdf with job_id:', currentJobId);

        const requestBody = {
            job_id: currentJobId,
            selected_page_indices: selectedIndices
        };
        console.log('Request body:', JSON.stringify(requestBody, null, 2));

        const response = await fetch('/api/generate-pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        console.log('Response status:', response.status);
        console.log('Response headers:', response.headers);

        if (!response.ok) {
            const error = await response.json();
            console.error('API error:', error);
            throw new Error(error.detail || 'Failed to generate PDF');
        }

        const result = await response.json();
        console.log('PDF generated successfully:', result);

        // Show success and provide download
        pageSelectionSection.style.display = 'none';
        resultsSection.style.display = 'block';
        resultsSection.scrollIntoView({ behavior: 'smooth' });

        resultsSummary.innerHTML = `
            <div class="stat-card">
                <div class="stat-value">${selectedIndices.length}</div>
                <div class="stat-label">Pages Selected</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${result.page_count}</div>
                <div class="stat-label">Pages in PDF</div>
            </div>
        `;

        reportsContainer.innerHTML = `
            <div class="report-card">
                <div class="report-title">${result.filename}</div>
                <div class="report-meta">
                    <span>${result.page_count} pages</span>
                </div>
                <a href="${result.download_url}" class="btn-primary" download>
                    Download PDF
                </a>
            </div>
        `;

        console.log('Results displayed, PDF ready for download');

    } catch (error) {
        console.error('Error generating PDF:', error);
        console.error('Error stack:', error.stack);
        alert(`Failed to generate PDF: ${error.message}`);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = 'Generate PDF with Selected Pages';
        }
    }
}
