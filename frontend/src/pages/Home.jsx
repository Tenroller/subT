import { useState, useCallback, useEffect, memo } from 'react'

const API_URL = import.meta.env.PROD ? '/api' : 'http://localhost:4569'

const STYLES = [
  {
    id: 'yellow_highlight',
    name: 'Yellow Highlight',
    description: 'Bold text with yellow highlight on current word',
    previewClass: 'yellow-highlight'
  },
  {
    id: 'multicolor_pop',
    name: 'Multi-color Pop',
    description: 'Vibrant alternating colors with heavy weight',
    previewClass: 'multicolor'
  },
  {
    id: 'clean_outline',
    name: 'Clean Outline',
    description: 'White italic text with dark stroke outline',
    previewClass: 'outline'
  }
]

const DISPLAY_MODES = [
  { id: 'word', name: 'Word by Word' },
  { id: 'sentence', name: 'Full Sentence' }
]

const POSITIONS = [
  { id: 'top', name: 'Top' },
  { id: 'center', name: 'Center' },
  { id: 'bottom', name: 'Bottom' }
]

const LANGUAGES = [
  { code: '', name: 'Original (No Translation)' },
  { code: 'en', name: 'English' },
  { code: 'es', name: 'Spanish' },
  { code: 'fr', name: 'French' },
  { code: 'de', name: 'German' },
  { code: 'pt', name: 'Portuguese' },
  { code: 'it', name: 'Italian' },
  { code: 'zh', name: 'Chinese' },
  { code: 'ja', name: 'Japanese' },
  { code: 'ko', name: 'Korean' },
  { code: 'ru', name: 'Russian' },
  { code: 'ar', name: 'Arabic' }
]

