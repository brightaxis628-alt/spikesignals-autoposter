document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('unifiedForm');
    
    // Mode Tab Elements
    const modeTabs = document.querySelectorAll('.mode-tab-btn');
    const fetchSection = document.getElementById('fetchSection');
    const uploadSection = document.getElementById('uploadSection');
    const aiSection = document.getElementById('aiSection');
    const detailsSection = document.getElementById('detailsSection');
    
    // Platform Source Filter Pills (YouTube, Instagram, TikTok)
    const sourcePills = document.querySelectorAll('.source-pill');
    let selectedPlatformSource = 'youtube';

    sourcePills.forEach(pill => {
        pill.addEventListener('click', () => {
            sourcePills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            selectedPlatformSource = pill.getAttribute('data-platform');
            
            // If user already typed something or wants to see trending for this app, trigger quick search
            performSearch(false);
        });
    });

    // Search & Fetch Elements
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const searchBtnText = document.getElementById('searchBtnText');
    const searchLoader = document.getElementById('searchLoader');
    const videoResultsContainer = document.getElementById('videoResultsContainer');
    const videoGrid = document.getElementById('videoGrid');
    const resultsCount = document.getElementById('resultsCount');
    const videoUrlInput = document.getElementById('videoUrl');

    // Selected Video Banner
    const selectedVideoBanner = document.getElementById('selectedVideoBanner');
    const selectedThumb = document.getElementById('selectedThumb');
    const selectedTitle = document.getElementById('selectedTitle');
    const selectedAuthor = document.getElementById('selectedAuthor');

    // Details / Copywriting Inputs
    const titleInput = document.getElementById('title');
    const descInput = document.getElementById('description');
    const captionInput = document.getElementById('caption');
    const regenerateCopyBtn = document.getElementById('regenerateCopyBtn');
    const autoMakeAlert = document.getElementById('autoMakeAlert');

    // Watermark & Custom Logo Elements
    const activeLogoPreview = document.getElementById('activeLogoPreview');
    const customLogoInput = document.getElementById('customLogoInput');
    const uploadLogoBtn = document.getElementById('uploadLogoBtn');
    const resetLogoBtn = document.getElementById('resetLogoBtn');
    const logoStatusText = document.getElementById('logoStatusText');
    const logoPositionInput = document.getElementById('logoPositionInput');
    const customLogoPathInput = document.getElementById('customLogoPathInput');
    const positionBtns = document.querySelectorAll('.position-btn');

    // AI & Other Inputs
    const searchHeadingInput = document.getElementById('searchHeading');
    const publicBaseUrlInput = document.getElementById('publicBaseUrl');

    // Drag and Drop Elements
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('videoFile');
    const filePreview = document.getElementById('filePreview');
    const fileName = document.getElementById('fileName');
    const removeBtn = document.getElementById('removeFile');

    // Submit & Console
    const submitBtn = document.getElementById('submitBtn');
    const btnText = document.querySelector('.btn-text');
    const loader = document.querySelector('.loader');
    const consoleEl = document.getElementById('console');
    const consoleOutput = document.getElementById('consoleOutput');

    let currentMode = 'fetch'; // 'fetch' | 'upload' | 'ai'
    let selectedFile = null;
    let selectedVideoData = null;
    let lastSearchQuery = null;
    let lastSearchPlatform = null;
    let currentSearchOffset = 0;

    // --- Mode Tab Switching ---
    modeTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            modeTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentMode = tab.getAttribute('data-mode');

            if (fetchSection) fetchSection.classList.add('hidden');
            if (uploadSection) uploadSection.classList.add('hidden');
            if (aiSection) aiSection.classList.add('hidden');

            if (currentMode === 'fetch') {
                if (fetchSection) fetchSection.classList.remove('hidden');
                if (detailsSection) detailsSection.classList.remove('hidden');
                btnText.innerHTML = `Brand Logo & Auto-Publish <i class="fa-solid fa-rocket"></i>`;

                // Preserve and restore selected video state
                if (selectedVideoData && selectedVideoBanner) {
                    selectedVideoBanner.classList.remove('hidden');
                    if (selectedTitle) selectedTitle.textContent = selectedVideoData.title;
                    if (selectedAuthor) selectedAuthor.textContent = `${selectedVideoData.uploader || 'Trending Creator'} • ${selectedVideoData.platform ? selectedVideoData.platform.toUpperCase() : 'VIDEO'}`;
                    if (selectedThumb) selectedThumb.src = selectedVideoData.thumbnail || '';
                    if (videoUrlInput) videoUrlInput.value = selectedVideoData.url;
                }
            } else if (currentMode === 'upload') {
                if (uploadSection) uploadSection.classList.remove('hidden');
                if (detailsSection) detailsSection.classList.remove('hidden');
                btnText.innerHTML = `Process & Publish <i class="fa-solid fa-rocket"></i>`;

                // Clear or guide for manual upload
                if (!selectedFile && autoMakeAlert) {
                    autoMakeAlert.classList.remove('hidden');
                    autoMakeAlert.innerHTML = `<i class="fa-solid fa-cloud-arrow-up"></i> Upload your video above, enter a title, and click "Auto-Make Copy"!`;
                }
            } else if (currentMode === 'ai') {
                if (aiSection) aiSection.classList.remove('hidden');
                if (detailsSection) detailsSection.classList.add('hidden');
                btnText.innerHTML = `Generate & Publish <i class="fa-solid fa-wand-magic-sparkles"></i>`;
            }
        });
    });

    // --- 1. SEARCH TRENDING VIDEOS BY WORDS & PLATFORM ---
    searchBtn.addEventListener('click', (e) => {
        if (e) e.preventDefault();
        performSearch(true);
    });
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            e.stopPropagation();
            performSearch(true);
        }
    });

    async function performSearch(fromUserClick = true) {
        const query = searchInput.value.trim();

        // Check if user entered a direct URL in search input
        if (query.startsWith('http://') || query.startsWith('https://')) {
            videoUrlInput.value = query;
            handleDirectUrl(query);
            return;
        }

        const normalizedQuery = query.toLowerCase();
        const normalizedPlatform = selectedPlatformSource.toLowerCase();

        if (fromUserClick && normalizedQuery === lastSearchQuery && normalizedPlatform === lastSearchPlatform) {
            // User clicked Fetch Trending again on the SAME topic -> Rotate to NEXT 6 fresh videos!
            currentSearchOffset += 6;
        } else {
            lastSearchQuery = normalizedQuery;
            lastSearchPlatform = normalizedPlatform;
            currentSearchOffset = 0;
        }

        searchBtn.disabled = true;
        searchBtnText.classList.add('hidden');
        searchLoader.classList.remove('hidden');
        videoResultsContainer.classList.remove('hidden');
        
        const platformName = selectedPlatformSource.toUpperCase();
        videoGrid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 2.5rem 1rem; color: var(--text-muted);">
                <i class="fa-solid fa-spinner fa-spin" style="font-size: 1.5rem; margin-bottom: 0.8rem; color: var(--accent);"></i>
                <p>Fetching top trending videos from <strong>${platformName}</strong>${query ? ` for "${query}"` : ''}...</p>
            </div>
        `;

        try {
            const endpoint = `/search-trending?query=${encodeURIComponent(query)}&platform=${encodeURIComponent(selectedPlatformSource)}&max_results=6&offset=${currentSearchOffset}`;
            const res = await fetch(endpoint);
            const data = await res.json();

            if (data.status !== 'success' || !data.videos || data.videos.length === 0) {
                resultsCount.textContent = `Found 0 videos on ${platformName}`;
                videoGrid.innerHTML = `
                    <div style="grid-column: 1/-1; text-align: center; padding: 2.5rem 1rem; color: var(--text-muted);">
                        <i class="fa-regular fa-folder-open" style="font-size: 1.8rem; margin-bottom: 0.5rem; display: block;"></i>
                        No trending videos found. Try different words or paste a direct video link!
                    </div>
                `;
                return;
            }

            const batchNum = Math.floor(currentSearchOffset / 6) + 1;
            resultsCount.innerHTML = `Found ${data.videos.length} videos on ${platformName} &bull; <span style="color:#a78bfa; font-weight: 500;">Batch #${batchNum} (click 'Fetch Trending' for next 6)</span>`;
            renderVideoCards(data.videos);

        } catch (err) {
            videoGrid.innerHTML = `<div style="grid-column: 1/-1; color: #ef4444; padding: 1rem;">Failed to fetch videos: ${err.message}</div>`;
        } finally {
            searchBtn.disabled = false;
            searchBtnText.classList.remove('hidden');
            searchLoader.classList.add('hidden');
        }
    }

    function renderVideoCards(videos) {
        videoGrid.innerHTML = '';
        videos.forEach((video) => {
            const card = document.createElement('div');
            card.className = 'video-card';

            const durationStr = formatDuration(video.duration);
            const thumbUrl = video.thumbnail || 'https://via.placeholder.com/320x180?text=Trending+Video';

            // Determine badge style
            let badgeClass = 'badge-yt';
            let badgeIcon = 'fa-brands fa-youtube';
            let badgeLabel = 'YouTube';

            const plat = (video.platform || '').toLowerCase();
            if (plat === 'instagram') {
                badgeClass = 'badge-ig';
                badgeIcon = 'fa-brands fa-instagram';
                badgeLabel = 'Reels';
            } else if (plat === 'tiktok') {
                badgeClass = 'badge-tk';
                badgeIcon = 'fa-brands fa-tiktok';
                badgeLabel = 'TikTok';
            } else {
                if (video.content_type === 'Short' || (video.duration && video.duration <= 95)) {
                    badgeClass = 'badge-yt';
                    badgeIcon = 'fa-brands fa-youtube';
                    badgeLabel = 'Shorts';
                } else {
                    badgeClass = 'badge-yt';
                    badgeIcon = 'fa-brands fa-youtube';
                    badgeLabel = 'YouTube';
                }
            }

            card.innerHTML = `
                <div class="video-card-thumb-wrapper">
                    <img src="${thumbUrl}" alt="Thumbnail" class="video-card-thumb" referrerpolicy="no-referrer" onerror="this.src='https://via.placeholder.com/320x180?text=Video'">
                    <span class="video-card-platform-badge ${badgeClass}"><i class="${badgeIcon}"></i> ${badgeLabel}</span>
                    ${durationStr ? `<span class="video-card-duration">${durationStr}</span>` : ''}
                </div>
                <div class="video-card-body">
                    <div>
                        <div class="video-card-title" title="${escapeHtml(video.title)}">${escapeHtml(video.title)}</div>
                        <div class="video-card-uploader"><i class="fa-solid fa-circle-user"></i> ${escapeHtml(video.uploader || 'Creator')}</div>
                    </div>
                    <div class="video-card-actions">
                        <button type="button" class="select-card-btn">
                            <i class="fa-solid fa-check"></i> Select Video
                        </button>
                        <a href="${video.url}" target="_blank" rel="noopener noreferrer" class="watch-card-btn" title="Open and watch video in new tab" onclick="event.stopPropagation();">
                            <i class="fa-solid fa-arrow-up-right-from-square"></i> Watch
                        </a>
                    </div>
                </div>
            `;

            card.addEventListener('click', () => {
                document.querySelectorAll('.video-card').forEach(c => {
                    c.classList.remove('selected');
                    const btn = c.querySelector('.select-card-btn');
                    if (btn) btn.innerHTML = `<i class="fa-solid fa-check"></i> Select Video`;
                });
                card.classList.add('selected');
                const btn = card.querySelector('.select-card-btn');
                if (btn) btn.innerHTML = `<i class="fa-solid fa-circle-check"></i> Selected`;
                selectVideo(video);
            });

            videoGrid.appendChild(card);
        });
    }

    function formatDuration(sec) {
        if (!sec || isNaN(sec)) return '';
        var h = Math.floor(sec / 3600);
        var m = Math.floor((sec % 3600) / 60);
        var s = Math.floor(sec % 60);
        var sStr = s < 10 ? '0' + s : '' + s;
        if (h > 0) {
            var mStr = m < 10 ? '0' + m : '' + m;
            return h + ':' + mStr + ':' + sStr;
        }
        return m + ':' + sStr;
    }

    function escapeHtml(text) {
        return text ? text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;") : '';
    }

    // --- 2. SELECT VIDEO & AUTOMAKE CAPTIONS & LINES ---
    async function selectVideo(video) {
        selectedVideoData = video;
        videoUrlInput.value = video.url;

        // Show Preview Banner
        selectedThumb.src = video.thumbnail || '';
        selectedTitle.textContent = video.title || 'Selected Video';
        selectedAuthor.textContent = `${video.uploader || 'Trending Creator'} • ${video.platform ? video.platform.toUpperCase() : 'VIDEO'}`;
        selectedVideoBanner.classList.remove('hidden');

        // Update Watch Link Button
        const selectedVideoLink = document.getElementById('selectedVideoLink');
        if (selectedVideoLink) {
            selectedVideoLink.href = video.url;
            selectedVideoLink.style.display = 'inline-flex';
        }

        // Automake captions, title and hashtags strictly based on video context
        await autoMakeCopy(video.title, searchInput.value.trim(), video.description || "", video.uploader || "");
    }

    // Direct URL input listener
    videoUrlInput.addEventListener('change', () => {
        const val = videoUrlInput.value.trim();
        if (val) {
            handleDirectUrl(val);
        }
    });

    async function handleDirectUrl(url) {
        selectedThumb.src = 'https://via.placeholder.com/120x80?text=Direct+Video';
        selectedTitle.textContent = "Direct Video Link";
        selectedAuthor.textContent = url;
        selectedVideoBanner.classList.remove('hidden');

        await autoMakeCopy("Trending Viral Video", searchInput.value.trim());
    }

    // --- 3. AUTO-CRAFT CAPTIONS, TITLE & LINES ---
    regenerateCopyBtn.addEventListener('click', () => {
        const titleVal = titleInput.value.trim() || (selectedVideoData ? selectedVideoData.title : searchInput.value.trim());
        const descVal = selectedVideoData ? (selectedVideoData.description || "") : "";
        const uploaderVal = selectedVideoData ? (selectedVideoData.uploader || "") : "";
        autoMakeCopy(titleVal, searchInput.value.trim(), descVal, uploaderVal);
    });

    async function autoMakeCopy(titleText, topicText = "", descText = "", uploaderText = "", videoFilename = "") {
        if (!titleText && !videoFilename) return;

        autoMakeAlert.classList.remove('hidden');
        autoMakeAlert.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Auto-crafting content strictly based on video context...`;

        try {
            const res = await fetch('/auto-make-copy', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    title: titleText || "", 
                    topic: topicText,
                    description: descText,
                    uploader: uploaderText,
                    video_filename: videoFilename || (selectedFile ? selectedFile.name : "")
                })
            });

            const json = await res.json();
            if (json.status === 'success' && json.data) {
                titleInput.value = json.data.title || titleText;
                descInput.value = json.data.description || '';
                captionInput.value = json.data.caption || '';
                autoMakeAlert.innerHTML = `<i class="fa-solid fa-sparkles"></i> Lines, captions & hashtags crafted based on video!`;
            }
        } catch (e) {
            console.error(e);
            titleInput.value = titleText;
            descInput.value = `${titleText}\n\n#trending #shorts #viral`;
            captionInput.value = `Wait till the end! 🔥\n\n${titleText}\n\n#reels #viral #explore`;
            autoMakeAlert.classList.add('hidden');
        }
    }

    // --- Drag and Drop File Upload ---
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
        }, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });

    dropZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        handleFiles(files);
    });

    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });

    function isGenericExportName(name) {
        return /(whats\s*app\s*video|screen\s*recording|untitled|vid_\d+|img_\d+|pxl_\d+|\d{4}[-_]\d{2}[-_]\d{2}|at\s+\d{1,2}[\.:]\d{2}[\.:]\d{2}|video_\d+|mov_\d+)/i.test(name);
    }

    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            if (file.type.startsWith('video/')) {
                selectedFile = file;
                fileName.textContent = file.name;
                dropZone.classList.add('hidden');
                filePreview.classList.remove('hidden');

                const isGeneric = isGenericExportName(file.name);
                const currentTopic = searchInput ? searchInput.value.trim() : 'trading';

                if (isGeneric) {
                    titleInput.value = '';
                    titleInput.placeholder = '🔍 Inspecting video frames with Multimodal AI...';
                    descInput.value = '';
                    descInput.placeholder = 'Analyzing visual scenes and generating hashtags...';
                    captionInput.value = '';
                    captionInput.placeholder = 'Crafting high-converting Instagram caption...';
                    if (autoMakeAlert) {
                        autoMakeAlert.classList.remove('hidden');
                        autoMakeAlert.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles fa-spin"></i> <strong>Multimodal AI</strong> is inspecting video frames to see what is happening...`;
                    }
                } else {
                    let cleanName = file.name.replace(/\.[^/.]+$/, "");
                    cleanName = cleanName.replace(/[\_\-]+(real|\d+s|final|v\d+|\d+p|cut|edit).*$/i, "");
                    cleanName = cleanName.replace(/[_\-]+/g, " ");
                    cleanName = cleanName.replace(/([a-z])([A-Z])/g, '$1 $2').trim();
                    titleInput.value = cleanName;
                    if (autoMakeAlert) {
                        autoMakeAlert.classList.remove('hidden');
                        autoMakeAlert.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles fa-spin"></i> Video loaded: <strong>${escapeHtml(file.name)}</strong>. Inspecting video scenes with Multimodal AI...`;
                    }
                }

                // Analyze video frames directly with backend Multimodal Vision
                const formData = new FormData();
                formData.append('file', file);
                formData.append('topic', currentTopic);

                fetch('/analyze-video-content', {
                    method: 'POST',
                    body: formData
                })
                .then(res => res.json())
                .then(json => {
                    if (json.status === 'success' && json.data) {
                        titleInput.value = json.data.title || '';
                        descInput.value = json.data.description || '';
                        captionInput.value = json.data.caption || '';
                        if (autoMakeAlert) {
                            autoMakeAlert.classList.remove('hidden');
                            autoMakeAlert.innerHTML = `<i class="fa-solid fa-circle-check"></i> <strong>Visual Content Analyzed!</strong> Captions crafted from video scenes.`;
                        }
                    } else {
                        fallbackCopy();
                    }
                })
                .catch(err => {
                    console.warn("Visual inspection fallback:", err);
                    fallbackCopy();
                });

                function fallbackCopy() {
                    let fallbackTitle = titleInput.value.trim();
                    if (!fallbackTitle || isGeneric) {
                        fallbackTitle = (currentTopic && currentTopic !== 'trending') ? `${currentTopic.toUpperCase()} Strategy Breakdown` : "High-Probability Market Setup & Strategy";
                    }
                    autoMakeCopy(fallbackTitle, currentTopic);
                }
            } else {
                alert("Please select a valid MP4 or MOV video file.");
            }
        }
    }

    removeBtn.addEventListener('click', () => {
        selectedFile = null;
        fileInput.value = '';
        dropZone.classList.remove('hidden');
        filePreview.classList.add('hidden');
        titleInput.value = '';
        descInput.value = '';
        captionInput.value = '';
        if (autoMakeAlert) {
            autoMakeAlert.classList.remove('hidden');
            autoMakeAlert.innerHTML = `<i class="fa-solid fa-cloud-arrow-up"></i> Upload your video above, enter a title, and click "Auto-Make Copy"!`;
        }
    });

    // --- Watermark Position Selector ---
    positionBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            positionBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const pos = btn.getAttribute('data-pos');
            if (logoPositionInput) {
                logoPositionInput.value = pos;
            }
        });
    });

    // --- Custom Logo Upload & Reset ---
    if (uploadLogoBtn && customLogoInput) {
        uploadLogoBtn.addEventListener('click', () => {
            customLogoInput.click();
        });

        customLogoInput.addEventListener('change', async function() {
            if (!this.files || this.files.length === 0) return;
            const file = this.files[0];
            
            if (logoStatusText) {
                logoStatusText.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Uploading ${file.name}...`;
            }
            
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const res = await fetch('/upload-logo', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                
                if (data.status === 'success') {
                    if (activeLogoPreview) activeLogoPreview.src = data.preview_url;
                    if (customLogoPathInput) customLogoPathInput.value = data.logo_path;
                    if (resetLogoBtn) resetLogoBtn.classList.remove('hidden');
                    if (logoStatusText) {
                        logoStatusText.innerHTML = `<span style="color: #34d399; font-weight: 600;"><i class="fa-solid fa-circle-check"></i> Custom logo active:</span> ${file.name}`;
                    }
                } else {
                    throw new Error(data.message || 'Failed to upload logo.');
                }
            } catch (err) {
                alert('Logo upload failed: ' + err.message);
                if (logoStatusText) {
                    logoStatusText.innerText = 'Error uploading custom logo. Reverted to default.';
                }
            }
        });
    }

    if (resetLogoBtn) {
        resetLogoBtn.addEventListener('click', () => {
            if (activeLogoPreview) activeLogoPreview.src = '/logos/logo.png';
            if (customLogoPathInput) customLogoPathInput.value = 'logos/logo.png';
            if (customLogoInput) customLogoInput.value = '';
            resetLogoBtn.classList.add('hidden');
            if (logoStatusText) {
                logoStatusText.innerText = 'Using default company logo (PNG with transparency recommended).';
            }
        });
    }

    // --- Logging Helper ---
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

    // --- Form Submission & Publish Handling ---
    async function handlePublish(e) {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }

        const platformCheckboxes = document.querySelectorAll('input[name="platforms"]:checked');
        const platforms = Array.from(platformCheckboxes).map(cb => cb.value);

        if (platforms.length === 0) {
            alert("Please select at least one platform to publish to (Instagram, TikTok, or YouTube).");
            return;
        }

        const publicBaseUrl = publicBaseUrlInput.value.trim();

        if (currentMode === 'fetch') {
            const url = videoUrlInput.value.trim();
            if (!url) {
                alert("Please search and select a video, or paste a video URL first.");
                return;
            }
        } else if (currentMode === 'upload') {
            if (!selectedFile) {
                alert("Please choose a video file to upload.");
                return;
            }
        } else if (currentMode === 'ai') {
            if (!searchHeadingInput.value.trim()) {
                alert("Please enter a trending topic or prompt for AI generation.");
                return;
            }
        }

        // Start Execution UI
        submitBtn.disabled = true;
        btnText.classList.add('hidden');
        loader.classList.remove('hidden');
        consoleOutput.innerHTML = '';

        try {
            const chosenPosition = (logoPositionInput && logoPositionInput.value) ? logoPositionInput.value : 'top-left';
            const chosenLogoPath = (customLogoPathInput && customLogoPathInput.value) ? customLogoPathInput.value : 'logos/logo.png';
            const posDisplay = chosenPosition.replace('-', ' ').toUpperCase();

            // MODE 1: FETCH URL, BRAND LOGO & AUTO-POST
            if (currentMode === 'fetch') {
                const url = videoUrlInput.value.trim();
                const videoTitle = titleInput.value.trim() || (selectedVideoData ? selectedVideoData.title : "Trending Video");
                
                log(`[1/3] Downloading original video stream from: ${url}...`, 'info');

                let stepCount = 1;
                const heartbeat = setInterval(() => {
                    stepCount++;
                    if (stepCount === 2) {
                        log(`[2/3] Adding watermark (${posDisplay}) with ultra-fast FFmpeg...`, 'info');
                    } else if (stepCount === 3) {
                        log(`[3/3] Uploading branded video to CDN and publishing to ${platforms.join(', ')}...`, 'info');
                    } else if (stepCount > 3) {
                        log(`Processing network publish on ${platforms.join(', ')}...`, 'info');
                    }
                }, 7000);

                const payload = {
                    url: url,
                    direct_url: (selectedVideoData && selectedVideoData.direct_video_url && selectedVideoData.url === url) ? selectedVideoData.direct_video_url : null,
                    title: videoTitle,
                    description: descInput.value.trim(),
                    caption: captionInput.value.trim(),
                    public_base_url: publicBaseUrl,
                    platforms: platforms,
                    logo_path: chosenLogoPath,
                    logo_position: chosenPosition
                };

                let res;
                try {
                    res = await fetch('/fetch-and-publish', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                } finally {
                    clearInterval(heartbeat);
                }

                const data = await res.json();
                if (data.status !== 'success') {
                    throw new Error(data.message || "Failed during fetch & post process.");
                }

                log(`[2/3] Watermark branded on video (${posDisplay}): ${data.output_file}`, 'success');
                log(`[3/3] Publishing to platforms: ${platforms.join(', ')}...`, 'info');

                if (data.public_video_url_used) {
                    log(`Public video URL served at: ${data.public_video_url_used}`, 'info');
                }

                Object.entries(data.results).forEach(([platform, resData]) => {
                    if (resData.status === 'success') {
                        log(`[${platform.toUpperCase()}] Published successfully: ${resData.result}`, 'success');
                    } else {
                        log(`[${platform.toUpperCase()}] Error: ${resData.message}`, 'error');
                    }
                });

                log("🎉 Video fetched, branded with logo, captioned, and published successfully!", 'success');
            }

            // MODE 2: MANUAL UPLOAD & PUBLISH
            else if (currentMode === 'upload') {
                log(`[1/3] Uploading local file: ${selectedFile.name}...`, 'info');
                const formData = new FormData();
                formData.append('file', selectedFile);
                formData.append('logo_path', chosenLogoPath);
                formData.append('logo_position', chosenPosition);

                const uploadRes = await fetch('/process-video', {
                    method: 'POST',
                    body: formData
                });
                const uploadData = await uploadRes.json();

                if (uploadData.status !== 'success') {
                    throw new Error(uploadData.message || "Video processing failed.");
                }

                const outputFileName = uploadData.output_file;
                log(`[2/3] Video branded with logo (${posDisplay}). Saved as: ${outputFileName}`, 'success');
                log(`[3/3] Publishing to platforms: ${platforms.join(', ')}...`, 'info');

                const publishPayload = {
                    video_filename: outputFileName,
                    title: titleInput.value.trim() || selectedFile.name,
                    description: descInput.value.trim(),
                    caption: captionInput.value.trim(),
                    public_base_url: publicBaseUrl,
                    platforms: platforms
                };

                const publishRes = await fetch('/publish-all', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(publishPayload)
                });

                const publishData = await publishRes.json();
                if (publishData.status !== 'success') {
                    throw new Error(publishData.message || "Publishing failed.");
                }

                Object.entries(publishData.results).forEach(([platform, resData]) => {
                    if (resData.status === 'success') {
                        log(`[${platform.toUpperCase()}] Published successfully: ${resData.result}`, 'success');
                    } else {
                        log(`[${platform.toUpperCase()}] Error: ${resData.message}`, 'error');
                    }
                });

                log("🎉 Video branded and published successfully!", 'success');
            }

            // MODE 3: AI GENERATOR
            else if (currentMode === 'ai') {
                const heading = searchHeadingInput.value.trim();
                log(`[1/3] Generating tailored AI video prompts for "${heading}"...`, 'info');
                
                const aiPayload = {
                    search_heading: heading,
                    public_base_url: publicBaseUrl,
                    platforms: platforms
                };

                const aiRes = await fetch('/generate-ai-media', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(aiPayload)
                });

                const aiData = await aiRes.json();
                if (aiData.status !== 'success') {
                    throw new Error(aiData.message || "AI generation failed.");
                }

                log(`[2/3] Generated Kling 3.0 videos and stamped top-left logo.`, 'success');
                log(`[3/3] Publishing results:`, 'info');

                Object.entries(aiData.results).forEach(([platform, resData]) => {
                    if (resData.status === 'success') {
                        log(`[${platform.toUpperCase()}] AI Video Published: ${resData.result}`, 'success');
                    } else {
                        log(`[${platform.toUpperCase()}] Error: ${resData.message}`, 'error');
                    }
                });

                log("🎉 AI Video workflow complete!", 'success');
            }

        } catch (err) {
            log(`Error: ${err.message}`, 'error');
        } finally {
            submitBtn.disabled = false;
            btnText.classList.remove('hidden');
            loader.classList.add('hidden');
        }
    }

    submitBtn.addEventListener('click', handlePublish);
    form.addEventListener('submit', (e) => { e.preventDefault(); return false; });
});
