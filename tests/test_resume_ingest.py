from app.rag.ingest import ResumeIngestor


def test_latex_to_text_keeps_human_resume_content():
    source = r"""
\documentclass{article}
\begin{document}
\section{Projects}
\textbf{AI Career Copilot} \href{https://github.com/example}{GitHub}\\
Built Python, FastAPI, RAG, and ChromaDB workflows. % comment
\end{document}
"""
    text = ResumeIngestor.latex_to_text(source)
    assert "AI Career Copilot" in text
    assert "Python" in text
    assert "FastAPI" in text
    assert "comment" not in text
