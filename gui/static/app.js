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
let isRecreatingRegions = false;  // リージョン再作成時のイベント制御用
let nextInternalId = 1;  // 内部ID生成用カウンター

// undo/redo用スタック
let undoStack = [];
let redoStack = [];
const MAX_UNDO_HISTORY = 50;

// ===========================================
// テーマ（FOUC防止のためDOMContentLoaded前に実行）
// ===========================================

function getPreferredTheme() {
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    const icon = document.getElementById('theme-icon');
    if (icon) {
        icon.textContent = theme === 'light' ? '☀' : '🌙';
    }
    // wavesurferの波形色を更新
    if (wavesurfer) {
        const styles = getComputedStyle(document.documentElement);
        wavesurfer.setOptions({
            waveColor: styles.getPropertyValue('--waveform-color').trim(),
            progressColor: styles.getPropertyValue('--waveform-progress').trim(),
            cursorColor: styles.getPropertyValue('--waveform-cursor').trim(),
        });
    }
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next);
}

// 初期テーマを即座に適用
applyTheme(getPreferredTheme());

// ===========================================
// セッション管理
// ===========================================

function handleSessionMismatch() {
    const reload = confirm(
        'セッションが無効です。\n' +
        'サーバーが再起動されたか、別のファイルが読み込まれています。\n\n' +
        'ページを再読み込みしますか？\n' +
        '（未保存の変更は失われます）'
    );
    if (reload) {
        location.reload();
    }
    setStatus('セッション無効');
}

// ===========================================
// 初期化
// ===========================================

document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    initKeyboardShortcuts();
    // 起動時にデータを自動読み込み
    loadInitialData();
});

// 未保存の変更がある場合、ページ遷移時に警告
window.addEventListener('beforeunload', (e) => {
    if (isModified) {
        e.preventDefault();
    }
});

