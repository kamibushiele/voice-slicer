/**
 * 音声文字起こし編集GUI - メインアプリケーション
 */

// ===========================================
// グローバル変数
// ===========================================

let wavesurfer = null;
let regions = null;
let currentData = null;
let selectedSegmentIndex = null;
let isModified = false;
let isLoopEnabled = false;
let nextInternalId = 1;  // 内部ID生成用カウンター

// ===========================================
// 初期化
// ===========================================

document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    initKeyboardShortcuts();
    // 起動時にデータを自動読み込み
    loadInitialData();
});

function initEventListeners() {

    // ツールバー
    document.getElementById('btn-play').addEventListener('click', togglePlayPause);
    document.getElementById('btn-loop').addEventListener('click', toggleLoop);
    document.getElementById('btn-zoom-in').addEventListener('click', () => adjustZoom(50));
    document.getElementById('btn-zoom-out').addEventListener('click', () => adjustZoom(-50));
    document.getElementById('zoom-slider').addEventListener('input', (e) => {
        setZoom(parseInt(e.target.value));
    });
    document.getElementById('playback-rate').addEventListener('change', (e) => {
        if (wavesurfer) {
            wavesurfer.setPlaybackRate(parseFloat(e.target.value));
        }
    });

    // 編集パネル
    document.getElementById('btn-delete-segment').addEventListener('click', deleteSelectedSegment);

    // セグメント操作パネル
    document.getElementById('btn-prev-segment').addEventListener('click', selectPreviousSegment);
    document.getElementById('btn-next-segment').addEventListener('click', selectNextSegment);
    document.getElementById('btn-add-segment').addEventListener('click', addNewSegment);

    // ヘッダー
    document.getElementById('btn-save').addEventListener('click', saveJson);
    document.getElementById('btn-regenerate').addEventListener('click', () => regenerateAudio(false));
    document.getElementById('btn-force-regenerate').addEventListener('click', () => regenerateAudio(true));
    document.getElementById('btn-help').addEventListener('click', () => {
        document.getElementById('help-modal').classList.remove('hidden');
    });

    // 編集フィールドの変更を即座に適用
    ['edit-start', 'edit-end'].forEach(id => {
        document.getElementById(id).addEventListener('change', () => {
            applyEditChanges();
        });
        document.getElementById(id).addEventListener('input', () => {
            updateDurationDisplay();
        });
    });

    // テキスト変更を即座に適用
    document.getElementById('edit-text').addEventListener('change', () => {
        applyEditChanges();
    });
}



function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // テキスト入力中は無視
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            // Ctrl+Sは常に有効
            if (e.ctrlKey && e.key === 's') {
                e.preventDefault();
                saveJson();
            }
            return;
        }

        switch (e.key) {
            case ' ':
                e.preventDefault();
                togglePlayPause();
                break;
            case 'l':
            case 'L':
                toggleLoop();
                break;
            case 'ArrowLeft':
                e.preventDefault();
                selectPreviousSegment();
                break;
            case 'ArrowRight':
                e.preventDefault();
                selectNextSegment();
                break;
            case 'ArrowUp':
                e.preventDefault();
                if (wavesurfer) wavesurfer.skip(-0.1);
                break;
            case 'ArrowDown':
                e.preventDefault();
                if (wavesurfer) wavesurfer.skip(0.1);
                break;
            case ',':
                if (wavesurfer) wavesurfer.skip(-5);
                break;
            case '.':
                if (wavesurfer) wavesurfer.skip(5);
                break;
            case '+':
            case '=':
                adjustZoom(50);
                break;
            case '-':
                adjustZoom(-50);
                break;
            case 'Delete':
                deleteSelectedSegment();
                break;
            case '>':
                changePlaybackRate(1);
                break;
            case '<':
                changePlaybackRate(-1);
                break;
            case '?':
                document.getElementById('help-modal').classList.remove('hidden');
                break;
            case 'Escape':
                document.getElementById('help-modal').classList.add('hidden');
                break;
        }

        // Ctrl+S
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            saveJson();
        }
    });
}

// ===========================================
// ファイル操作
// ===========================================

// 各セグメントに内部IDを付与（UI追跡用、保存時は除去）
function assignInternalIds(segments) {
    segments.forEach(seg => {
        if (!seg._id) {
            seg._id = nextInternalId++;
        }
    });
}

