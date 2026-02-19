import { Link } from 'react-router-dom'

function Layout({ children }) {
  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <Link to="/" className="header__logo-link">
          <h1 className="header__title">SubT</h1>
        </Link>
        <p className="header__subtitle">
          Upload your video and let AI create stunning, stylized subtitles automatically.
        </p>
      </header>

      {/* Main content */}
      <main className="main-content">
        {children}
      </main>

      {/* Footer */}
      <footer className="footer">
        <nav className="footer__nav">
          <Link to="/faq" className="footer__link">FAQ</Link>
          <span className="footer__separator">|</span>
          <Link to="/about" className="footer__link">About</Link>
        </nav>
      </footer>
    </div>
  )
}

export default Layout
