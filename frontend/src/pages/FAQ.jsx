function FAQ() {
  const faqs = [
    {
      question: "Is this free?",
      answer: "Yes, 100%, just upload a video and test it."
    },
    {
      question: "Why is this free?",
      answer: "I created this webapp as a hobby and I host it on my own VPS. There's no catch - I just wanted to build something useful and share it with others."
    },
    {
      question: "Are the videos deleted?",
      answer: "Yes, we don't keep the videos stored. Your uploaded videos and processed outputs are automatically deleted after a short period. We respect your privacy and don't retain any of your content."
    }
  ]

  return (
    <div className="page-content">
      <h2 className="page-title">Frequently Asked Questions</h2>
      <div className="faq-list">
        {faqs.map((faq, index) => (
          <div key={index} className="faq-card">
            <h3 className="faq-card__question">{faq.question}</h3>
            <p className="faq-card__answer">{faq.answer}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default FAQ