// 保存用にセグメントデータをクリーンアップ（内部IDを除去）
function cleanSegmentsForSave(segments) {
    return segments.map(seg => {
        const cleaned = { ...seg };
        delete cleaned._id;
        delete cleaned.edited;
        return cleaned;
    });
}

async function loadInitialData() {
    try {
        setStatus('読み込み中...');

        const response = await fetch('/api/data');
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || '読み込みに失敗しました');
        }

        currentData = data;

        // 内部IDを付与
        assignInternalIds(currentData.segments);

        // UIを更新
        updateFileInfo();
        renderSegmentList();
        initWavesurfer();

        // ボタンを有効化
        document.getElementById('btn-save').disabled = false;
        document.getElementById('btn-regenerate').disabled = false;
        document.getElementById('btn-force-regenerate').disabled = false;
        document.getElementById('btn-add-segment').disabled = false;

        // 未書き出しの変更がある場合は通知
        if (currentData.has_unexported) {
            setStatus(`${currentData.segments.length}件のセグメントを読み込みました（未書き出しの変更あり）`);
            markModified();
        } else {
            setStatus(`${currentData.segments.length}件のセグメントを読み込みました`);
        }

        updateTitle();

    } catch (error) {
        console.error('Load error:', error);
        setStatus('読み込みエラー: ' + error.message);
    }
}

async function saveJson() {
    if (!currentData) return;

    try {
        setStatus('保存中...');

        // 保存用データを作成（内部IDを除去）
        const saveData = {
            ...currentData,
            segments: cleanSegmentsForSave(currentData.segments)
        };

        const response = await fetch('/api/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(saveData)
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || '保存に失敗しました');
        }

        isModified = false;
        updateModifiedStatus();
        setStatus('保存しました');

    } catch (error) {
        console.error('Save error:', error);
        alert(`保存エラー: ${error.message}`);
        setStatus('保存エラー');
    }
}

async function regenerateAudio(forceExport = false) {
    if (!currentData) return;

    if (!forceExport) {
        if (!confirm('変更を書き出しますか？\n（変更/追加/削除/リネームを反映します）')) {
            return;
        }
    } else {
        if (!confirm('全セグメントを強制的に書き出しますか？\n（変更の有無に関係なく全件を再生成します）')) {
            return;
        }
    }

    try {
        setStatus(forceExport ? '全件書き出し中...' : '書き出し中...');

        // 送信用データを作成（内部IDを除去）
        const requestData = {
            ...currentData,
            segments: cleanSegmentsForSave(currentData.segments),
            force: forceExport
        };

        const response = await fetch('/api/regenerate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || '書き出しに失敗しました');
        }

        // セグメントを更新し、内部IDを付与
        if (result.segments) {
            currentData.segments = result.segments;
            assignInternalIds(currentData.segments);
            renderSegmentList();
        }

        // 変更なしフラグをリセット
        isModified = false;
        currentData.has_unexported = false;
        updateModifiedStatus();
        updateTitle();

        alert(`${result.message}\n出力先: ${result.output_dir}`);
        setStatus('書き出し完了');

    } catch (error) {
        console.error('Export error:', error);
        alert(`書き出しエラー: ${error.message}`);
        setStatus('書き出しエラー');
    }
}

// ===========================================
// Wavesurfer
// ===========================================