function initEventListeners() {

    // ツールバー
    document.getElementById('btn-undo').addEventListener('click', undo);
    document.getElementById('btn-redo').addEventListener('click', redo);
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
    document.getElementById('volume-slider').addEventListener('input', (e) => {
        if (wavesurfer) {
            wavesurfer.setVolume(parseInt(e.target.value) / 100);
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
    document.getElementById('btn-theme').addEventListener('click', toggleTheme);
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
        const isTextInput = e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA';

        // Ctrl+S: 常に有効（保存）
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            saveJson();
            return;
        }

        // Ctrl+Enter: テキスト入力中に確定して抜ける
        if (e.ctrlKey && e.key === 'Enter' && isTextInput) {
            e.preventDefault();
            applyEditChanges();
            e.target.blur();
            return;
        }

        // テキスト入力中はそれ以外のショートカットを無視
        // （Ctrl+Z/Yはブラウザのテキスト編集undo/redoを使用）
        if (isTextInput) {
            return;
        }

        // Ctrl+Z/Y: テキスト入力中以外でセグメントundo/redo
        if (e.ctrlKey) {
            if (e.key === 'z') {
                e.preventDefault();
                undo();
                return;
            }
            if (e.key === 'y') {
                e.preventDefault();
                redo();
                return;
            }
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
        delete cleaned.index_formatted;  // 表示専用フィールドを除外
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

        // undo履歴をクリア
        clearUndoHistory();

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
            if (result.error_code === 'SESSION_MISMATCH') {
                handleSessionMismatch();
                return;
            }
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
            if (result.error_code === 'SESSION_MISMATCH') {
                handleSessionMismatch();
                return;
            }
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

    // テーマに応じた波形色を取得
    const styles = getComputedStyle(document.documentElement);
    const waveColor = styles.getPropertyValue('--waveform-color').trim();
    const progressColor = styles.getPropertyValue('--waveform-progress').trim();
    const cursorColor = styles.getPropertyValue('--waveform-cursor').trim();

    // Wavesurferを初期化
    wavesurfer = WaveSurfer.create({
        container: '#waveform-container',
        waveColor: waveColor,
        progressColor: progressColor,
        cursorColor: cursorColor,
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

        // ホイール操作: Ctrl/Shiftでズーム、通常スクロールで横移動
        const waveformEditor = document.getElementById('waveform-editor');
        waveformEditor.addEventListener('wheel', (e) => {
            if (e.ctrlKey || e.shiftKey) {
                // Ctrl+ホイール または Shift+ホイール: ズーム
                e.preventDefault();
                const delta = e.deltaY > 0 ? -10 : 10;
                adjustZoom(delta);
            } else {
                // 通常ホイール: 横スクロール
                e.preventDefault();
                // wavesurferのラッパー要素の親（スクロールコンテナ）を取得
                const wrapper = wavesurfer.getWrapper();
                const scrollContainer = wrapper.parentElement;
                if (scrollContainer) {
                    scrollContainer.scrollLeft += e.deltaY;
                }
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
        if (isRecreatingRegions) return;

        const index = parseInt(region.id.replace('region-', ''));
        const segment = currentData.segments[index];

        if (segment) {
            // 常に start <= end を保証（正規化）
            const newStart = Math.min(region.start, region.end);
            const newEnd = Math.max(region.start, region.end);

            segment.start = newStart;
            segment.end = newEnd;

            markModified();
            renderSegmentList();

            if (selectedSegmentIndex === index) {
                updateEditPanel();
            }

            // 重なり状態が変わった可能性があるため、リージョンを再作成
            isRecreatingRegions = true;
            createRegions();
            // 選択状態を復元
            if (selectedSegmentIndex !== null) {
                updateRegionColor(selectedSegmentIndex);
            }
            isRecreatingRegions = false;
        }
    });

    // 音声を読み込み
    const audioUrl = `/api/audio/${encodeURIComponent(currentData.source_file_resolved)}`;
    wavesurfer.load(audioUrl);
}

// ===========================================
// セグメント重なり計算
// ===========================================

/**
 * セグメントの重なり情報を計算
 * @param {Array} segments - セグメントの配列
 * @returns {Array} 各セグメントの { layerIndex, totalLayers }
 */
function calculateOverlapInfo(segments) {
    const info = segments.map(() => ({ layerIndex: 0, totalLayers: 1 }));

    for (let i = 0; i < segments.length; i++) {
        const seg = segments[i];
        const overlapping = [];

        // このセグメントと重なる全セグメントを探す
        for (let j = 0; j < segments.length; j++) {
            if (i === j) continue;
            const other = segments[j];

            // 重なり判定: 開始が他方の終了より前 かつ 終了が他方の開始より後
            if (seg.start < other.end && seg.end > other.start) {
                overlapping.push(j);
            }
        }

        if (overlapping.length === 0) continue;

        // 既に割り当てられたレイヤーを収集（自分より前に処理されたもののみ）
        const usedLayers = new Set();
        for (const j of overlapping) {
            if (j < i) {
                usedLayers.add(info[j].layerIndex);
            }
        }

        // 空いているレイヤーを探す
        let layer = 0;
        while (usedLayers.has(layer)) {
            layer++;
        }
        info[i].layerIndex = layer;

        // このグループの総レイヤー数を更新
        const maxLayer = Math.max(layer + 1, ...overlapping.map(j => info[j].totalLayers));
        info[i].totalLayers = maxLayer;
        for (const j of overlapping) {
            info[j].totalLayers = maxLayer;
        }
    }

    return info;
}

function createRegions() {
    // 既存のリージョンをクリア
    regions.clearRegions();

    // 重なり情報を計算
    const overlapInfo = calculateOverlapInfo(currentData.segments);

    // セグメントごとにリージョンを作成
    currentData.segments.forEach((segment, index) => {
        const color = 'rgba(52, 152, 219, 0.3)';

        // 常に start <= end を保証（ハンドル位置の逆転を防止）
        const displayStart = Math.min(segment.start, segment.end);
        const displayEnd = Math.max(segment.start, segment.end);

        const region = regions.addRegion({
            id: `region-${index}`,
            start: displayStart,
            end: displayEnd,
            color: color,
            drag: true,
            resize: true,
            minLength: 0,  // 幅0を許容（ハンドルは独立して操作可能）
        });

        // 重なり情報に基づいて高さと位置を設定
        const { layerIndex, totalLayers } = overlapInfo[index];
        const availableHeight = 80; // 使用可能な高さ（%）
        const baseTop = 20; // 開始位置（%）

        const layerHeight = availableHeight / totalLayers;
        const top = baseTop + (layerIndex * layerHeight);

        if (region.element) {
            region.element.classList.add('segment-region');
            region.element.style.height = `${layerHeight}%`;
            region.element.style.top = `${top}%`;

            // 非選択時のスタイル（角丸とボーダー）
            region.element.style.borderRadius = '6px';
            region.element.style.border = '1px solid rgba(255, 255, 255, 0.4)';
            region.element.style.boxSizing = 'border-box';

            // ハンドルのスタイルを設定（inline styleを上書き）
            const leftHandle = region.element.querySelector('[part~="region-handle-left"]');
            const rightHandle = region.element.querySelector('[part~="region-handle-right"]');

            if (leftHandle) {
                // 左ハンドル: 緑色、セグメントの外側（左側）に配置
                leftHandle.style.width = '3px';
                leftHandle.style.background = '#27ae60';
                leftHandle.style.border = 'none';
                leftHandle.style.borderRadius = '2px 0 0 2px';
                leftHandle.style.left = '-3px';
                leftHandle.style.opacity = '0.9';
                leftHandle.style.display = 'none';  // 選択時のみ表示
            }

            if (rightHandle) {
                // 右ハンドル: 赤色、セグメントの外側（右側）に配置
                rightHandle.style.width = '3px';
                rightHandle.style.background = '#e74c3c';
                rightHandle.style.border = 'none';
                rightHandle.style.borderRadius = '0 2px 2px 0';
                rightHandle.style.right = '-3px';
                rightHandle.style.opacity = '0.9';
                rightHandle.style.display = 'none';  // 選択時のみ表示
            }

            // ドラッグ開始時にundo用の状態を保存
            region.element.addEventListener('mousedown', () => {
                saveStateForUndo();
            });
        }
    });
}

function updateRegionColor(index) {
    const region = regions.getRegions().find(r => r.id === `region-${index}`);
    if (!region) return;

    const segment = currentData.segments[index];
    let color;
    let zIndex;

    if (selectedSegmentIndex === index) {
        color = 'rgba(230, 126, 34, 0.4)';
        zIndex = '100';  // 選択中は最前面に
    } else {
        color = 'rgba(52, 152, 219, 0.3)';
        zIndex = '1';
    }

    region.setOptions({ color });

    // 選択中のセグメントを最前面に表示し、ハンドルを表示
    if (region.element) {
        region.element.style.zIndex = zIndex;

        const leftHandle = region.element.querySelector('[part~="region-handle-left"]');
        const rightHandle = region.element.querySelector('[part~="region-handle-right"]');
        const isSelected = selectedSegmentIndex === index;

        // 選択状態に応じてボーダーを変更
        if (isSelected) {
            region.element.style.border = 'none';
        } else {
            region.element.style.border = '1px solid rgba(255, 255, 255, 0.4)';
        }

        if (leftHandle) {
            leftHandle.style.display = isSelected ? 'block' : 'none';
        }
        if (rightHandle) {
            rightHandle.style.display = isSelected ? 'block' : 'none';
        }
    }
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

        // 表示番号はセグメントID、書き出し済みの場合はindexも表示
        const segId = segment._seg_id || '?';
        const indexInfo = segment.index_formatted ? ` (${segment.index_formatted})` : '';

        item.innerHTML = `
            <div class="segment-item-header">
                <span class="segment-index">#${segId}${indexInfo}</span>
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

    // 表示番号はセグメントID、書き出し済みの場合はindexも表示
    const segId = segment._seg_id || '?';
    const indexInfo = segment.index_formatted ? ` (${segment.index_formatted})` : '';
    document.getElementById('edit-segment-index').textContent = `#${segId}${indexInfo}`;
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

    // undo用に状態を保存
    saveStateForUndo();

    // 変更を適用
    segment.start = newStart;
    segment.end = newEnd;
    segment.text = newText;

    markModified();
    renderSegmentList();

    // 重なり状態が変わった可能性があるため、リージョンを再作成
    isRecreatingRegions = true;
    createRegions();
    // 選択状態を復元
    if (selectedSegmentIndex !== null) {
        updateRegionColor(selectedSegmentIndex);
    }
    isRecreatingRegions = false;
}

function deleteSelectedSegment() {
    if (selectedSegmentIndex === null) return;

    if (!confirm('このセグメントを削除しますか？')) {
        return;
    }

    // undo用に状態を保存
    saveStateForUndo();

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

    // undo用に状態を保存
    saveStateForUndo();

    const duration = wavesurfer ? wavesurfer.getDuration() : 10;
    const currentTime = wavesurfer ? wavesurfer.getCurrentTime() : 0;

    // 内部ID生成（UI追跡用）
    const newInternalId = nextInternalId++;

    // セグメントID生成（既存IDの最大値+1）
    const existingIds = currentData.segments
        .map(s => parseInt(s._seg_id || '0', 10))
        .filter(id => !isNaN(id));
    const maxId = existingIds.length > 0 ? Math.max(...existingIds) : 0;
    const newSegId = String(maxId + 1);

    // 新規セグメントにはindex/index_subを設定しない（書き出し時に決定）
    const newSegment = {
        _id: newInternalId,
        _seg_id: newSegId,
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

// ===========================================
// Undo/Redo機能
// ===========================================

function saveStateForUndo() {
    if (!currentData || !currentData.segments) return;

    // 現在の状態をディープコピーして保存
    const state = {
        segments: JSON.parse(JSON.stringify(currentData.segments)),
        selectedSegmentIndex: selectedSegmentIndex
    };

    undoStack.push(state);

    // 履歴の上限を超えたら古いものを削除
    if (undoStack.length > MAX_UNDO_HISTORY) {
        undoStack.shift();
    }

    // 新しい操作をしたらredoスタックをクリア
    redoStack = [];

    updateUndoRedoButtons();
}

function undo() {
    if (undoStack.length === 0 || !currentData) return;

    // 現在の状態をredoスタックに保存
    const currentState = {
        segments: JSON.parse(JSON.stringify(currentData.segments)),
        selectedSegmentIndex: selectedSegmentIndex
    };
    redoStack.push(currentState);

    // 前の状態を復元
    const prevState = undoStack.pop();
    currentData.segments = prevState.segments;
    selectedSegmentIndex = prevState.selectedSegmentIndex;

    // UIを更新
    refreshAfterUndoRedo();
    setStatus('元に戻しました');
}

function redo() {
    if (redoStack.length === 0 || !currentData) return;

    // 現在の状態をundoスタックに保存
    const currentState = {
        segments: JSON.parse(JSON.stringify(currentData.segments)),
        selectedSegmentIndex: selectedSegmentIndex
    };
    undoStack.push(currentState);

    // 次の状態を復元
    const nextState = redoStack.pop();
    currentData.segments = nextState.segments;
    selectedSegmentIndex = nextState.selectedSegmentIndex;

    // UIを更新
    refreshAfterUndoRedo();
    setStatus('やり直しました');
}

function refreshAfterUndoRedo() {
    // リージョンを再作成
    isRecreatingRegions = true;
    createRegions();
    if (selectedSegmentIndex !== null) {
        updateRegionColor(selectedSegmentIndex);
    }
    isRecreatingRegions = false;

    // リストを更新
    renderSegmentList();
    updateEditPanel();

    // 変更フラグを更新
    markModified();
    updateUndoRedoButtons();
}

function updateUndoRedoButtons() {
    const undoBtn = document.getElementById('btn-undo');
    const redoBtn = document.getElementById('btn-redo');

    if (undoBtn) {
        undoBtn.disabled = undoStack.length === 0;
    }
    if (redoBtn) {
        redoBtn.disabled = redoStack.length === 0;
    }
}

function clearUndoHistory() {
    undoStack = [];
    redoStack = [];
    updateUndoRedoButtons();
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
