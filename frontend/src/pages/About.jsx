function About() {
  return (
    <div className="page-content">
      <h2 className="page-title">About SubT</h2>
      <div className="about-section">
        <p className="about-text">
          SubT is an AI-powered video subtitle creation tool that automatically transcribes your videos
          and burns stylized subtitles into them. Built with FastAPI, Whisper AI, and React.
        </p>
        <p className="about-text">
          Created by Guilherme Tenroller as a personal project.
        </p>
        <div className="about-links">
          <a
            href="https://github.com/Tenroller"
            target="_blank"
            rel="noopener noreferrer"
            className="about-link"
          >
            GitHub
          </a>
          <a
            href="https://www.linkedin.com/in/tenroller/"
            target="_blank"
            rel="noopener noreferrer"
            className="about-link"
          >
            LinkedIn
          </a>
        </div>
      </div>
    </div>
  )
}

export default About