function initWavesurfer() {
    // 既存のインスタンスを破棄
    if (wavesurfer) {
        wavesurfer.destroy();
    }

    // Wavesurferを初期化
    wavesurfer = WaveSurfer.create({
        container: '#waveform-container',
        waveColor: '#4a90d9',
        progressColor: '#1a5fa3',
        cursorColor: '#ffffff',
        cursorWidth: 2,
        height: 150,
        normalize: true,
        scrollParent: true,
        minPxPerSec: 100,
    });

    // タイムラインプラグインを初期化（波形の上に表示）
    wavesurfer.registerPlugin(WaveSurfer.Timeline.create({
        height: 20,
        insertPosition: 'beforebegin',
        timeInterval: 0.5,
        primaryLabelInterval: 5,
        secondaryLabelInterval: 1,
        formatTimeCallback: (seconds) => {
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${mins}:${String(secs).padStart(2, '0')}`;
        },
        style: {
            marginBottom: '30px', // 波形との間に余白を作る
            fontSize: '11px',
            color: '#aaaaaa',
        },
    }));

    // リージョンプラグインを初期化
    regions = wavesurfer.registerPlugin(WaveSurfer.Regions.create());

    // イベントリスナー
    wavesurfer.on('ready', () => {
        createRegions();
        updateTimeDisplay();

        // タイムラインクリックでシーク
        const waveformContainer = document.getElementById('waveform-container');
        const timeline = waveformContainer.previousElementSibling;
        if (timeline && timeline.tagName === 'DIV') {
            timeline.style.cursor = 'pointer';
            timeline.addEventListener('click', (e) => {
                const rect = timeline.getBoundingClientRect();
                const clickX = e.clientX - rect.left + waveformContainer.parentElement.scrollLeft;
                const duration = wavesurfer.getDuration();
                const width = timeline.scrollWidth;
                const time = (clickX / width) * duration;
                if (time >= 0 && time <= duration) {
                    wavesurfer.setTime(time);
                }
            });
        }

        // ホイールでズーム
        const waveformEditor = document.getElementById('waveform-editor');
        waveformEditor.addEventListener('wheel', (e) => {
            if (e.ctrlKey) {
                e.preventDefault();
                const delta = e.deltaY > 0 ? -10 : 10;
                adjustZoom(delta);
            }
        }, { passive: false });
    });

    wavesurfer.on('audioprocess', updateTimeDisplay);
    wavesurfer.on('seek', updateTimeDisplay);

    wavesurfer.on('play', () => {
        document.getElementById('btn-play').querySelector('.icon').textContent = '⏸';
    });

    wavesurfer.on('pause', () => {
        document.getElementById('btn-play').querySelector('.icon').textContent = '▶';
    });


    // リージョンイベント
    regions.on('region-clicked', (region, e) => {
        e.stopPropagation();
        const index = parseInt(region.id.replace('region-', ''));
        selectSegment(index);
    });

    regions.on('region-updated', (region) => {
        const index = parseInt(region.id.replace('region-', ''));
        const segment = currentData.segments[index];

        if (segment) {
            segment.start = region.start;
            segment.end = region.end;
            segment.edited = true;

            markModified();
            renderSegmentList();

            if (selectedSegmentIndex === index) {
                updateEditPanel();
            }
        }
    });

    // 音声を読み込み
    const audioUrl = `/api/audio/${encodeURIComponent(currentData.source_file_resolved)}`;
    wavesurfer.load(audioUrl);
}

function createRegions() {
    // 既存のリージョンをクリア
    regions.clearRegions();

    // セグメントごとにリージョンを作成
    currentData.segments.forEach((segment, index) => {
        const color = segment.edited ?
            'rgba(39, 174, 96, 0.3)' :
            'rgba(52, 152, 219, 0.3)';

        const region = regions.addRegion({
            id: `region-${index}`,
            start: segment.start,
            end: segment.end,
            color: color,
            drag: true,
            resize: true,
            minLength: 0.001,  // 最小長さを設定
        });

        // セグメントを下80%に配置（上20%はタイムラインクリック用）
        if (region.element) {
            region.element.classList.add('segment-region');
            region.element.style.height = '80%';
            region.element.style.top = '20%';

            // 短いセグメントでもリサイズハンドルが表示されるように最小幅を確保
            region.element.style.minWidth = '16px';

            // リサイズハンドルを強制的に表示
            const handles = region.element.querySelectorAll('[data-resize]');
            handles.forEach(handle => {
                handle.style.width = '8px';
                handle.style.minWidth = '8px';
                handle.style.display = 'block';
            });
        }
    });
}

function updateRegionColor(index) {
    const region = regions.getRegions().find(r => r.id === `region-${index}`);
    if (!region) return;

    const segment = currentData.segments[index];
    let color;

    if (selectedSegmentIndex === index) {
        color = 'rgba(230, 126, 34, 0.4)';
    } else if (segment.edited) {
        color = 'rgba(39, 174, 96, 0.3)';
    } else {
        color = 'rgba(52, 152, 219, 0.3)';
    }

    region.setOptions({ color });
}

// ===========================================
// セグメント操作
// ===========================================

function renderSegmentList() {
    const container = document.getElementById('segments-container');
    container.innerHTML = '';

    // 選択中のセグメントの内部IDを保存
    const selectedInternalId = selectedSegmentIndex !== null
        ? currentData.segments[selectedSegmentIndex]?._id
        : null;

    // 開始時刻順にソート
    currentData.segments.sort((a, b) => a.start - b.start);

    // 選択中のセグメントの新しい配列位置を探す
    if (selectedInternalId !== null) {
        selectedSegmentIndex = currentData.segments.findIndex(s => s._id === selectedInternalId);
        if (selectedSegmentIndex === -1) selectedSegmentIndex = null;
    }

    currentData.segments.forEach((segment, index) => {
        const item = document.createElement('div');
        item.className = 'segment-item';
        if (selectedSegmentIndex === index) {
            item.classList.add('selected');
        }
        if (segment.edited) {
            item.classList.add('edited');
        }

        // 表示番号は位置番号（1-based）、書き出し済みの場合はindexも表示
        const displayNum = index + 1;
        const indexInfo = segment.filename ? ` (${segment.filename.split('_')[0]})` : '';

        item.innerHTML = `
            <div class="segment-item-header">
                <span class="segment-index">#${displayNum}${indexInfo}</span>
                <span class="segment-time">${formatTime(segment.start)} - ${formatTime(segment.end)}</span>
            </div>
            <div class="segment-text">${escapeHtml(segment.text)}</div>
        `;

        item.addEventListener('click', () => selectSegment(index));
        container.appendChild(item);
    });

    document.getElementById('segment-count').textContent = `${currentData.segments.length}件`;
}

function selectSegment(index) {
    const prevIndex = selectedSegmentIndex;
    selectedSegmentIndex = index;

    // 前の選択を解除
    if (prevIndex !== null) {
        updateRegionColor(prevIndex);
    }

    // 新しい選択を適用
    updateRegionColor(index);

    // リストを更新
    renderSegmentList();

    // 編集パネルを更新
    updateEditPanel();

    // ボタンを有効化
    document.getElementById('btn-delete-segment').disabled = false;

    // 波形をセグメント先頭にスクロール
    const segment = currentData.segments[index];
    if (wavesurfer && segment) {
        const duration = wavesurfer.getDuration();
        wavesurfer.seekTo(segment.start / duration);
    }

    // セグメント一覧をスクロール
    scrollSegmentIntoView(index);
}

function selectPreviousSegment() {
    if (!currentData || currentData.segments.length === 0) return;

    if (selectedSegmentIndex === null) {
        selectSegment(0);
    } else if (selectedSegmentIndex > 0) {
        selectSegment(selectedSegmentIndex - 1);
    }
}

function selectNextSegment() {
    if (!currentData || currentData.segments.length === 0) return;

    if (selectedSegmentIndex === null) {
        selectSegment(0);
    } else if (selectedSegmentIndex < currentData.segments.length - 1) {
        selectSegment(selectedSegmentIndex + 1);
    }
}

function updateEditPanel() {
    if (selectedSegmentIndex === null) {
        document.getElementById('edit-segment-index').textContent = '';
        document.getElementById('edit-start').value = '';
        document.getElementById('edit-end').value = '';
        document.getElementById('edit-text').value = '';
        document.getElementById('edit-duration').textContent = '0.000 秒';
        return;
    }

    const segment = currentData.segments[selectedSegmentIndex];

    // 表示番号は位置番号（1-based）、書き出し済みの場合はファイル名から取得したindexも表示
    const displayNum = selectedSegmentIndex + 1;
    const indexInfo = segment.filename ? ` (${segment.filename.split('_')[0]})` : '';
    document.getElementById('edit-segment-index').textContent = `#${displayNum}${indexInfo}`;
    document.getElementById('edit-start').value = segment.start.toFixed(6);
    document.getElementById('edit-end').value = segment.end.toFixed(6);
    document.getElementById('edit-text').value = segment.text || '';

    updateDurationDisplay();
}

function updateDurationDisplay() {
    const start = parseFloat(document.getElementById('edit-start').value) || 0;
    const end = parseFloat(document.getElementById('edit-end').value) || 0;
    const duration = Math.max(0, end - start);
    document.getElementById('edit-duration').textContent = `${duration.toFixed(3)} 秒`;
}

function applyEditChanges() {
    if (selectedSegmentIndex === null) return;

    const segment = currentData.segments[selectedSegmentIndex];

    const newStart = parseFloat(document.getElementById('edit-start').value);
    const newEnd = parseFloat(document.getElementById('edit-end').value);
    const newText = document.getElementById('edit-text').value;

    // 無効な値はスキップ
    if (isNaN(newStart) || isNaN(newEnd) || newStart >= newEnd) {
        return;
    }

    // 変更があるか確認
    const hasChanges = (
        segment.start !== newStart ||
        segment.end !== newEnd ||
        segment.text !== newText
    );

    if (!hasChanges) return;

    // 変更を適用
    segment.start = newStart;
    segment.end = newEnd;
    segment.text = newText;
    segment.edited = true;

    // リージョンを更新
    const region = regions.getRegions().find(r => r.id === `region-${selectedSegmentIndex}`);
    if (region) {
        region.setOptions({
            start: newStart,
            end: newEnd,
        });
    }

    markModified();
    renderSegmentList();
    updateRegionColor(selectedSegmentIndex);
}

function deleteSelectedSegment() {
    if (selectedSegmentIndex === null) return;

    if (!confirm('このセグメントを削除しますか？')) {
        return;
    }

    // リージョンを削除
    const region = regions.getRegions().find(r => r.id === `region-${selectedSegmentIndex}`);
    if (region) {
        region.remove();
    }

    // セグメントを削除（indexは変更しない）
    currentData.segments.splice(selectedSegmentIndex, 1);

    selectedSegmentIndex = null;

    // リージョンを再作成
    createRegions();

    markModified();
    renderSegmentList();
    updateEditPanel();

    // ボタンを無効化
    document.getElementById('btn-delete-segment').disabled = true;

    setStatus('セグメントを削除しました');
}

function addNewSegment() {
    if (!currentData) return;

    const duration = wavesurfer ? wavesurfer.getDuration() : 10;
    const currentTime = wavesurfer ? wavesurfer.getCurrentTime() : 0;

    // 内部ID生成（UI追跡用）
    const newInternalId = nextInternalId++;

    // 新規セグメントにはindex/index_sub/filenameを設定しない（書き出し時に決定）
    const newSegment = {
        _id: newInternalId,
        start: currentTime,
        end: Math.min(currentTime + 1, duration),
        text: '',
        edited: true,
    };

    currentData.segments.push(newSegment);

    // 先にソートする（renderSegmentListと同じ順序）
    currentData.segments.sort((a, b) => a.start - b.start);

    // ソート後に新しいセグメントの位置を探す（内部IDで検索）
    const newSegmentArrayIndex = currentData.segments.findIndex(s => s._id === newInternalId);

    markModified();

    // ソート後の配列でリージョンを再作成
    createRegions();
    renderSegmentList();

    // 正しい位置を選択
    if (newSegmentArrayIndex !== -1) {
        selectSegment(newSegmentArrayIndex);
    }

    setStatus('新しいセグメントを追加しました');
}

// ===========================================
// 再生制御
// ===========================================

function togglePlayPause() {
    if (!wavesurfer) return;
    wavesurfer.playPause();
}

function toggleLoop() {
    isLoopEnabled = !isLoopEnabled;
    const btn = document.getElementById('btn-loop');
    btn.classList.toggle('active', isLoopEnabled);
    setStatus(isLoopEnabled ? 'ループ再生ON' : 'ループ再生OFF');
}

function changePlaybackRate(direction) {
    if (!wavesurfer) return;

    const rates = [0.5, 1, 1.5, 2, 3];
    const select = document.getElementById('playback-rate');
    const currentRate = parseFloat(select.value);
    const currentIndex = rates.indexOf(currentRate);

    let newIndex;
    if (direction > 0) {
        newIndex = Math.min(currentIndex + 1, rates.length - 1);
    } else {
        newIndex = Math.max(currentIndex - 1, 0);
    }

    const newRate = rates[newIndex];
    select.value = newRate;
    wavesurfer.setPlaybackRate(newRate);
    setStatus(`再生速度: ${newRate}x`);
}


function updateTimeDisplay() {
    if (!wavesurfer) return;

    const current = wavesurfer.getCurrentTime();
    const duration = wavesurfer.getDuration();

    document.getElementById('time-display').textContent =
        `${formatTime(current)} / ${formatTime(duration)}`;

    // ループ再生: 選択セグメントの終了位置でループ
    if (isLoopEnabled && selectedSegmentIndex !== null && wavesurfer.isPlaying()) {
        const segment = currentData.segments[selectedSegmentIndex];
        if (segment && current >= segment.end) {
            wavesurfer.setTime(segment.start);
        }
    }

    // 再生位置に応じてセグメントを自動選択
    autoSelectSegmentAtTime(current);
}

// 指定時刻にあるセグメントを自動選択
let isAutoSelecting = false;

function autoSelectSegmentAtTime(time) {
    // ループ再生中は自動選択を無効化（手動選択を尊重）
    if (!currentData || !currentData.segments || isAutoSelecting || isLoopEnabled) return;

    // 現在時刻を含むセグメントを探す
    const segmentIndex = currentData.segments.findIndex(seg =>
        time >= seg.start && time <= seg.end
    );

    // セグメントが見つかり、現在選択中のものと異なる場合のみ選択
    if (segmentIndex !== -1 && segmentIndex !== selectedSegmentIndex) {
        isAutoSelecting = true;
        selectSegmentWithoutSeek(segmentIndex);
        isAutoSelecting = false;
    }
}

// シークなしでセグメントを選択（自動選択用）
function selectSegmentWithoutSeek(index) {
    const prevIndex = selectedSegmentIndex;
    selectedSegmentIndex = index;

    // 前の選択を解除
    if (prevIndex !== null) {
        updateRegionColor(prevIndex);
    }

    // 新しい選択を適用
    updateRegionColor(index);

    // リストを更新
    renderSegmentList();

    // 編集パネルを更新
    updateEditPanel();

    // ボタンを有効化
    document.getElementById('btn-delete-segment').disabled = false;

    // リスト内の選択項目をスクロールして表示
    scrollSegmentIntoView(index);
}

// セグメントリストの選択項目を表示範囲にスクロール
function scrollSegmentIntoView(index) {
    const container = document.getElementById('segments-container');
    const items = container.querySelectorAll('.segment-item');
    if (items[index]) {
        items[index].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
}

// ===========================================
// ズーム
// ===========================================

function adjustZoom(delta) {
    const slider = document.getElementById('zoom-slider');
    const newValue = Math.max(10, Math.min(500, parseInt(slider.value) + delta));
    slider.value = newValue;
    setZoom(newValue);
}

function setZoom(value) {
    if (!wavesurfer) return;

    const minPxPerSec = value;
    wavesurfer.zoom(minPxPerSec);
    document.getElementById('zoom-level').textContent = `${value}%`;
}

// ===========================================
// UI更新
// ===========================================

function updateFileInfo() {
    const info = currentData.audio_info;
    const fileInfo = `${info.file_name} | ${info.sample_rate}Hz | ${formatTime(info.duration)}`;
    document.getElementById('file-info').textContent = fileInfo;
}

function markModified() {
    isModified = true;
    updateModifiedStatus();
    updateTitle();
}

function updateModifiedStatus() {
    const indicator = document.getElementById('status-modified');
    indicator.classList.toggle('hidden', !isModified);
}

function updateTitle() {
    const hasUnexported = currentData?.has_unexported || false;
    const needsExport = hasUnexported || isModified;
    const icon = needsExport ? '⚠' : '✓';
    const title = `${icon} 手動調整GUI`;

    document.title = title;
    document.querySelector('#header h1').textContent = title;
}

function setStatus(message) {
    document.getElementById('status-message').textContent = message;
}

// ===========================================
// ヘルプモーダル
// ===========================================

function closeHelpModal() {
    document.getElementById('help-modal').classList.add('hidden');
}

// モーダル外クリックで閉じる
document.getElementById('help-modal').addEventListener('click', (e) => {
    if (e.target.id === 'help-modal') {
        closeHelpModal();
    }
});

// ===========================================
// ユーティリティ
// ===========================================

function formatTime(seconds) {
    if (isNaN(seconds)) return '00:00.000';

    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;

    return `${String(mins).padStart(2, '0')}:${secs.toFixed(3).padStart(6, '0')}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