// ─── Live Preview Component ───────────────────────────────────────────────────
// Simulates how subtitles look on a real video frame
const LivePreview = memo(function LivePreview({ style, displayMode, position, textColor, highlightColor }) {
  // Animate word-by-word highlight cycling
  const [activeWord, setActiveWord] = useState(1)
  const words = ['This', 'is', 'your', 'subtitle', 'preview']
  const fullSentence = words.join(' ')

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveWord(prev => (prev + 1) % words.length)
    }, 700)
    return () => clearInterval(interval)
  }, [words.length])

  const positionStyle = {
    top: { top: '12%', bottom: 'auto', transform: 'translateX(-50%)' },
    center: { top: '50%', bottom: 'auto', transform: 'translate(-50%, -50%)' },
    bottom: { bottom: '12%', top: 'auto', transform: 'translateX(-50%)' }
  }[position]

  const subtitleContainerStyle = {
    position: 'absolute',
    left: '50%',
    width: '88%',
    textAlign: 'center',
    transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
    ...positionStyle
  }

  const renderSubtitle = () => {
    if (style === 'yellow_highlight') {
      const color = textColor || '#FFFFFF'
      const bg = highlightColor || '#FFD700'
      if (displayMode === 'word') {
        return (
          <div style={{
            fontFamily: "'Impact', 'Arial Black', sans-serif",
            fontSize: '1.05rem',
            fontWeight: 900,
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
            lineHeight: 1.3,
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'center',
            gap: '4px'
          }}>
            {words.map((word, i) => (
              <span key={i} style={{
                color: i === activeWord ? '#000' : color,
                background: i === activeWord ? bg : 'transparent',
                padding: i === activeWord ? '2px 6px' : '2px 0',
                borderRadius: '2px',
                transition: 'all 0.15s ease',
                textShadow: i === activeWord ? 'none' : '2px 2px 4px rgba(0,0,0,0.9), -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000'
              }}>
                {word}
              </span>
            ))}
          </div>
        )
      } else {
        return (
          <div style={{
            fontFamily: "'Impact', 'Arial Black', sans-serif",
            fontSize: '1.05rem',
            fontWeight: 900,
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
            lineHeight: 1.3,
            color: color,
            textShadow: '2px 2px 4px rgba(0,0,0,0.9), -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000'
          }}>
            {fullSentence}
          </div>
        )
      }
    }

    if (style === 'multicolor_pop') {
      const colors = ['#FFFFFF', '#CCFF00', '#00FFFF', '#FF6B6B', '#FFD700']
      if (displayMode === 'word') {
        return (
          <div style={{
            fontFamily: "'Impact', 'Arial Black', sans-serif",
            fontSize: '1.1rem',
            fontWeight: 900,
            textTransform: 'uppercase',
            letterSpacing: '0.03em',
            lineHeight: 1.3,
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'center',
            gap: '5px'
          }}>
            {words.map((word, i) => (
              <span key={i} style={{
                color: colors[i % colors.length],
                display: 'inline-block',
                textShadow: '2px 2px 0px rgba(0,0,0,1), -1px -1px 0 #000'
              }}>
                {word}
              </span>
            ))}
          </div>
        )
      } else {
        return (
          <div style={{
            fontFamily: "'Impact', 'Arial Black', sans-serif",
            fontSize: '1.05rem',
            fontWeight: 900,
            textTransform: 'uppercase',
            letterSpacing: '0.03em',
            lineHeight: 1.4,
            color: '#FFFFFF',
            textShadow: '2px 2px 0px rgba(0,0,0,1)'
          }}>
            {fullSentence}
          </div>
        )
      }
    }

    if (style === 'clean_outline') {
      const color = textColor || '#FFFFFF'
      if (displayMode === 'word') {
        return (
          <div style={{
            fontFamily: "'Arial', sans-serif",
            fontSize: '1.15rem',
            fontStyle: 'italic',
            fontWeight: 700,
            textTransform: 'uppercase',
            lineHeight: 1.4,
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'center',
            gap: '5px'
          }}>
            {words.map((word, i) => (
              <span key={i} style={{
                color: i === activeWord ? '#FFD700' : color,
                WebkitTextStroke: '1.5px black',
                textShadow: '2px 2px 4px rgba(0,0,0,0.8)',
                transition: 'color 0.15s ease',
                display: 'inline-block'
              }}>
                {word}
              </span>
            ))}
          </div>
        )
      } else {
        return (
          <div style={{
            fontFamily: "'Arial', sans-serif",
            fontSize: '1.15rem',
            fontStyle: 'italic',
            fontWeight: 700,
            textTransform: 'uppercase',
            lineHeight: 1.5,
            color: color,
            WebkitTextStroke: '1.5px black',
            textShadow: '2px 2px 4px rgba(0,0,0,0.8)'
          }}>
            {fullSentence}
          </div>
        )
      }
    }
  }

  return (
    <div className="preview-panel">
      <div className="preview-panel__label">
        <span className="preview-panel__dot" />
        Live Preview
      </div>

      {/* Video frame mock */}
      <div className="preview-frame">
        {/* Fake video scene */}
        <div className="preview-frame__scene">
          {/* Simulated video content */}
          <div className="preview-frame__bg-gradient" />
          <div className="preview-frame__person" />
          <div className="preview-frame__cityline" />

          {/* Subtitle overlay */}
          <div style={subtitleContainerStyle}>
            {renderSubtitle()}
          </div>
        </div>

        {/* Video chrome: play bar */}
        <div className="preview-frame__controls">
          <div className="preview-frame__progress">
            <div className="preview-frame__progress-fill" />
          </div>
          <div className="preview-frame__time">0:03 / 0:12</div>
        </div>
      </div>

      {/* Config summary pills */}
      <div className="preview-pills">
        <span className="preview-pill preview-pill--style">
          {STYLES.find(s => s.id === style)?.name}
        </span>
        <span className="preview-pill">
          {DISPLAY_MODES.find(m => m.id === displayMode)?.name}
        </span>
        <span className="preview-pill">
          {POSITIONS.find(p => p.id === position)?.name}
        </span>
      </div>

      <p className="preview-panel__hint">
        Updates live as you change settings
      </p>
    </div>
  )
})

// ─── Session Storage Helpers ──────────────────────────────────────────────────
const JOB_STATE_KEY = 'subt_job_state'

function loadJobState() {
  try {
    const stored = sessionStorage.getItem(JOB_STATE_KEY)
    if (stored) return JSON.parse(stored)
  } catch (e) {
    console.error('Failed to load job state:', e)
  }
  return null
}

function saveJobState(state) {
  try {
    sessionStorage.setItem(JOB_STATE_KEY, JSON.stringify(state))
  } catch (e) {
    console.error('Failed to save job state:', e)
  }
}

