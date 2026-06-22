document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('uploadForm');
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('videoFile');
    const filePreview = document.getElementById('filePreview');
    const fileName = document.getElementById('fileName');
    const removeBtn = document.getElementById('removeFile');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = document.querySelector('.btn-text');
    const loader = document.querySelector('.loader');
    const consoleEl = document.getElementById('console');
    const consoleOutput = document.getElementById('consoleOutput');

    let selectedFile = null;

    // --- Drag and Drop Logic ---
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });

    dropZone.addEventListener('drop', (e) => {
        let dt = e.dataTransfer;
        let files = dt.files;
        handleFiles(files);
    });

    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });

    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            if (file.type.startsWith('video/')) {
                selectedFile = file;
                showPreview(file.name);
            } else {
                alert("Please select a valid video file.");
            }
        }
    }

    function showPreview(name) {
        fileName.textContent = name;
        dropZone.classList.add('hidden');
        filePreview.classList.remove('hidden');
    }

    removeBtn.addEventListener('click', () => {
        selectedFile = null;
        fileInput.value = '';
        dropZone.classList.remove('hidden');
        filePreview.classList.add('hidden');
    });

    // --- Logging ---
    function log(message, type = 'info') {
        consoleEl.classList.remove('hidden');
        const now = new Date();
        const time = now.toLocaleTimeString([], { hour12: false });
        
        const div = document.createElement('div');
        div.className = 'log-entry';
        div.innerHTML = `<span class="log-time">[${time}]</span> <span class="log-${type}">${message}</span>`;
        
        consoleOutput.appendChild(div);
        consoleOutput.scrollTop = consoleOutput.scrollHeight;
    }

    // --- Form Submission ---
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (!selectedFile) {
            alert("Please select a video file first!");
            return;
        }

        // Get Form Data
        const title = document.getElementById('title').value;
        const description = document.getElementById('description').value;
        const caption = document.getElementById('caption').value;
        const ngrokUrl = document.getElementById('ngrokUrl').value;
        
        // Get Selected Platforms
        const platformCheckboxes = document.querySelectorAll('input[name="platforms"]:checked');
        const platforms = Array.from(platformCheckboxes).map(cb => cb.value);

        if (platforms.length === 0) {
            alert("Please select at least one platform to publish to.");
            return;
        }

        // UI Loading State
        submitBtn.disabled = true;
        btnText.classList.add('hidden');
        loader.classList.remove('hidden');
        consoleOutput.innerHTML = ''; // Clear logs

        log(`Starting workflow for: ${selectedFile.name}`, 'info');

        try {
            // STEP 1: Upload and Process Video
            log("Uploading video to server for processing...", 'info');
            const formData = new FormData();
            formData.append('file', selectedFile);

            const uploadRes = await fetch('/process-video', {
                method: 'POST',
                body: formData
            });
            const uploadData = await uploadRes.json();

            if (uploadData.status !== 'success') {
                throw new Error(uploadData.message || "Failed to process video");
            }

            const outputFileName = uploadData.output_file;
            log(`Video edited successfully! Logo added. Saved as: ${outputFileName}`, 'success');

            // STEP 2: Publish to platforms
            log(`Sending payload to Zernio API for platforms: ${platforms.join(', ')}...`, 'info');
            
            const publishPayload = {
                video_filename: outputFileName,
                title: title,
                description: description,
                caption: caption,
                public_base_url: ngrokUrl,
                platforms: platforms
            };

            const publishRes = await fetch('/publish-all', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(publishPayload)
            });

            const publishData = await publishRes.json();

            if (publishData.status !== 'success') {
                throw new Error(publishData.message || "Failed to publish video");
            }

            log(`Zernio fetched video from: ${publishData.public_video_url_used}`, 'info');

            // Log individual platform results
            Object.entries(publishData.results).forEach(([platform, result]) => {
                if (result.status === 'success') {
                    log(`[${platform.toUpperCase()}] Success: ${result.result}`, 'success');
                } else {
                    log(`[${platform.toUpperCase()}] Error: ${result.message}`, 'error');
                }
            });

            log("Workflow completed! 🎉", 'success');

        } catch (error) {
            log(error.message, 'error');
        } finally {
            // Reset UI
            submitBtn.disabled = false;
            btnText.classList.remove('hidden');
            loader.classList.add('hidden');
        }
    });
});
