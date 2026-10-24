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

    // --- Mode Tab Switching ---
    modeTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            modeTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentMode = tab.getAttribute('data-mode');

            fetchSection.classList.add('hidden');
            uploadSection.classList.add('hidden');
            aiSection.classList.add('hidden');

            if (currentMode === 'fetch') {
                fetchSection.classList.remove('hidden');
                detailsSection.classList.remove('hidden');
                btnText.innerHTML = `Brand Logo & Auto-Publish <i class="fa-solid fa-rocket"></i>`;
            } else if (currentMode === 'upload') {
                uploadSection.classList.remove('hidden');
                detailsSection.classList.remove('hidden');
                btnText.innerHTML = `Process & Publish <i class="fa-solid fa-rocket"></i>`;
            } else if (currentMode === 'ai') {
                aiSection.classList.remove('hidden');
                detailsSection.classList.add('hidden');
                btnText.innerHTML = `Generate & Publish <i class="fa-solid fa-wand-magic-sparkles"></i>`;
            }
        });
    });

    // --- 1. SEARCH TRENDING VIDEOS BY WORDS & PLATFORM ---
    searchBtn.addEventListener('click', () => performSearch(true));
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            performSearch(true);
        }
    });

    async function performSearch(showAlertOnEmpty = true) {
        const query = searchInput.value.trim();

        // Check if user entered a direct URL in search input
        if (query.startsWith('http://') || query.startsWith('https://')) {
            videoUrlInput.value = query;
            handleDirectUrl(query);
            return;
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
            const endpoint = `/search-trending?query=${encodeURIComponent(query)}&platform=${encodeURIComponent(selectedPlatformSource)}&max_results=6`;
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

            resultsCount.textContent = `Found ${data.videos.length} videos on ${platformName}`;
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
        const m = Math.floor(sec / 60);
        const s = Math.floor(sec % 60);
        return `${m}:${s < 10 ? '0' : ''}${s}`;
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

        // Automake captions, title and hashtags
        await autoMakeCopy(video.title, searchInput.value.trim());
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
        autoMakeCopy(titleVal, searchInput.value.trim());
    });

    async function autoMakeCopy(titleText, topicText = "") {
        if (!titleText) return;

        autoMakeAlert.classList.remove('hidden');
        autoMakeAlert.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Auto-crafting viral lines & captions...`;

        try {
            const res = await fetch('/auto-make-copy', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: titleText, topic: topicText })
            });

            const json = await res.json();
            if (json.status === 'success' && json.data) {
                titleInput.value = json.data.title || titleText;
                descInput.value = json.data.description || '';
                captionInput.value = json.data.caption || '';
                autoMakeAlert.innerHTML = `<i class="fa-solid fa-sparkles"></i> Lines, captions & hashtags automatically crafted!`;
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

    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            if (file.type.startsWith('video/')) {
                selectedFile = file;
                fileName.textContent = file.name;
                dropZone.classList.add('hidden');
                filePreview.classList.remove('hidden');

                const cleanName = file.name.replace(/\.[^/.]+$/, "");
                autoMakeCopy(cleanName);
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
    });

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

    // --- Form Submission Handling ---
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

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
            // MODE 1: FETCH URL, BRAND LOGO & AUTO-POST
            if (currentMode === 'fetch') {
                const url = videoUrlInput.value.trim();
                const videoTitle = titleInput.value.trim() || (selectedVideoData ? selectedVideoData.title : "Trending Video");
                
                log(`[1/3] Downloading original video stream from: ${url}...`, 'info');

                const payload = {
                    url: url,
                    direct_url: (selectedVideoData && selectedVideoData.direct_video_url && selectedVideoData.url === url) ? selectedVideoData.direct_video_url : null,
                    title: videoTitle,
                    description: descInput.value.trim(),
                    caption: captionInput.value.trim(),
                    public_base_url: publicBaseUrl,
                    platforms: platforms
                };

                const res = await fetch('/fetch-and-publish', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const data = await res.json();
                if (data.status !== 'success') {
                    throw new Error(data.message || "Failed during fetch & post process.");
                }

                log(`[2/3] Top-left company logo stamped on video: ${data.output_file}`, 'success');
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

                const uploadRes = await fetch('/process-video', {
                    method: 'POST',
                    body: formData
                });
                const uploadData = await uploadRes.json();

                if (uploadData.status !== 'success') {
                    throw new Error(uploadData.message || "Video processing failed.");
                }

                const outputFileName = uploadData.output_file;
                log(`[2/3] Video branded with top-left logo. Saved as: ${outputFileName}`, 'success');
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
    });
});