function clearJobState() {
  try {
    sessionStorage.removeItem(JOB_STATE_KEY)
  } catch (e) {
    console.error('Failed to clear job state:', e)
  }
}

// ─── Home Page ─────────────────────────────────────────────────────────────────
function Home() {
  // Restore job state from session storage on mount
  const savedState = loadJobState()

  const [file, setFile] = useState(null)
  const [style, setStyle] = useState('yellow_highlight')
  const [displayMode, setDisplayMode] = useState('word')
  const [position, setPosition] = useState('bottom')
  const [isDragging, setIsDragging] = useState(false)
  const [isProcessing, setIsProcessing] = useState(savedState?.isProcessing ?? false)
  const [jobId, setJobId] = useState(savedState?.jobId ?? null)
  const [progress, setProgress] = useState(savedState?.progress ?? 0)
  const [status, setStatus] = useState(savedState?.status ?? '')
  const [error, setError] = useState(null)
  const [isComplete, setIsComplete] = useState(savedState?.isComplete ?? false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [textColor, setTextColor] = useState('#FFFFFF')
  const [highlightColor, setHighlightColor] = useState('#FFD700')
  const [targetLanguage, setTargetLanguage] = useState('')

  // Persist job state to session storage whenever it changes
  useEffect(() => {
    if (jobId) {
      saveJobState({ jobId, progress, status, isProcessing, isComplete })
    }
  }, [jobId, progress, status, isProcessing, isComplete])

  const handleFileSelect = useCallback((selectedFile) => {
    setError(null)
    if (!selectedFile.type.includes('mp4')) {
      setError('Please select an MP4 video file')
      return
    }
    if (selectedFile.size > 100 * 1024 * 1024) {
      setError('File too large. Maximum size is 100MB')
      return
    }
    setFile(selectedFile)
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setIsDragging(false)
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile) handleFileSelect(droppedFile)
  }, [handleFileSelect])

  const handleDragOver = useCallback((e) => { e.preventDefault(); setIsDragging(true) }, [])
  const handleDragLeave = useCallback((e) => { e.preventDefault(); setIsDragging(false) }, [])

  const handleFileInput = useCallback((e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) handleFileSelect(selectedFile)
  }, [handleFileSelect])

  const removeFile = useCallback(() => { setFile(null); setError(null) }, [])

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const handleSubmit = async () => {
    if (!file) return
    setError(null)
    setIsProcessing(true)
    setProgress(0)
    setStatus('Uploading video...')

    try {
      const formData = new FormData()
      formData.append('video', file)
      formData.append('style', style)
      formData.append('display_mode', displayMode)
      formData.append('position', position)
      if (textColor && textColor !== '#FFFFFF') formData.append('text_color', textColor)
      if (highlightColor && highlightColor !== '#FFD700') formData.append('highlight_color', highlightColor)
      if (targetLanguage) formData.append('target_language', targetLanguage)

      const response = await fetch(`${API_URL}/upload`, { method: 'POST', body: formData })
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Upload failed')
      }
      const { job_id } = await response.json()
      setJobId(job_id)
    } catch (err) {
      setError(err.message)
      setIsProcessing(false)
    }
  }

  useEffect(() => {
    if (!jobId || !isProcessing) return

    const controller = new AbortController()
    let pollTimeout

    // Status map constant (moved outside for efficiency)
    const STATUS_MAP = {
      pending: 'Starting...',
      queued: 'Waiting in queue...',
      transcribing: 'Transcribing audio with AI...',
      translating: 'Translating subtitles...',
      generating_subtitles: 'Generating stylized subtitles...',
      processing_video: 'Burning subtitles into video...',
      completed: 'Complete!',
      failed: 'Failed'
    }

    let retryCount = 0
    const MAX_RETRIES = 3

    const pollStatus = async () => {
      try {
        const response = await fetch(`${API_URL}/status/${jobId}`, {
          signal: controller.signal
        })
        const data = await response.json()

        setProgress(data.progress)
        setStatus(STATUS_MAP[data.status] || data.status)

        retryCount = 0 // Reset retry count on success

        if (data.status === 'completed') {
          setIsComplete(true)
          setIsProcessing(false)
          return
        } else if (data.status === 'failed') {
          clearJobState()
          setError(data.error || 'Processing failed')
          setIsProcessing(false)
          return
        }

        // Adaptive polling: early stages poll more frequently
        const isEarlyStage = ['pending', 'queued', 'transcribing'].includes(data.status)
        const interval = isEarlyStage ? 5000 : 15000

        pollTimeout = setTimeout(pollStatus, interval)

      } catch (err) {
        if (err.name === 'AbortError') return // Cleanup triggered

        console.error('Status poll error:', err)

        // Exponential backoff on error
        retryCount++
        if (retryCount <= MAX_RETRIES) {
          const backoffDelay = Math.min(1000 * Math.pow(2, retryCount), 30000)
          pollTimeout = setTimeout(pollStatus, backoffDelay)
        } else {
          clearJobState()
          setError('Failed to check status after multiple retries')
          setIsProcessing(false)
        }
      }
    }

    // Start polling immediately
    pollStatus()

    return () => {
      controller.abort()
      if (pollTimeout) clearTimeout(pollTimeout)
    }
  }, [jobId, isProcessing])

  const handleDownload = () => jobId && window.open(`${API_URL}/download/${jobId}`, '_blank')
  const handleDownloadSrt = () => jobId && window.open(`${API_URL}/download-srt/${jobId}`, '_blank')

  const handleNewVideo = () => {
    clearJobState()
    setFile(null); setJobId(null); setProgress(0); setStatus('')
    setIsComplete(false); setError(null); setShowAdvanced(false)
    setTextColor('#FFFFFF'); setHighlightColor('#FFD700'); setTargetLanguage('')
  }

  return (
    <>
      {error && <div className="error-message">{error}</div>}

      {isComplete ? (
        <section className="download-section">
          <span className="download-section__icon">&#10003;</span>
          <h2 className="download-section__title">Your video is ready!</h2>
          <p className="download-section__subtitle">Subtitles have been burned into your video.</p>
          <div className="download-section__buttons">
            <button className="download-button" onClick={handleDownload}>Download Video</button>
            <button className="download-button download-button--srt" onClick={handleDownloadSrt}>Download SRT</button>
          </div>
          <button className="new-video-button" onClick={handleNewVideo}>Create another video</button>
        </section>
      ) : isProcessing ? (
        <section className="progress-section">
          <div className="progress-section__header">
            <span className="progress-section__title">Processing your video</span>
            <span className="progress-section__status">{status}</span>
          </div>
          <div className="progress-bar">
            <div className="progress-bar__fill" style={{ width: `${progress}%` }} />
          </div>
          <div className="progress-section__percentage">{progress}%</div>
          <p className="progress-section__hint">Go grab a coffee ☕, this may take some time...</p>
        </section>
      ) : (
        /* ── Two-column layout ── */
        <div className="workspace">
          {/* LEFT: config steps */}
          <div className="workspace__config">

            {/* Step 1 — Upload */}
            <div className="step">
              <div className="step__header">
                <div className="step__number">1</div>
                <span className="step__label">Upload your video</span>
              </div>
              <div
                className={`upload-zone ${isDragging ? 'upload-zone--dragover' : ''} ${file ? 'upload-zone--has-file' : ''}`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => !file && document.getElementById('file-input').click()}
              >
                <input id="file-input" type="file" accept="video/mp4" onChange={handleFileInput} style={{ display: 'none' }} />
                <div className="upload-zone__content">
                  {file ? (
                    <div className="upload-zone__file-info">
                      <span className="upload-zone__file-name">{file.name}</span>
                      <span className="upload-zone__file-size">{formatFileSize(file.size)}</span>
                      <button className="upload-zone__remove" onClick={(e) => { e.stopPropagation(); removeFile() }}>Remove</button>
                    </div>
                  ) : (
                    <>
                      <span className="upload-zone__icon">&#127909;</span>
                      <div className="upload-zone__title">Drop your video here or click to browse</div>
                      <div className="upload-zone__subtitle">
                        <span className="upload-zone__pill">MP4</span>
                        <span>·</span>
                        <span>Max 5 minutes</span>
                        <span>·</span>
                        <span>Up to 100 MB</span>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Step 2 — Style */}
            <div className="step">
              <div className="step__header">
                <div className="step__number">2</div>
                <span className="step__label">Choose your subtitle style</span>
              </div>
              <div className="style-cards">
                {STYLES.map((s) => (
                  <div
                    key={s.id}
                    className={`style-card ${style === s.id ? 'style-card--selected' : ''}`}
                    onClick={() => setStyle(s.id)}
                  >
                    <div className="style-card__check">&#10003;</div>
                    <div className={`style-card__preview style-card__preview--${s.previewClass}`}>
                      {s.id === 'yellow_highlight' && (<><span>WHAT </span><span className="highlight">KIND</span><span> OF</span></>)}
                      {s.id === 'multicolor_pop' && (<><span className="word-1">ADD </span><span className="word-2">COOL </span><span className="word-3">CAPTIONS</span></>)}
                      {s.id === 'clean_outline' && <span>HERE ARE THREE</span>}
                    </div>
                    <div className="style-card__name">{s.name}</div>
                    <div className="style-card__description">{s.description}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Step 3 — Display */}
            <div className="step">
              <div className="step__header">
                <div className="step__number">3</div>
                <span className="step__label">Configure display</span>
              </div>
              <div className="options-grid">
                <div className="option-group">
                  <span className="option-group__label">Display Mode</span>
                  <div className="option-buttons">
                    {DISPLAY_MODES.map((mode) => (
                      <button
                        key={mode.id}
                        className={`option-button ${displayMode === mode.id ? 'option-button--selected' : ''}`}
                        onClick={() => setDisplayMode(mode.id)}
                      >{mode.name}</button>
                    ))}
                  </div>
                </div>
                <div className="option-group">
                  <span className="option-group__label">Position</span>
                  <div className="option-buttons">
                    {POSITIONS.map((pos) => (
                      <button
                        key={pos.id}
                        className={`option-button ${position === pos.id ? 'option-button--selected' : ''}`}
                        onClick={() => setPosition(pos.id)}
                      >{pos.name}</button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Step 4 — Advanced */}
            <div className="step">
              <div className="step__header">
                <div className="step__number">4</div>
                <span className="step__label">Advanced options</span>
              </div>
              <button className="advanced-toggle" onClick={() => setShowAdvanced(!showAdvanced)}>
                <span className="advanced-toggle__left">
                  <span className="advanced-toggle__icon">&#9881;</span>
                  Colors &amp; Translation
                </span>
                <span className={`advanced-toggle__chevron ${showAdvanced ? 'advanced-toggle__chevron--open' : ''}`}>&#9660;</span>
              </button>

              {showAdvanced && (
                <div className="advanced-options">
                  <div className="advanced-options__grid">
                    <div className="option-group">
                      <span className="option-group__label">Text Color</span>
                      <div className="color-picker-wrapper">
                        <input type="color" value={textColor} onChange={(e) => setTextColor(e.target.value)} className="color-picker" />
                        <span className="color-value">{textColor}</span>
                      </div>
                    </div>
                    <div className="option-group">
                      <span className="option-group__label">Highlight Color</span>
                      <div className="color-picker-wrapper">
                        <input type="color" value={highlightColor} onChange={(e) => setHighlightColor(e.target.value)} className="color-picker" />
                        <span className="color-value">{highlightColor}</span>
                      </div>
                    </div>
                    <div className="option-group option-group--full">
                      <span className="option-group__label">Translate Subtitles To</span>
                      <select value={targetLanguage} onChange={(e) => setTargetLanguage(e.target.value)} className="language-select">
                        {LANGUAGES.map((lang) => (
                          <option key={lang.code} value={lang.code}>{lang.name}</option>
                        ))}
                      </select>
                      <p className="option-hint">Translation packages are downloaded on first use — this may take a moment.</p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Submit */}
            <section className="submit-section">
              <button className="submit-button" onClick={handleSubmit} disabled={!file}>
                Generate Subtitles
              </button>
              {!file && (
                <p className="submit-hint">
                  <span className="submit-hint__arrow">&#8593;</span>
                  Upload a video above to get started
                </p>
              )}
            </section>
          </div>

          {/* RIGHT: live preview */}
          <div className="workspace__preview">
            <LivePreview
              style={style}
              displayMode={displayMode}
              position={position}
              textColor={textColor}
              highlightColor={highlightColor}
            />
          </div>
        </div>
      )}
    </>
  )
}

export default Home
