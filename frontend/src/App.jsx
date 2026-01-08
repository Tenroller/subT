import { useState, useCallback, useEffect } from 'react'
import './App.css'

// Use relative /api path in production (nginx proxies to backend)
// Use localhost:8000 for local development
const API_URL = import.meta.env.PROD ? '/api' : 'http://localhost:8000'

// Subtitle style options
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

function App() {
  // State
  const [file, setFile] = useState(null)
  const [style, setStyle] = useState('yellow_highlight')
  const [displayMode, setDisplayMode] = useState('word')
  const [position, setPosition] = useState('bottom')
  const [isDragging, setIsDragging] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [jobId, setJobId] = useState(null)
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState('')
  const [error, setError] = useState(null)
  const [isComplete, setIsComplete] = useState(false)

  // File handling
  const handleFileSelect = useCallback((selectedFile) => {
    setError(null)

    // Validate file type
    if (!selectedFile.type.includes('mp4')) {
      setError('Please select an MP4 video file')
      return
    }

    // Max 100MB for upload (actual duration check happens on server)
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
    if (droppedFile) {
      handleFileSelect(droppedFile)
    }
  }, [handleFileSelect])

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleFileInput = useCallback((e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      handleFileSelect(selectedFile)
    }
  }, [handleFileSelect])

  const removeFile = useCallback(() => {
    setFile(null)
    setError(null)
  }, [])

  // Format file size
  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  // Submit handler
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

      const response = await fetch(`${API_URL}/upload`, {
        method: 'POST',
        body: formData
      })

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

  // Poll for job status
  useEffect(() => {
    if (!jobId || !isProcessing) return

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`${API_URL}/status/${jobId}`)
        const data = await response.json()

        setProgress(data.progress)

        // Convert status to user-friendly text
        const statusMap = {
          pending: 'Starting...',
          queued: 'Waiting in queue... (Server busy)',
          transcribing: 'Transcribing audio with AI...',
          generating_subtitles: 'Generating stylized subtitles...',
          processing_video: 'Burning subtitles into video...',
          completed: 'Complete!',
          failed: 'Failed'
        }
        setStatus(statusMap[data.status] || data.status)

        if (data.status === 'completed') {
          clearInterval(pollInterval)
          setIsComplete(true)
          setIsProcessing(false)
        } else if (data.status === 'failed') {
          clearInterval(pollInterval)
          setError(data.error || 'Processing failed')
          setIsProcessing(false)
        }
      } catch (err) {
        console.error('Status poll error:', err)
      }
    }, 10000)

    return () => clearInterval(pollInterval)
  }, [jobId, isProcessing])

  // Download handler
  const handleDownload = () => {
    if (jobId) {
      window.open(`${API_URL}/download/${jobId}`, '_blank')
    }
  }

  // Reset to start new video
  const handleNewVideo = () => {
    setFile(null)
    setJobId(null)
    setProgress(0)
    setStatus('')
    setIsComplete(false)
    setError(null)
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <h1 className="header__title">Subtitle Creator</h1>
        <p className="header__subtitle">
          Upload your video and let AI create stunning, stylized subtitles automatically
        </p>
      </header>

      {/* Error Message */}
      {error && (
        <div className="error-message">
          ⚠️ {error}
        </div>
      )}

      {/* Completed State */}
      {isComplete ? (
        <section className="download-section">
          <div className="download-section__icon">✅</div>
          <h2 className="download-section__title">Your video is ready!</h2>
          <p className="download-section__subtitle">
            Subtitles have been burned into your video. Click below to download.
          </p>
          <button className="download-button" onClick={handleDownload}>
            ⬇️ Download Video
          </button>
          <button className="new-video-button" onClick={handleNewVideo}>
            Create another video
          </button>
        </section>
      ) : isProcessing ? (
        /* Processing State */
        <section className="progress-section">
          <div className="progress-section__header">
            <span className="progress-section__title">Processing your video</span>
            <span className="progress-section__status">{status}</span>
          </div>
          <div className="progress-bar">
            <div
              className="progress-bar__fill"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="progress-section__percentage">
            {progress}%
          </div>
        </section>
      ) : (
        <>
          {/* Upload Section */}
          <section className="upload-section">
            <div
              className={`upload-zone ${isDragging ? 'upload-zone--dragover' : ''} ${file ? 'upload-zone--has-file' : ''}`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => !file && document.getElementById('file-input').click()}
            >
              <input
                id="file-input"
                type="file"
                accept="video/mp4"
                onChange={handleFileInput}
              />
              <div className="upload-zone__content">
                {file ? (
                  <div className="upload-zone__file-info">
                    <span className="upload-zone__file-name">🎬 {file.name}</span>
                    <span className="upload-zone__file-size">{formatFileSize(file.size)}</span>
                    <button
                      className="upload-zone__remove"
                      onClick={(e) => { e.stopPropagation(); removeFile(); }}
                    >
                      Remove
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="upload-zone__icon">🎬</div>
                    <div className="upload-zone__title">
                      Drop your video here or click to browse
                    </div>
                    <div className="upload-zone__subtitle">
                      MP4 format, maximum 5 minutes
                    </div>
                  </>
                )}
              </div>
            </div>
          </section>

          {/* Style Selection */}
          <section className="options-section">
            <h2 className="options-section__title">Choose your subtitle style</h2>
            <div className="style-cards">
              {STYLES.map((s) => (
                <div
                  key={s.id}
                  className={`style-card ${style === s.id ? 'style-card--selected' : ''}`}
                  onClick={() => setStyle(s.id)}
                >
                  <div className={`style-card__preview style-card__preview--${s.previewClass}`}>
                    {s.id === 'yellow_highlight' && (
                      <>
                        <span>WHAT </span>
                        <span className="highlight">KIND</span>
                        <span> OF</span>
                      </>
                    )}
                    {s.id === 'multicolor_pop' && (
                      <>
                        <span className="word-1">ADD </span>
                        <span className="word-2">COOL </span>
                        <span className="word-3">CAPTIONS</span>
                      </>
                    )}
                    {s.id === 'clean_outline' && (
                      <span>HERE ARE THREE</span>
                    )}
                  </div>
                  <div className="style-card__name">{s.name}</div>
                  <div className="style-card__description">{s.description}</div>
                </div>
              ))}
            </div>
          </section>

          {/* Display Mode & Position */}
          <section className="options-section">
            <div className="options-grid">
              <div className="option-group">
                <span className="option-group__label">Display Mode</span>
                <div className="option-buttons">
                  {DISPLAY_MODES.map((mode) => (
                    <button
                      key={mode.id}
                      className={`option-button ${displayMode === mode.id ? 'option-button--selected' : ''}`}
                      onClick={() => setDisplayMode(mode.id)}
                    >
                      {mode.name}
                    </button>
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
                    >
                      {pos.name}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* Submit Button */}
          <section className="submit-section">
            <button
              className="submit-button"
              onClick={handleSubmit}
              disabled={!file}
            >
              🚀 Generate Subtitles
            </button>
          </section>
        </>
      )}
    </div>
  )
}

export default App
